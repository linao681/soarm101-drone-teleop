#include <Arduino.h>
#include <WiFi.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <sensor_msgs/msg/joint_state.h>
#include <std_msgs/msg/int32_multi_array.h>

#if __has_include("wifi_config.h")
#include "wifi_config.h"
#else
#include "wifi_config.example.h"
#endif
#include "control_logic.h"
#include "agent_discovery.h"
#include "servo_bus.h"

extern "C" void arduino_wifi_transport_dump_trace();

const unsigned long WIFI_RESTART_TIMEOUT_MS = 10000;
constexpr unsigned long AGENT_LIVENESS_PERIOD_MS = 1000;
constexpr uint32_t AGENT_PING_TIMEOUT_MS = 100;
constexpr uint8_t AGENT_LIVENESS_FAILURE_LIMIT = 5;

rcl_publisher_t state_pub;
rcl_publisher_t status_pub;
rcl_subscription_t command_sub;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
sensor_msgs__msg__JointState state_msg;
sensor_msgs__msg__JointState command_msg;
std_msgs__msg__Int32MultiArray status_msg;
rosidl_runtime_c__String joint_names[6];
rosidl_runtime_c__String command_names[6];
char command_name_buffers[6][32];
char command_frame_id[32] = {'\0'};
int32_t status_data[14] = {0};
double pos_data[6] = {0};
double command_pos_data[6] = {0};
volatile uint32_t publish_count = 0;
volatile rcl_ret_t last_publish_rc = RCL_RET_OK;
volatile rcl_ret_t last_status_rc = RCL_RET_OK;
volatile uint32_t command_count = 0;
volatile uint32_t invalid_command_count = 0;
volatile uint32_t spin_error_count = 0;
volatile unsigned long last_command_ms = 0;
volatile int32_t last_reject_reason_code = control_logic::NONE;
bool servo_calibration_ok = false;
bool pending_arm_request = false;
control_logic::Controller controller;

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

    status_msg.data.data = status_data;
    status_msg.data.size = 14;
    status_msg.data.capacity = 14;
}

bool parse_hex_digit(char value, uint8_t* digit) {
    if (value >= '0' && value <= '9') {
        *digit = static_cast<uint8_t>(value - '0');
        return true;
    }
    if (value >= 'a' && value <= 'f') {
        *digit = static_cast<uint8_t>(value - 'a' + 10);
        return true;
    }
    if (value >= 'A' && value <= 'F') {
        *digit = static_cast<uint8_t>(value - 'A' + 10);
        return true;
    }
    return false;
}

bool parse_command_id(const rosidl_runtime_c__String& value,
                      uint32_t* session_id, uint32_t* sequence) {
    if (value.data == nullptr || value.size != 20 || value.data[0] != 'S' ||
        value.data[1] != '1' || value.data[2] != ':' || value.data[11] != ':') {
        return false;
    }
    uint32_t parsed_session = 0;
    uint32_t parsed_sequence = 0;
    for (size_t i = 0; i < 8; ++i) {
        uint8_t digit = 0;
        if (!parse_hex_digit(value.data[3 + i], &digit)) {
            return false;
        }
        parsed_session = (parsed_session << 4) | digit;
        if (!parse_hex_digit(value.data[12 + i], &digit)) {
            return false;
        }
        parsed_sequence = (parsed_sequence << 4) | digit;
    }
    *session_id = parsed_session;
    *sequence = parsed_sequence;
    return true;
}

control_logic::JointArray measured_positions() {
    control_logic::JointArray measured{};
    for (size_t joint = 0; joint < control_logic::kJointCount; ++joint) {
        measured[joint] = pos_data[joint];
    }
    return measured;
}

void set_reject_reason(control_logic::RejectReason reason) {
    last_reject_reason_code = static_cast<int32_t>(reason);
}

void command_callback(const void* message) {
    const sensor_msgs__msg__JointState* command =
        (const sensor_msgs__msg__JointState*)message;

    if (command == NULL || command->name.size != 6 ||
        command->position.size != 6 || command->name.data == nullptr ||
        command->position.data == nullptr) {
        invalid_command_count++;
        set_reject_reason(control_logic::BAD_SHAPE);
        return;
    }

    const char* expected_names[6] = {
        "shoulder_pan", "shoulder_lift", "elbow_flex",
        "wrist_flex", "wrist_roll", "gripper"
    };
    for (int i = 0; i < 6; i++) {
        const size_t expected_size = strlen(expected_names[i]);
        if (command->name.data[i].data == nullptr ||
            command->name.data[i].size != expected_size ||
            memcmp(command->name.data[i].data, expected_names[i], expected_size) != 0) {
            invalid_command_count++;
            set_reject_reason(control_logic::BAD_NAME);
            return;
        }
        const double value = command->position.data[i];
        if (!isfinite(value)) {
            invalid_command_count++;
            set_reject_reason(control_logic::NONFINITE);
            return;
        }
    }

    if (!servo_bus::command_within_limits(command->position.data)) {
        invalid_command_count++;
        set_reject_reason(control_logic::OUT_OF_RANGE);
        return;
    }

    uint32_t session_id = 0;
    uint32_t sequence = 0;
    if (!parse_command_id(command->header.frame_id, &session_id, &sequence)) {
        invalid_command_count++;
        set_reject_reason(control_logic::BAD_SHAPE);
        return;
    }

    control_logic::Command queued_command{};
    queued_command.session_id = session_id;
    queued_command.sequence = sequence;
    for (size_t joint = 0; joint < control_logic::kJointCount; ++joint) {
        queued_command.target[joint] = command->position.data[joint];
    }
    const servo_bus::Stats& servo_stats = servo_bus::stats();
    const bool bus_ready = servo_calibration_ok && servo_stats.response_mask == 0x3f;
    const control_logic::Output output = controller.on_command(
        queued_command, measured_positions(), bus_ready, millis());
    command_count++;
    last_command_ms = millis();
    set_reject_reason(output.reject_reason);
    if (output.should_arm) {
        pending_arm_request = true;
    }
}

void publish_joint_state() {
    const uint32_t now_ms = millis();
    state_msg.header.stamp.sec = static_cast<int32_t>(now_ms / 1000U);
    state_msg.header.stamp.nanosec = (now_ms % 1000U) * 1000000U;
    state_msg.position.data = pos_data;
    state_msg.position.size = 6;
    last_publish_rc = rcl_publish(&state_pub, &state_msg, NULL);
    publish_count++;
}

void publish_status() {
    const servo_bus::Stats& servo_stats = servo_bus::stats();
    const uint32_t now_ms = millis();
    status_data[0] = 1;
    status_data[1] = static_cast<int32_t>(controller.state());
    status_data[2] = static_cast<int32_t>(controller.session_id());
    status_data[3] = static_cast<int32_t>(controller.last_received_sequence());
    status_data[4] = static_cast<int32_t>(controller.last_applied_sequence());
    status_data[5] = command_count > 0 ? static_cast<int32_t>(now_ms - last_command_ms) : 0;
    status_data[6] = servo_stats.response_mask;
    status_data[7] = last_reject_reason_code;
    status_data[8] = static_cast<int32_t>(controller.command_timeout_count());
    status_data[9] = static_cast<int32_t>(invalid_command_count);
    status_data[10] = static_cast<int32_t>(controller.control_reject_count());
    status_data[11] = static_cast<int32_t>(servo_stats.read_errors);
    status_data[12] = static_cast<int32_t>(servo_stats.write_errors);
    status_data[13] = WiFi.RSSI();
    last_status_rc = rcl_publish(&status_pub, &status_msg, NULL);
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

    const agent_discovery::Agent agent = agent_discovery::discover();
    char agent_host[16] = {};
    const String agent_ip_text = agent.ip.toString();
    agent_ip_text.toCharArray(agent_host, sizeof(agent_host));
    const uint16_t agent_port = agent.port;
    Serial.printf("Agent: %s:%u\n", agent_host, static_cast<unsigned>(agent_port));

    initialize_joint_messages();

    // micro-ROS: wait for the Agent before allocating entities. Retrying a
    // partially initialized rclc stack leaks scarce ESP32-C3 memory.
    set_microros_wifi_transports(
        (char*)WIFI_SSID, (char*)WIFI_PASS, agent_host, agent_port);
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
    TRY("status publisher", rclc_publisher_init_best_effort(&status_pub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32MultiArray), "follower_status"));
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

    // Keep actuator updates at 50 Hz and publish state/status at 20 Hz.
    unsigned long t = 0;
    unsigned long last_publish = millis();
    unsigned long last_servo_read = millis();
    unsigned long last_control_tick = millis();
    unsigned long last_status = millis();
    unsigned long last_diagnostics = millis();
    unsigned long wifi_lost_since = 0;
    unsigned long last_agent_liveness_ms = millis();
    uint8_t agent_liveness_failures = 0;
    while (true) {
        rcl_ret_t spin_rc = rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
        if (spin_rc != RCL_RET_OK && spin_rc != RCL_RET_TIMEOUT) {
            spin_error_count++;
            rcl_reset_error();
            Serial.println("micro-ROS Agent lost; restarting for rediscovery.");
            delay(100);
            ESP.restart();
        }
        if (millis() - last_servo_read >= 50) {
            last_servo_read += 50;
            servo_bus::read_all(pos_data);
        }
        if (millis() - last_control_tick >= 20) {
            last_control_tick += 20;
            const servo_bus::Stats& servo_stats = servo_bus::stats();
            const bool bus_ready = servo_calibration_ok &&
                servo_stats.response_mask == 0x3f;
            if (pending_arm_request) {
                pending_arm_request = false;
                const bool success = bus_ready && servo_bus::arm_at_current_position(pos_data);
                controller.report_write_result(success);
                set_reject_reason(success ? control_logic::NONE : control_logic::WRITE_FAILED);
                if (success) {
                    Serial.println("Servo control ARMED at measured position.");
                } else {
                    Serial.println("Control command rejected: arm write failed.");
                }
            } else {
                const control_logic::Output output = controller.tick(
                    millis(), measured_positions(), bus_ready);
                set_reject_reason(output.reject_reason);
                if (output.should_write) {
                    const bool success = servo_bus::write_positions(output.applied_target.data());
                    controller.report_write_result(success);
                    set_reject_reason(success ? control_logic::NONE : control_logic::WRITE_FAILED);
                }
            }
        }
        if (millis() - last_publish >= 50) {
            last_publish += 50;
            publish_joint_state();
        }
        if (millis() - last_status >= 50) {
            last_status += 50;
            publish_status();
        }
        if (millis() - last_diagnostics >= 60000) {
            last_diagnostics += 60000;
            servo_calibration_ok = print_servo_diagnostics();
        }
        if (millis() - last_agent_liveness_ms >= AGENT_LIVENESS_PERIOD_MS) {
            last_agent_liveness_ms += AGENT_LIVENESS_PERIOD_MS;
            if (rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, 1) == RMW_RET_OK) {
                agent_liveness_failures = 0;
            } else {
                agent_liveness_failures++;
                Serial.printf("micro-ROS Agent liveness failure %u/%u\n",
                    static_cast<unsigned>(agent_liveness_failures),
                    static_cast<unsigned>(AGENT_LIVENESS_FAILURE_LIMIT));
                if (agent_liveness_failures >= AGENT_LIVENESS_FAILURE_LIMIT) {
                    Serial.println("micro-ROS Agent liveness failed; restarting for rediscovery.");
                    delay(100);
                    ESP.restart();
                }
            }
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
            Serial.printf("OK RSSI:%d uptime:%lu pub:%lu pub_rc:%d cmd:%lu state:%d timeout:%lu invalid:%lu reject:%lu spin_err:%lu age:%lu servo_mask:0x%02x calib:%d armed:%d servo_ok:%lu servo_err:%lu write_ok:%lu write_err:%lu\n",
                WiFi.RSSI(), (millis() - wifi_start) / 1000,
                (unsigned long) publish_count, last_publish_rc,
                (unsigned long) command_count,
                static_cast<int>(controller.state()),
                (unsigned long) controller.command_timeout_count(),
                (unsigned long) invalid_command_count,
                (unsigned long) controller.control_reject_count(),
                (unsigned long) spin_error_count,
                command_count > 0 ? millis() - last_command_ms : 0,
                servo_stats.response_mask,
                servo_calibration_ok ? 1 : 0,
                controller.state() == control_logic::ACTIVE ? 1 : 0,
                (unsigned long) servo_stats.read_success,
                (unsigned long) servo_stats.read_errors,
                (unsigned long) servo_stats.write_success,
                (unsigned long) servo_stats.write_errors);
        }
    }
}

void loop() {}
