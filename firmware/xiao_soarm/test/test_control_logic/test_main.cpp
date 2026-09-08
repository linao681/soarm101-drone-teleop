#include <array>

#include <unity.h>

#include "../../src/control_logic.h"

using namespace control_logic;

JointArray filled(double value) {
    JointArray result{};
    result.fill(value);
    return result;
}

JointArray zeros() {
    return filled(0.0);
}

Command command(uint32_t session, uint32_t sequence, const JointArray& target) {
    return Command{session, sequence, target};
}

Controller active_controller_at_zero(uint32_t session) {
    Controller controller;
    controller.on_command(command(session, 1, zeros()), zeros(), true, 0);
    controller.report_write_result(true);
    return controller;
}

void test_first_command_must_match_measured_pose() {
    Controller controller;
    const JointArray measured = zeros();
    const Command far = command(1, 1, filled(0.2));
    const Output output = controller.on_command(far, measured, true, 0);
    TEST_ASSERT_EQUAL(WAITING_HANDSHAKE, output.state);
    TEST_ASSERT_EQUAL(HANDSHAKE_MISMATCH, output.reject_reason);
}

void test_sequence_gap_does_not_reject_valid_target() {
    Controller controller = active_controller_at_zero(7);
    controller.on_command(command(7, 2, filled(0.1)), zeros(), true, 10);
    const Output output = controller.on_command(command(7, 4, filled(0.3)), zeros(), true, 20);
    TEST_ASSERT_EQUAL(ACTIVE, output.state);
    TEST_ASSERT_EQUAL_UINT32(4, output.last_received_sequence);
}

void test_out_of_order_command_is_rejected() {
    Controller controller = active_controller_at_zero(7);
    controller.on_command(command(7, 5, filled(0.1)), zeros(), true, 10);
    const Output output = controller.on_command(command(7, 4, filled(0.2)), zeros(), true, 20);
    TEST_ASSERT_EQUAL(STALE_COMMAND, output.reject_reason);
}

void test_timeout_holds_and_requires_new_handshake() {
    Controller controller = active_controller_at_zero(7);
    const Output timed_out = controller.tick(521, zeros(), true);
    TEST_ASSERT_EQUAL(HOLDING_TIMEOUT, timed_out.state);
    TEST_ASSERT_FALSE(timed_out.should_write);
    const Output resumed = controller.on_command(command(8, 1, zeros()), zeros(), true, 530);
    TEST_ASSERT_TRUE(resumed.should_arm);
}

void test_trajectory_obeys_velocity_limit() {
    Controller controller = active_controller_at_zero(7);
    controller.on_command(command(7, 2, filled(1.0)), zeros(), true, 0);
    const Output previous = controller.tick(0, zeros(), true);
    const Output current = controller.tick(20, zeros(), true);
    for (size_t joint = 0; joint < kJointCount; ++joint) {
        const double delta = current.applied_target[joint] - previous.applied_target[joint];
        TEST_ASSERT_TRUE(delta <= kMaxVelocityRadS[joint] * 0.020 + 1e-6);
    }
}

void test_summer_profile_applies_host_step_in_one_tick() {
    Controller controller = active_controller_at_zero(7);
    controller.on_command(command(7, 2, filled(0.24)), zeros(), true, 0);

    const Output output = controller.tick(20, zeros(), true);

    for (size_t joint = 0; joint < kJointCount; ++joint) {
        TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.24f, static_cast<float>(output.applied_target[joint]));
        TEST_ASSERT_TRUE(output.should_write);
    }
}

void test_bus_fault_prevents_writes() {
    Controller controller = active_controller_at_zero(7);
    const Output output = controller.tick(20, zeros(), false);
    TEST_ASSERT_EQUAL(BUS_FAULT, output.state);
    TEST_ASSERT_FALSE(output.should_write);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_first_command_must_match_measured_pose);
    RUN_TEST(test_sequence_gap_does_not_reject_valid_target);
    RUN_TEST(test_out_of_order_command_is_rejected);
    RUN_TEST(test_timeout_holds_and_requires_new_handshake);
    RUN_TEST(test_trajectory_obeys_velocity_limit);
    RUN_TEST(test_summer_profile_applies_host_step_in_one_tick);
    RUN_TEST(test_bus_fault_prevents_writes);
    return UNITY_END();
}
