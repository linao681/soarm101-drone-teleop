#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace control_logic {

constexpr size_t kJointCount = 6;
constexpr uint32_t kCommandTimeoutMs = 500;
constexpr double kHandshakeToleranceRad = 0.05;
constexpr double kMaxVelocityRadS[kJointCount] = {
    12.0, 12.0, 12.0, 12.0, 12.0, 12.0
};

enum State : int32_t {
    WAITING_HANDSHAKE = 0,
    ACTIVE = 1,
    HOLDING_TIMEOUT = 2,
    BUS_FAULT = 3,
};

enum RejectReason : int32_t {
    NONE = 0,
    BAD_SHAPE = 1,
    BAD_NAME = 2,
    NONFINITE = 3,
    OUT_OF_RANGE = 4,
    STALE_COMMAND = 5,
    BUS_NOT_READY = 6,
    HANDSHAKE_MISMATCH = 7,
    WRITE_FAILED = 8,
};

using JointArray = std::array<double, kJointCount>;

struct Command {
    uint32_t session_id;
    uint32_t sequence;
    JointArray target;
};

struct Output {
    State state;
    RejectReason reject_reason;
    bool should_arm;
    bool should_write;
    bool final_target;
    uint32_t write_sequence;
    uint32_t last_received_sequence;
    uint32_t last_applied_sequence;
    JointArray applied_target;
};

class Controller {
public:
    Controller();

    Output on_command(const Command& command, const JointArray& measured,
                      bool bus_ready, uint32_t now_ms);
    Output tick(uint32_t now_ms, const JointArray& measured, bool bus_ready);
    void report_write_result(bool success);

    State state() const;
    uint32_t session_id() const;
    uint32_t last_received_sequence() const;
    uint32_t last_applied_sequence() const;
    RejectReason last_reject_reason() const;
    uint32_t command_timeout_count() const;
    uint32_t invalid_command_count() const;
    uint32_t control_reject_count() const;

private:
    Output make_output(RejectReason reason = NONE) const;
    bool near_pose(const JointArray& first, const JointArray& second) const;
    bool newer_sequence(uint32_t sequence) const;
    void clear_pending_output();

    State state_;
    RejectReason last_reject_reason_;
    uint32_t session_id_;
    uint32_t last_received_sequence_;
    uint32_t last_applied_sequence_;
    uint32_t last_command_ms_;
    uint32_t pending_arm_sequence_;
    uint32_t pending_final_sequence_;
    uint32_t last_output_write_sequence_;
    uint32_t command_timeout_count_;
    uint32_t invalid_command_count_;
    uint32_t control_reject_count_;
    bool has_received_sequence_;
    bool pending_arm_;
    bool pending_final_target_;
    bool has_tick_;
    uint32_t last_tick_ms_;
    JointArray desired_target_;
    JointArray applied_target_;
};

}  // namespace control_logic
