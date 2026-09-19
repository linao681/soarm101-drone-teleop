#include "servo_bus.h"

#include <cstdint>

#include <SCServo.h>

namespace servo_bus {
namespace {

constexpr uint32_t kBaudRate = 1000000;
constexpr uint16_t kExpectedModel = 777;
constexpr uint8_t kTorqueEnableRegister = 40;  // Torque_Enable
constexpr uint8_t kIds[kJointCount] = {1, 2, 3, 4, 5, 6};

// These are read from the bus at runtime. The constants only define the
// expected order and identity of the six leader actuators.
SMS_STS servos;
Stats bus_stats = {};
uint32_t bus_calibration_crc = 0;

int read_torque_enable(uint8_t id) {
    return servos.readByte(id, kTorqueEnableRegister);
}

int decode_sign_magnitude(int encoded, uint8_t sign_bit) {
    if (encoded < 0) {
        return encoded;
    }
    if (encoded & (1 << sign_bit)) {
        return -(encoded & ~(1 << sign_bit));
    }
    return encoded;
}

}  // namespace

void begin() {
    // XIAO ESP32-C3: adapter TX -> D7/RX, adapter RX <- D6/TX.
    Serial0.begin(kBaudRate, SERIAL_8N1, D7, D6);
    servos.pSerial = &Serial0;
    // Keep a failed read short so an unpowered actuator cannot starve ROS.
    servos.IOTimeOut = 4;
    delay(10);
}

leader_logic::BusSnapshot scan_and_disable_torque() {
    uint8_t response_mask = 0;
    uint8_t model_mask = 0;
    uint8_t torque_off_mask = 0;

    for (size_t joint = 0; joint < kJointCount; ++joint) {
        const uint8_t id = kIds[joint];
        const int model = servos.readWord(id, 3);
        if (model >= 0) {
            response_mask |= static_cast<uint8_t>(1U << joint);
            if (model == kExpectedModel) {
                model_mask |= static_cast<uint8_t>(1U << joint);
            }
        }

        if (servos.writeByte(id, kTorqueEnableRegister, 0) != 1) {
            bus_stats.torque_errors++;
        }
        const int torque = read_torque_enable(id);
        if (torque == 0) {
            torque_off_mask |= static_cast<uint8_t>(1U << joint);
        } else {
            bus_stats.torque_errors++;
        }
    }

    bus_stats.response_mask = response_mask;
    bus_stats.model_mask = model_mask;
    bus_stats.torque_off_mask = torque_off_mask;
    return leader_logic::BusSnapshot{
        response_mask, model_mask, torque_off_mask};
}

bool read_status() {
    uint8_t response_mask = 0;
    uint8_t model_mask = 0;
    uint8_t torque_off_mask = 0;
    leader_logic::CalibrationRecord records[kJointCount] = {};
    bool calibration_valid = true;

    for (size_t joint = 0; joint < kJointCount; ++joint) {
        const uint8_t id = kIds[joint];
        const int model = servos.readWord(id, 3);
        const int range_min = servos.readWord(id, 9);
        const int range_max = servos.readWord(id, 11);
        const int homing_offset = decode_sign_magnitude(
            servos.readWord(id, 31), 11);
        const int torque = read_torque_enable(id);
        const bool valid = model >= 0 && range_min >= 0 && range_max >= 0 &&
            homing_offset > -4096 && torque >= 0;

        if (valid) {
            response_mask |= static_cast<uint8_t>(1U << joint);
            if (model == kExpectedModel) {
                model_mask |= static_cast<uint8_t>(1U << joint);
            }
            if (torque == 0) {
                torque_off_mask |= static_cast<uint8_t>(1U << joint);
            }
            records[joint] = leader_logic::CalibrationRecord{
                id,
                static_cast<uint16_t>(model),
                static_cast<int16_t>(homing_offset),
                static_cast<uint16_t>(range_min),
                static_cast<uint16_t>(range_max),
            };
        } else {
            calibration_valid = false;
            bus_stats.read_errors++;
        }
    }

    bus_stats.response_mask = response_mask;
    bus_stats.model_mask = model_mask;
    bus_stats.torque_off_mask = torque_off_mask;
    if (calibration_valid) {
        bus_calibration_crc = leader_logic::calibration_crc32(
            records, kJointCount);
    } else {
        bus_calibration_crc = 0;
    }
    return calibration_valid;
}

bool read_all(int32_t positions[kJointCount]) {
    uint8_t response_mask = 0;
    bus_stats.read_cycles++;

    for (size_t joint = 0; joint < kJointCount; ++joint) {
        const int raw = servos.ReadPos(kIds[joint]);
        const bool valid_read = servos.Err == 0 && raw >= INT16_MIN && raw <= INT16_MAX;
        if (valid_read) {
            positions[joint] = static_cast<int32_t>(raw);
            response_mask |= static_cast<uint8_t>(1U << joint);
            bus_stats.read_success++;
        } else {
            positions[joint] = 0;
            bus_stats.read_errors++;
        }
    }

    bus_stats.response_mask = response_mask;
    return response_mask == 0x3f;
}

uint32_t calibration_crc32() {
    return bus_calibration_crc;
}

const Stats& stats() {
    return bus_stats;
}

}  // namespace servo_bus
