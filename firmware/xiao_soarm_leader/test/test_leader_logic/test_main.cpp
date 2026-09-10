#include <cstdint>

#include <unity.h>

#include "../../src/leader_logic.h"

using namespace leader_logic;

static Controller ready_controller(uint32_t initial_sequence = 0) {
    Controller c(initial_sequence);
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    c.report_agent_connected(true);
    for (int i = 0; i < 10; ++i) c.report_read(0x3f);
    return c;
}

void test_ready_requires_bus_agent_and_ten_good_reads() {
    Controller c;
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    TEST_ASSERT_EQUAL(WAITING_AGENT, c.state());
    c.report_agent_connected(true);
    for (int i = 0; i < 9; ++i) TEST_ASSERT_FALSE(c.report_read(0x3f).publish_sample);
    const Output ready = c.report_read(0x3f);
    TEST_ASSERT_EQUAL(READY, ready.state);
    TEST_ASSERT_TRUE(ready.publish_sample);
    TEST_ASSERT_EQUAL_UINT32(1, ready.sequence);
}

void test_three_bad_reads_fault_and_ten_good_reads_recover() {
    Controller c = ready_controller();
    TEST_ASSERT_EQUAL(READY, c.report_read(0x00).state);
    TEST_ASSERT_EQUAL(READY, c.report_read(0x00).state);
    TEST_ASSERT_EQUAL(BUS_FAULT, c.report_read(0x00).state);
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    for (int i = 0; i < 9; ++i) {
        TEST_ASSERT_EQUAL(BUS_FAULT, c.report_read(0x3f).state);
    }
    TEST_ASSERT_EQUAL(READY, c.report_read(0x3f).state);
}

void test_missing_model_or_torque_mask_never_readies() {
    Controller missing_model;
    missing_model.report_agent_connected(true);
    missing_model.report_bus_check(BusSnapshot{0x3f, 0x1f, 0x3f}, 1);
    TEST_ASSERT_EQUAL(BUS_FAULT, missing_model.state());

    Controller torque_on;
    torque_on.report_agent_connected(true);
    torque_on.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x1f}, 1);
    TEST_ASSERT_EQUAL(BUS_FAULT, torque_on.state());
}

void test_sequence_wraps_from_uint32_max_to_zero() {
    Controller c = ready_controller(UINT32_MAX - 2);
    TEST_ASSERT_EQUAL_UINT32(UINT32_MAX, c.report_read(0x3f).sequence);
    TEST_ASSERT_EQUAL_UINT32(0, c.report_read(0x3f).sequence);
}

void test_crc_matches_python_vector() {
    const CalibrationRecord records[6] = {
        {1, 777, 1084, 694, 3349}, {2, 777, -1065, 804, 3220},
        {3, 777, 16, 795, 3080}, {4, 777, 133, 679, 3084},
        {5, 777, 1925, 0, 4095}, {6, 777, -1891, 1447, 2808},
    };
    TEST_ASSERT_EQUAL_HEX32(0x9d36c031, calibration_crc32(records, 6));
}

void test_agent_watchdog_stops_on_first_failure_and_restarts_after_five() {
    AgentWatchdog watchdog;

    AgentHealth health = watchdog.report_probe(false);
    TEST_ASSERT_TRUE(health.connected);
    TEST_ASSERT_FALSE(health.restart_requested);
    health = watchdog.report_probe(false);
    TEST_ASSERT_TRUE(health.connected);
    TEST_ASSERT_FALSE(health.restart_requested);
    health = watchdog.report_probe(false);
    TEST_ASSERT_TRUE(health.connected);
    TEST_ASSERT_FALSE(health.restart_requested);
    health = watchdog.report_probe(false);
    TEST_ASSERT_TRUE(health.connected);
    TEST_ASSERT_FALSE(health.restart_requested);
    health = watchdog.report_probe(false);
    TEST_ASSERT_FALSE(health.connected);
    TEST_ASSERT_TRUE(health.restart_requested);
}

void test_agent_watchdog_success_resets_consecutive_failures() {
    AgentWatchdog watchdog;

    watchdog.report_probe(false);
    watchdog.report_probe(false);
    AgentHealth health = watchdog.report_probe(true);
    TEST_ASSERT_TRUE(health.connected);
    TEST_ASSERT_FALSE(health.restart_requested);
    TEST_ASSERT_FALSE(watchdog.report_probe(false).restart_requested);
    TEST_ASSERT_FALSE(watchdog.report_probe(false).restart_requested);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_ready_requires_bus_agent_and_ten_good_reads);
    RUN_TEST(test_three_bad_reads_fault_and_ten_good_reads_recover);
    RUN_TEST(test_missing_model_or_torque_mask_never_readies);
    RUN_TEST(test_sequence_wraps_from_uint32_max_to_zero);
    RUN_TEST(test_crc_matches_python_vector);
    RUN_TEST(test_agent_watchdog_stops_on_first_failure_and_restarts_after_five);
    RUN_TEST(test_agent_watchdog_success_resets_consecutive_failures);
    return UNITY_END();
}
