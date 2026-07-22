#include <Arduino.h>
#include <WiFi.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/joint_state.h>

#include "wifi_config.h"
#include "servo_bus.h"

extern "C" void arduino_wifi_transport_dump_trace();

const uint16_t AGENT_PORT = 8888;
const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long WIFI_RESTART_TIMEOUT_MS = 10000;

rcl_publisher_t state_pub;
rcl_subscription_t command_sub;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
sensor_msgs__msg__JointState state_msg;
sensor_msgs__msg__JointState command_msg;
rosidl_runtime_c__String joint_names[6];
rosidl_runtime_c__String command_names[6];
char command_name_buffers[6][32];
char command_frame_id[1] = {'\0'};
double pos_data[6] = {0};
double command_pos_data[6] = {0};
double target_pos_data[6] = {0};
volatile uint32_t publish_count = 0;
volatile rcl_ret_t last_publish_rc = RCL_RET_OK;
volatile uint32_t command_count = 0;
volatile uint32_t invalid_command_count = 0;
volatile uint32_t spin_error_count = 0;
volatile unsigned long last_command_ms = 0;
volatile bool command_fresh = false;
volatile uint32_t command_timeout_count = 0;
bool servo_calibration_ok = false;
volatile uint32_t command_generation = 0;
uint32_t processed_command_generation = 0;
uint32_t control_reject_count = 0;
bool servo_control_armed = false;
double last_applied_target[6] = {0};

void initialize_joint_messages() {
    const char* names[6] = {
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    };

    for (int i = 0; i < 6; i++) {
        joint_names[i].data = (char*)names[i];
        joint_names[i].size = strlen(names[i]);
        joint_names[i].capacity = strlen(names[i]) + 1;

        command_names[i].data = command_name_buffers[i];
        command_names[i].size = 0;
        command_names[i].capacity = sizeof(command_name_buffers[i]);
    }

    state_msg.name.data = joint_names;
    state_msg.name.size = 6;
    state_msg.name.capacity = 6;
    state_msg.position.data = pos_data;
    state_msg.position.size = 6;
    state_msg.position.capacity = 6;

    command_msg.header.frame_id.data = command_frame_id;
    command_msg.header.frame_id.size = 0;
    command_msg.header.frame_id.capacity = sizeof(command_frame_id);
    command_msg.name.data = command_names;
    command_msg.name.size = 0;
    command_msg.name.capacity = 6;
    command_msg.position.data = command_pos_data;
    command_msg.position.size = 0;
    command_msg.position.capacity = 6;
}

void command_callback(const void* message) {
    const sensor_msgs__msg__JointState* command =
        (const sensor_msgs__msg__JointState*)message;

    if (command == NULL || command->name.size != 6 ||
        command->position.size != 6) {
        invalid_command_count++;
        return;
    }

    const char* expected_names[6] = {
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    };
    for (int i = 0; i < 6; i++) {
        const size_t expected_size = strlen(expected_names[i]);
        if (command->name.data[i].size != expected_size ||
            memcmp(command->name.data[i].data, expected_names[i], expected_size) != 0) {
            invalid_command_count++;
            return;
        }
        const double value = command->position.data[i];
        if (!isfinite(value)) {
            invalid_command_count++;
            return;
        }
    }

    if (!servo_bus::command_within_limits(command->position.data)) {
        invalid_command_count++;
        return;
    }

    for (int i = 0; i < 6; i++) {
        target_pos_data[i] = command->position.data[i];
    }
    command_count++;
    command_generation++;
    last_command_ms = millis();
    command_fresh = true;
}

void publish_joint_state() {
    state_msg.position.data = pos_data;
    state_msg.position.size = 6;
    last_publish_rc = rcl_publish(&state_pub, &state_msg, NULL);
    publish_count++;
}

bool print_servo_diagnostics() {
    servo_bus::Diagnostic diagnostics[servo_bus::kJointCount] = {};
    const size_t valid_count = servo_bus::read_diagnostics(diagnostics);
    Serial.printf("Servo diagnostics: %u/%u valid\n",
        static_cast<unsigned>(valid_count),
        static_cast<unsigned>(servo_bus::kJointCount));
    for (size_t i = 0; i < servo_bus::kJointCount; ++i) {
        const servo_bus::Diagnostic& d = diagnostics[i];
        Serial.printf(
            "  ID%u valid:%d fw:%d.%d model:%d offset:%d min:%d max:%d torque:%d voltage:%.1fV temp:%dC pos:%d\n",
            static_cast<unsigned>(i + 1), d.valid ? 1 : 0,
            d.firmware_major, d.firmware_minor, d.model_number,
            d.homing_offset, d.range_min, d.range_max, d.torque_enabled,
            d.voltage_tenths / 10.0, d.temperature_c, d.present_position);
    }
    const bool matches = servo_bus::calibration_matches(diagnostics);
    Serial.printf("Servo calibration match: %s\n", matches ? "YES" : "NO");
    return matches;
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("=== SO-101 micro-ROS safe servo control ===");

    servo_bus::begin();
    const uint8_t startup_servo_mask = servo_bus::scan();
    Serial.printf("Servo Ping mask: 0x%02x (expected 0x3f)\n", startup_servo_mask);
    servo_calibration_ok = print_servo_diagnostics();

    // WiFi
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.setSleep(false);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    unsigned long wifi_start = millis();
    Serial.printf("\nIP: %s  RSSI: %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    delay(3000);

    initialize_joint_messages();

    // micro-ROS: wait for the Agent before allocating entities. Retrying a
    // partially initialized rclc stack leaks scarce ESP32-C3 memory.
    set_microros_wifi_transports(
        (char*)WIFI_SSID, (char*)WIFI_PASS, (char*)AGENT_IP, AGENT_PORT);
    while (rmw_uros_ping_agent(500, 1) != RMW_RET_OK) {
        Serial.println("Waiting for micro-ROS Agent...");
        delay(1000);
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi lost while waiting; restarting.");
            delay(100);
            ESP.restart();
        }
    }

    const char* step = "";
    allocator = rcl_get_default_allocator();
    rcl_ret_t rc = RCL_RET_OK;
    #define TRY(s, fn) step = s; if (rc == RCL_RET_OK) { rc = fn; if (rc != RCL_RET_OK) { Serial.printf("FAIL [%s] rc=%d\n", step, rc); } }
    TRY("support",  rclc_support_init(&support, 0, NULL, &allocator));
    // Use the RMW best-effort entity-creation stream. ESP -> Agent create
    // requests are stable, while the immediate Agent status datagram can
    // be missed when it is followed by an XRCE heartbeat.
    TRY("entity timeout", rmw_uros_set_context_entity_creation_session_timeout(
        rcl_context_get_rmw_context(&support.context), 0));
    TRY("node",     rclc_node_init_default(&node, "so101_follower", "", &support));
    TRY("publisher", rclc_publisher_init_best_effort(&state_pub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState), "joint_states"));
    TRY("subscription", rclc_subscription_init_best_effort(&command_sub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState), "joint_command"));
    TRY("executor", rclc_executor_init(&executor, &support.context, 1, &allocator));
    TRY("exec+subscription", rclc_executor_add_subscription(
        &executor, &command_sub, &command_msg, &command_callback, ON_NEW_DATA));
    #undef TRY
    if (rc != RCL_RET_OK) {
        arduino_wifi_transport_dump_trace();
        Serial.println("micro-ROS init failed; restarting cleanly.");
        delay(1000);
        ESP.restart();
    }
    Serial.printf("micro-ROS ready. Uptime: %lu s\n", (millis() - wifi_start) / 1000);
    servo_calibration_ok = print_servo_diagnostics();

    // 每 5 秒报一次状态
    unsigned long t = 0;
    unsigned long last_publish = millis();
    unsigned long last_servo_read = millis();
    unsigned long last_diagnostics = millis();
    unsigned long wifi_lost_since = 0;
    while (true) {
        rcl_ret_t spin_rc = rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
        if (spin_rc != RCL_RET_OK && spin_rc != RCL_RET_TIMEOUT) {
            spin_error_count++;
            rcl_reset_error();
        }
        if (millis() - last_publish >= 50) {
            last_publish += 50;
            publish_joint_state();
        }
        if (millis() - last_servo_read >= 50) {
            last_servo_read += 50;
            servo_bus::read_all(pos_data);
        }
        if (processed_command_generation != command_generation) {
            processed_command_generation = command_generation;
            const servo_bus::Stats& servo_stats = servo_bus::stats();
            bool command_safe = servo_calibration_ok &&
                servo_stats.response_mask == 0x3f;

            if (!servo_control_armed) {
                for (int i = 0; i < 6 && command_safe; ++i) {
                    if (fabs(target_pos_data[i] - pos_data[i]) > 0.05) {
                        command_safe = false;
                    }
                }
                if (command_safe && servo_bus::arm_at_current_position(pos_data)) {
                    servo_control_armed = true;
                    for (int i = 0; i < 6; ++i) {
                        last_applied_target[i] = pos_data[i];
                    }
                    Serial.println("Servo control ARMED at measured position.");
                } else {
                    control_reject_count++;
                    Serial.println("Control command rejected: arm handshake mismatch.");
                }
            } else {
                for (int i = 0; i < 6 && command_safe; ++i) {
                    if (fabs(target_pos_data[i] - last_applied_target[i]) > 0.25) {
                        command_safe = false;
                    }
                }
                if (command_safe && servo_bus::write_positions(target_pos_data)) {
                    for (int i = 0; i < 6; ++i) {
                        last_applied_target[i] = target_pos_data[i];
                    }
                } else {
                    control_reject_count++;
                    Serial.println("Control command rejected: limits, step, or bus state.");
                }
            }
        }
        if (command_fresh && millis() - last_command_ms > COMMAND_TIMEOUT_MS) {
            command_fresh = false;
            command_timeout_count++;
        }
        if (millis() - last_diagnostics >= 60000) {
            last_diagnostics += 60000;
            servo_calibration_ok = print_servo_diagnostics();
        }
        delay(1);
        if (WiFi.status() != WL_CONNECTED) {
            if (wifi_lost_since == 0) {
                wifi_lost_since = millis();
                Serial.println("WIFI LOST! Waiting for auto-reconnect...");
            } else if (millis() - wifi_lost_since > WIFI_RESTART_TIMEOUT_MS) {
                Serial.println("WiFi recovery timed out; restarting.");
                delay(100);
                ESP.restart();
            }
        } else {
            wifi_lost_since = 0;
        }
        if (millis() - t > 5000) {
            t = millis();
            const servo_bus::Stats& servo_stats = servo_bus::stats();
            Serial.printf("OK RSSI:%d uptime:%lu pub:%lu pub_rc:%d cmd:%lu fresh:%d timeout:%lu invalid:%lu reject:%lu spin_err:%lu age:%lu servo_mask:0x%02x calib:%d armed:%d servo_ok:%lu servo_err:%lu write_ok:%lu write_err:%lu\n",
                WiFi.RSSI(), (millis() - wifi_start) / 1000,
                (unsigned long) publish_count, last_publish_rc,
                (unsigned long) command_count,
                command_fresh ? 1 : 0,
                (unsigned long) command_timeout_count,
                (unsigned long) invalid_command_count,
                (unsigned long) control_reject_count,
                (unsigned long) spin_error_count,
                command_count > 0 ? millis() - last_command_ms : 0,
                servo_stats.response_mask,
                servo_calibration_ok ? 1 : 0,
                servo_control_armed ? 1 : 0,
                (unsigned long) servo_stats.read_success,
                (unsigned long) servo_stats.read_errors,
                (unsigned long) servo_stats.write_success,
                (unsigned long) servo_stats.write_errors);
        }
    }
}

void loop() {}
