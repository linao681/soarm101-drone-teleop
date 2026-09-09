#include <Arduino.h>
#include <WiFi.h>
#include <esp_system.h>
#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rmw/qos_profiles.h>
#include <std_msgs/msg/int32_multi_array.h>

#if __has_include("wifi_config.h")
#include "wifi_config.h"
#else
#include "wifi_config.example.h"
#endif

#include "agent_discovery.h"
#include "leader_logic.h"
#include "servo_bus.h"

constexpr size_t LEADER_RAW_FIELD_COUNT = 11;
constexpr size_t LEADER_STATUS_FIELD_COUNT = 13;
constexpr uint32_t READ_PERIOD_MS = 20;
constexpr uint32_t STATUS_PERIOD_MS = 100;

rcl_publisher_t raw_state_pub;
rcl_publisher_t status_pub;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
std_msgs__msg__Int32MultiArray raw_state_msg;
std_msgs__msg__Int32MultiArray status_msg;
int32_t raw_state_data[LEADER_RAW_FIELD_COUNT] = {};
int32_t status_data[LEADER_STATUS_FIELD_COUNT] = {};
leader_logic::Controller controller(0);
uint32_t boot_session_id = 0;
uint32_t last_published_sequence = 0;
rcl_ret_t last_raw_publish_rc = RCL_RET_OK;
rcl_ret_t last_status_publish_rc = RCL_RET_OK;

void initialize_messages() {
    raw_state_msg.data.data = raw_state_data;
    raw_state_msg.data.size = LEADER_RAW_FIELD_COUNT;
    raw_state_msg.data.capacity = LEADER_RAW_FIELD_COUNT;

    status_msg.data.data = status_data;
    status_msg.data.size = LEADER_STATUS_FIELD_COUNT;
    status_msg.data.capacity = LEADER_STATUS_FIELD_COUNT;
}

void set_agent_host(const IPAddress& address, char output[16]) {
    snprintf(output, 16, "%u.%u.%u.%u",
        static_cast<unsigned>(address[0]),
        static_cast<unsigned>(address[1]),
        static_cast<unsigned>(address[2]),
        static_cast<unsigned>(address[3]));
}

void connect_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.setSleep(false);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nWiFi IP: %s RSSI: %d\n",
        WiFi.localIP().toString().c_str(), WiFi.RSSI());
}

bool initialize_microros(const leader_discovery::Discovery& discovery) {
    char agent_host[16] = {};
    set_agent_host(discovery.agent_ip(), agent_host);
    set_microros_wifi_transports(
        const_cast<char*>(WIFI_SSID), const_cast<char*>(WIFI_PASS),
        agent_host, discovery.agent_port());

    while (rmw_uros_ping_agent(500, 1) != RMW_RET_OK) {
        Serial.println("Waiting for micro-ROS Agent...");
        delay(1000);
    }

    allocator = rcl_get_default_allocator();
    if (rclc_support_init(&support, 0, nullptr, &allocator) != RCL_RET_OK) {
        return false;
    }
    if (rmw_uros_set_context_entity_creation_session_timeout(
            rcl_context_get_rmw_context(&support.context), 0) != RCL_RET_OK) {
        return false;
    }
    if (rclc_node_init_default(&node, "so101_leader", "", &support) != RCL_RET_OK) {
        return false;
    }

    rmw_qos_profile_t qos = rmw_qos_profile_default;
    qos.reliability = RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT;
    qos.history = RMW_QOS_POLICY_HISTORY_KEEP_LAST;
    qos.depth = 1;
    if (rclc_publisher_init(&raw_state_pub, &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32MultiArray),
            "/leader/raw_state", &qos) != RCL_RET_OK) {
        return false;
    }
    if (rclc_publisher_init(&status_pub, &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32MultiArray),
            "/leader/status", &qos) != RCL_RET_OK) {
        return false;
    }
    return true;
}

void publish_raw_state(const int32_t positions[servo_bus::kJointCount],
                       uint32_t sequence, uint32_t now_ms) {
    raw_state_data[0] = 1;
    raw_state_data[1] = static_cast<int32_t>(boot_session_id);
    raw_state_data[2] = static_cast<int32_t>(sequence);
    raw_state_data[3] = static_cast<int32_t>(now_ms);
    raw_state_data[4] = servo_bus::stats().response_mask;
    for (size_t joint = 0; joint < servo_bus::kJointCount; ++joint) {
        raw_state_data[5 + joint] = positions[joint];
    }
    last_raw_publish_rc = rcl_publish(&raw_state_pub, &raw_state_msg, nullptr);
    last_published_sequence = sequence;
}

void publish_status(uint32_t now_ms) {
    const servo_bus::Stats& bus_stats = servo_bus::stats();
    status_data[0] = 1;
    status_data[1] = static_cast<int32_t>(controller.state());
    status_data[2] = static_cast<int32_t>(boot_session_id);
    status_data[3] = static_cast<int32_t>(last_published_sequence);
    status_data[4] = bus_stats.response_mask;
    status_data[5] = bus_stats.model_mask;
    status_data[6] = bus_stats.torque_off_mask;
    status_data[7] = static_cast<int32_t>(servo_bus::calibration_crc32());
    status_data[8] = static_cast<int32_t>(bus_stats.read_cycles);
    status_data[9] = static_cast<int32_t>(bus_stats.read_errors);
    status_data[10] = static_cast<int32_t>(bus_stats.torque_errors);
    status_data[11] = static_cast<int32_t>(now_ms);
    status_data[12] = WiFi.RSSI();
    last_status_publish_rc = rcl_publish(&status_pub, &status_msg, nullptr);
}

leader_logic::BusSnapshot current_bus_snapshot() {
    const servo_bus::Stats& bus_stats = servo_bus::stats();
    return leader_logic::BusSnapshot{
        bus_stats.response_mask,
        bus_stats.model_mask,
        bus_stats.torque_off_mask,
    };
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("=== SO-101 wireless leader ===");

    boot_session_id = esp_random();
    servo_bus::begin();
    servo_bus::scan_and_disable_torque();
    servo_bus::read_status();
    controller.report_bus_check(
        current_bus_snapshot(), servo_bus::calibration_crc32());

    connect_wifi();
    leader_discovery::Discovery discovery;
    discovery.begin();
    while (!discovery.has_agent()) {
        discovery.poll();
        delay(10);
    }
    Serial.printf("Agent: %s:%u\n", discovery.agent_ip().toString().c_str(),
        static_cast<unsigned>(discovery.agent_port()));

    initialize_messages();
    if (!initialize_microros(discovery)) {
        Serial.println("micro-ROS initialization failed; restarting.");
        delay(1000);
        ESP.restart();
    }
    controller.report_agent_connected(true);

    uint32_t last_read_ms = millis();
    uint32_t last_status_ms = last_read_ms;
    uint32_t last_bus_check_ms = last_read_ms;
    int32_t positions[servo_bus::kJointCount] = {};

    while (true) {
        const uint32_t now_ms = millis();
        if (static_cast<uint32_t>(now_ms - last_read_ms) >= READ_PERIOD_MS) {
            last_read_ms += READ_PERIOD_MS;
            const bool complete = servo_bus::read_all(positions);
            const leader_logic::Output output = controller.report_read(
                servo_bus::stats().response_mask);
            if (complete && output.publish_sample) {
                publish_raw_state(positions, output.sequence, now_ms);
            }
        }

        if (controller.state() == leader_logic::BUS_FAULT &&
            static_cast<uint32_t>(now_ms - last_bus_check_ms) >= 1000) {
            last_bus_check_ms = now_ms;
            servo_bus::scan_and_disable_torque();
            servo_bus::read_status();
            controller.report_bus_check(
                current_bus_snapshot(), servo_bus::calibration_crc32());
        }

        if (static_cast<uint32_t>(now_ms - last_status_ms) >= STATUS_PERIOD_MS) {
            last_status_ms += STATUS_PERIOD_MS;
            publish_status(now_ms);
        }
        delay(1);
    }
}

void loop() {}
