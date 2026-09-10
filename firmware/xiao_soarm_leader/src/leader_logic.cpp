#include "leader_logic.h"

namespace leader_logic {
namespace {

constexpr uint32_t kCrcPolynomial = 0xedb88320u;

void crc_byte(uint32_t& crc, uint8_t value) {
    crc ^= value;
    for (int bit = 0; bit < 8; ++bit) {
        crc = (crc >> 1) ^ ((crc & 1u) ? kCrcPolynomial : 0u);
    }
}

}  // namespace

AgentHealth AgentWatchdog::report_probe(bool reachable) {
    if (reachable) {
        consecutive_failures_ = 0;
        return AgentHealth{true, false};
    }
    if (consecutive_failures_ < kAgentLivenessFailureLimit) {
        ++consecutive_failures_;
    }
    return AgentHealth{
        false,
        consecutive_failures_ >= kAgentLivenessFailureLimit,
    };
}

Controller::Controller(uint32_t initial_sequence)
    : state_(STARTING),
      bus_snapshot_{0, 0, 0},
      calibration_crc_(0),
      sequence_(initial_sequence),
      bad_reads_(0),
      good_reads_(0),
      agent_connected_(false) {}

bool Controller::bus_ready() const {
    return bus_snapshot_.response_mask == kValidMask &&
        bus_snapshot_.model_mask == kValidMask &&
        bus_snapshot_.torque_off_mask == kValidMask;
}

bool Controller::complete_read(uint8_t response_mask) const {
    return response_mask == kValidMask;
}

Output Controller::output(bool publish_sample) {
    return Output{state_, publish_sample, sequence_};
}

Output Controller::handle_good_read() {
    bad_reads_ = 0;
    if (state_ == READY) {
        ++sequence_;
        return output(true);
    }

    if (state_ == WAITING_AGENT || state_ == BUS_FAULT) {
        if (!bus_ready() || !agent_connected_) {
            return output(false);
        }
        if (good_reads_ < kGoodReadLimit) {
            ++good_reads_;
        }
        if (good_reads_ >= kGoodReadLimit) {
            state_ = READY;
            good_reads_ = 0;
            ++sequence_;
            return output(true);
        }
    }
    return output(false);
}

void Controller::report_bus_check(const BusSnapshot& snapshot, uint32_t calibration_crc) {
    bus_snapshot_ = snapshot;
    calibration_crc_ = calibration_crc;
    good_reads_ = 0;
    bad_reads_ = 0;

    if (!bus_ready()) {
        state_ = BUS_FAULT;
        return;
    }

    if (state_ == STARTING) {
        state_ = WAITING_AGENT;
    }
}

void Controller::report_agent_connected(bool connected) {
    agent_connected_ = connected;
    if (!connected) {
        good_reads_ = 0;
        bad_reads_ = 0;
        if (state_ == READY || state_ == WAITING_AGENT) {
            state_ = bus_ready() ? WAITING_AGENT : STARTING;
        }
        return;
    }

    if (state_ == STARTING && bus_ready()) {
        state_ = WAITING_AGENT;
    }
}

Output Controller::report_read(uint8_t response_mask) {
    if (complete_read(response_mask)) {
        return handle_good_read();
    }

    good_reads_ = 0;
    if (state_ == READY || state_ == WAITING_AGENT || state_ == BUS_FAULT) {
        if (bad_reads_ < kBadReadLimit) {
            ++bad_reads_;
        }
        if (bad_reads_ >= kBadReadLimit) {
            state_ = BUS_FAULT;
            return output(false);
        }
    }
    return output(false);
}

State Controller::state() const { return state_; }

uint32_t Controller::calibration_crc() const { return calibration_crc_; }

uint32_t calibration_crc32(const CalibrationRecord* records, size_t count) {
    uint32_t crc = 0xffffffffu;
    for (size_t index = 0; index < count; ++index) {
        const CalibrationRecord& record = records[index];
        crc_byte(crc, record.id);
        crc_byte(crc, static_cast<uint8_t>(record.model & 0xffu));
        crc_byte(crc, static_cast<uint8_t>((record.model >> 8) & 0xffu));
        const uint16_t homing_offset = static_cast<uint16_t>(record.homing_offset);
        crc_byte(crc, static_cast<uint8_t>(homing_offset & 0xffu));
        crc_byte(crc, static_cast<uint8_t>((homing_offset >> 8) & 0xffu));
        crc_byte(crc, static_cast<uint8_t>(record.range_min & 0xffu));
        crc_byte(crc, static_cast<uint8_t>((record.range_min >> 8) & 0xffu));
        crc_byte(crc, static_cast<uint8_t>(record.range_max & 0xffu));
        crc_byte(crc, static_cast<uint8_t>((record.range_max >> 8) & 0xffu));
    }
    return crc ^ 0xffffffffu;
}

}  // namespace leader_logic
