#include "control_logic.h"

#include <algorithm>
#include <cmath>

namespace control_logic {
namespace {

constexpr double kMinimumDtSeconds = 0.001;
constexpr double kMaximumDtSeconds = 0.050;
constexpr double kTargetEpsilon = 1e-9;

bool finite_target(const JointArray& target) {
    for (double value : target) {
        if (!std::isfinite(value)) {
            return false;
        }
    }
    return true;
}

}  // namespace

Controller::Controller()
    : state_(WAITING_HANDSHAKE),
      last_reject_reason_(NONE),
      session_id_(0),
      last_received_sequence_(0),
      last_applied_sequence_(0),
      last_command_ms_(0),
      pending_arm_sequence_(0),
      pending_final_sequence_(0),
      last_output_write_sequence_(0),
      command_timeout_count_(0),
      invalid_command_count_(0),
      control_reject_count_(0),
      has_received_sequence_(false),
      pending_arm_(false),
      pending_final_target_(false),
      has_tick_(false),
      last_tick_ms_(0),
      desired_target_(),
      applied_target_() {
    desired_target_.fill(0.0);
    applied_target_.fill(0.0);
}

Output Controller::make_output(RejectReason reason) const {
    Output output{};
    output.state = state_;
    output.reject_reason = reason;
    output.should_arm = false;
    output.should_write = false;
    output.final_target = false;
    output.write_sequence = 0;
    output.last_received_sequence = last_received_sequence_;
    output.last_applied_sequence = last_applied_sequence_;
    output.applied_target = applied_target_;
    return output;
}

bool Controller::near_pose(const JointArray& first, const JointArray& second) const {
    for (size_t joint = 0; joint < kJointCount; ++joint) {
        if (std::abs(first[joint] - second[joint]) > kHandshakeToleranceRad) {
            return false;
        }
    }
    return true;
}

bool Controller::newer_sequence(uint32_t sequence) const {
    return !has_received_sequence_ ||
        static_cast<int32_t>(sequence - last_received_sequence_) > 0;
}

void Controller::clear_pending_output() {
    pending_arm_ = false;
    pending_arm_sequence_ = 0;
    pending_final_target_ = false;
    pending_final_sequence_ = 0;
    last_output_write_sequence_ = 0;
}

Output Controller::on_command(const Command& command, const JointArray& measured,
                              bool bus_ready, uint32_t now_ms) {
    if (!finite_target(command.target)) {
        invalid_command_count_++;
        last_reject_reason_ = NONFINITE;
        return make_output(NONFINITE);
    }

    if (!bus_ready) {
        last_reject_reason_ = BUS_NOT_READY;
        control_reject_count_++;
        state_ = BUS_FAULT;
        clear_pending_output();
        return make_output(BUS_NOT_READY);
    }

    if (state_ == BUS_FAULT) {
        state_ = WAITING_HANDSHAKE;
        session_id_ = 0;
        has_received_sequence_ = false;
    }

    if (state_ == ACTIVE && command.session_id == session_id_ &&
        !newer_sequence(command.sequence)) {
        last_reject_reason_ = STALE_COMMAND;
        control_reject_count_++;
        return make_output(STALE_COMMAND);
    }

    if (state_ == ACTIVE && command.session_id != session_id_) {
        state_ = WAITING_HANDSHAKE;
        session_id_ = 0;
        has_received_sequence_ = false;
        clear_pending_output();
    }

    if (state_ != ACTIVE) {
        if (!near_pose(command.target, measured)) {
            last_reject_reason_ = HANDSHAKE_MISMATCH;
            control_reject_count_++;
            return make_output(HANDSHAKE_MISMATCH);
        }
        state_ = WAITING_HANDSHAKE;
        session_id_ = command.session_id;
        last_received_sequence_ = command.sequence;
        has_received_sequence_ = true;
        last_command_ms_ = now_ms;
        desired_target_ = measured;
        applied_target_ = measured;
        pending_arm_ = true;
        pending_arm_sequence_ = command.sequence;
        last_reject_reason_ = NONE;
        Output output = make_output();
        output.should_arm = true;
        output.write_sequence = command.sequence;
        return output;
    }

    session_id_ = command.session_id;
    last_received_sequence_ = command.sequence;
    has_received_sequence_ = true;
    last_command_ms_ = now_ms;
    desired_target_ = command.target;
    last_reject_reason_ = NONE;
    if (near_pose(desired_target_, applied_target_)) {
        last_applied_sequence_ = command.sequence;
    }
    return make_output();
}

Output Controller::tick(uint32_t now_ms, const JointArray& measured, bool bus_ready) {
    if (!bus_ready) {
        if (state_ == ACTIVE) {
            state_ = BUS_FAULT;
            clear_pending_output();
        }
        last_reject_reason_ = BUS_NOT_READY;
        return make_output(BUS_NOT_READY);
    }

    if (state_ == BUS_FAULT) {
        state_ = WAITING_HANDSHAKE;
        session_id_ = 0;
        has_received_sequence_ = false;
        clear_pending_output();
        return make_output();
    }

    if (state_ == ACTIVE && now_ms - last_command_ms_ > kCommandTimeoutMs) {
        state_ = HOLDING_TIMEOUT;
        desired_target_ = applied_target_;
        command_timeout_count_++;
        clear_pending_output();
        last_reject_reason_ = NONE;
        return make_output();
    }

    if (state_ != ACTIVE) {
        return make_output();
    }

    const uint32_t elapsed_ms = has_tick_ ? now_ms - last_tick_ms_ : 20;
    const double dt = std::clamp(elapsed_ms / 1000.0,
                                 kMinimumDtSeconds, kMaximumDtSeconds);
    has_tick_ = true;
    last_tick_ms_ = now_ms;
    (void)measured;

    Output output = make_output();
    output.should_write = false;
    pending_final_target_ = false;
    pending_final_sequence_ = 0;
    for (size_t joint = 0; joint < kJointCount; ++joint) {
        const double difference = desired_target_[joint] - applied_target_[joint];
        const double maximum_step = kMaxVelocityRadS[joint] * dt;
        const double step = std::clamp(difference, -maximum_step, maximum_step);
        applied_target_[joint] += step;
        if (std::abs(step) > kTargetEpsilon) {
            output.should_write = true;
        }
    }
    output.applied_target = applied_target_;
    output.write_sequence = last_received_sequence_;
    output.final_target = near_pose(desired_target_, applied_target_);
    if (output.final_target && output.should_write) {
        pending_final_target_ = true;
        pending_final_sequence_ = last_received_sequence_;
    }
    if (!output.final_target || !output.should_write) {
        pending_final_target_ = false;
        pending_final_sequence_ = 0;
    }
    last_output_write_sequence_ = output.should_write ? output.write_sequence : 0;
    return output;
}

void Controller::report_write_result(bool success) {
    if (!success) {
        state_ = BUS_FAULT;
        last_reject_reason_ = WRITE_FAILED;
        control_reject_count_++;
        clear_pending_output();
        return;
    }
    if (pending_arm_) {
        state_ = ACTIVE;
        last_applied_sequence_ = pending_arm_sequence_;
        clear_pending_output();
        last_reject_reason_ = NONE;
        return;
    }
    if (pending_final_target_) {
        last_applied_sequence_ = pending_final_sequence_;
        pending_final_target_ = false;
        pending_final_sequence_ = 0;
    }
    last_reject_reason_ = NONE;
    last_output_write_sequence_ = 0;
}

State Controller::state() const { return state_; }
uint32_t Controller::session_id() const { return session_id_; }
uint32_t Controller::last_received_sequence() const { return last_received_sequence_; }
uint32_t Controller::last_applied_sequence() const { return last_applied_sequence_; }
RejectReason Controller::last_reject_reason() const { return last_reject_reason_; }
uint32_t Controller::command_timeout_count() const { return command_timeout_count_; }
uint32_t Controller::invalid_command_count() const { return invalid_command_count_; }
uint32_t Controller::control_reject_count() const { return control_reject_count_; }

}  // namespace control_logic
