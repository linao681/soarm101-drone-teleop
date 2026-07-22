#pragma once

#include <Arduino.h>

namespace servo_bus {

constexpr size_t kJointCount = 6;

struct Stats {
    uint32_t read_cycles;
    uint32_t read_success;
    uint32_t read_errors;
    uint32_t write_success;
    uint32_t write_errors;
    uint8_t response_mask;
    bool torque_enabled;
};

struct Diagnostic {
    bool valid;
    int firmware_major;
    int firmware_minor;
    int model_number;
    int homing_offset;
    int range_min;
    int range_max;
    int torque_enabled;
    int voltage_tenths;
    int temperature_c;
    int present_position;
};

void begin();
uint8_t scan();
size_t read_diagnostics(Diagnostic output[kJointCount]);
bool calibration_matches(const Diagnostic diagnostics[kJointCount]);
bool read_all(double positions_rad[kJointCount]);
bool command_within_limits(const double positions_rad[kJointCount]);
bool arm_at_current_position(const double positions_rad[kJointCount]);
bool write_positions(const double positions_rad[kJointCount]);
void disable_torque();
const Stats& stats();

}  // namespace servo_bus
