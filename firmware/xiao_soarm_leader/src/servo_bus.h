#pragma once

#include <Arduino.h>

#include "leader_logic.h"

namespace servo_bus {

constexpr size_t kJointCount = 6;

struct Stats {
    uint32_t read_cycles;
    uint32_t read_success;
    uint32_t read_errors;
    uint32_t torque_errors;
    uint8_t response_mask;
    uint8_t model_mask;
    uint8_t torque_off_mask;
};

void begin();
leader_logic::BusSnapshot scan_and_disable_torque();
bool read_status();
bool read_all(int32_t positions[kJointCount]);
uint32_t calibration_crc32();
const Stats& stats();

}  // namespace servo_bus
