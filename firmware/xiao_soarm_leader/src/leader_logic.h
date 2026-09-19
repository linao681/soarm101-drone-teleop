#pragma once

#include <cstddef>
#include <cstdint>

namespace leader_logic {

constexpr uint8_t kValidMask = 0x3f;
constexpr uint8_t kBadReadLimit = 3;
constexpr uint8_t kGoodReadLimit = 10;
constexpr uint8_t kAgentLivenessFailureLimit = 5;

enum State : int32_t { STARTING = 0, WAITING_AGENT = 1, READY = 2, BUS_FAULT = 3 };

struct BusSnapshot {
    uint8_t response_mask;
    uint8_t model_mask;
    uint8_t torque_off_mask;
};

struct Output {
    State state;
    bool publish_sample;
    uint32_t sequence;
};

struct AgentHealth {
    bool connected;
    bool restart_requested;
};

class AgentWatchdog {
public:
    AgentHealth report_probe(bool reachable);

private:
    uint8_t consecutive_failures_ = 0;
};

struct CalibrationRecord {
    uint8_t id;
    uint16_t model;
    int16_t homing_offset;
    uint16_t range_min;
    uint16_t range_max;
};

class Controller {
public:
    explicit Controller(uint32_t initial_sequence = 0);
    void report_bus_check(const BusSnapshot& snapshot, uint32_t calibration_crc);
    void report_agent_connected(bool connected);
    Output report_read(uint8_t response_mask);
    State state() const;
    uint32_t calibration_crc() const;

private:
    bool bus_ready() const;
    bool complete_read(uint8_t response_mask) const;
    Output output(bool publish_sample);
    Output handle_good_read();

    State state_;
    BusSnapshot bus_snapshot_;
    uint32_t calibration_crc_;
    uint32_t sequence_;
    uint8_t bad_reads_;
    uint8_t good_reads_;
    bool agent_connected_;
};

uint32_t calibration_crc32(const CalibrationRecord* records, size_t count);

}  // namespace leader_logic
