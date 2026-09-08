#include "servo_bus.h"

#include <SCServo.h>
#include <math.h>

namespace servo_bus {
namespace {

constexpr uint32_t kBaudRate = 1000000;
constexpr double kTwoPi = 6.28318530717958647692;
constexpr double kResolution = 4096.0;
constexpr uint8_t kLeRobotAcceleration = 254;

// Snapshot from /home/linao/so101_lerobot/cali/my_follower.json.
// Present_Position already has
// Homing_Offset applied by the servo, so angle conversion must not apply the
// offset a second time. The offsets are retained here for identity/safety
// checks when write control is enabled.
constexpr uint8_t kIds[kJointCount] = {1, 2, 3, 4, 5, 6};
constexpr int16_t kHomingOffsets[kJointCount] = {
    -1100, -1947, 1051, -208, 151, 315
};
constexpr int16_t kRangeMin[kJointCount] = {
    839, 798, 814, 947, 0, 1611
};
constexpr int16_t kRangeMax[kJointCount] = {
    3240, 3235, 3122, 3364, 4095, 3214
};

SMS_STS servos;
Stats bus_stats = {};

double raw_to_radians(int raw, size_t joint) {
    (void)joint;
    return (raw - kResolution / 2.0) * (kTwoPi / kResolution);
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

long radians_to_raw(double radians, size_t joint) {
    (void)joint;
    const double raw = radians * kResolution / kTwoPi
        + kResolution / 2.0;
    return lround(raw);
}

}  // namespace

void begin() {
    // XIAO ESP32-C3: adapter TX -> D7/RX, adapter RX <- D6/TX.
    Serial0.begin(kBaudRate, SERIAL_8N1, D7, D6);
    servos.pSerial = &Serial0;
    // A 1 Mbps reply arrives in well under 1 ms. Keep a failed read short so
    // an unpowered/missing servo cannot starve the micro-ROS executor.
    servos.IOTimeOut = 4;
    delay(10);
}

uint8_t scan() {
    uint8_t mask = 0;
    for (size_t i = 0; i < kJointCount; ++i) {
        if (servos.Ping(kIds[i]) == kIds[i]) {
            mask |= static_cast<uint8_t>(1U << i);
        }
    }
    bus_stats.response_mask = mask;
    return mask;
}

size_t read_diagnostics(Diagnostic output[kJointCount]) {
    size_t valid_count = 0;
    for (size_t i = 0; i < kJointCount; ++i) {
        Diagnostic& d = output[i];
        d.firmware_major = servos.readByte(kIds[i], 0);
        d.firmware_minor = servos.readByte(kIds[i], 1);
        d.model_number = servos.readWord(kIds[i], 3);
        d.range_min = servos.readWord(kIds[i], 9);
        d.range_max = servos.readWord(kIds[i], 11);
        d.homing_offset = decode_sign_magnitude(
            servos.readWord(kIds[i], 31), 11);
        d.torque_enabled = servos.readByte(kIds[i], 40);
        d.voltage_tenths = servos.ReadVoltage(kIds[i]);
        d.temperature_c = servos.ReadTemper(kIds[i]);
        d.present_position = servos.ReadPos(kIds[i]);
        d.valid = d.firmware_major >= 0 && d.firmware_minor >= 0 &&
            d.model_number >= 0 && d.range_min >= 0 && d.range_max >= 0 &&
            d.homing_offset > -4096 && d.torque_enabled >= 0 &&
            d.voltage_tenths >= 0 && d.temperature_c >= 0 &&
            d.present_position >= 0;
        if (d.valid) {
            ++valid_count;
        }
    }
    return valid_count;
}

bool calibration_matches(const Diagnostic diagnostics[kJointCount]) {
    for (size_t i = 0; i < kJointCount; ++i) {
        const Diagnostic& d = diagnostics[i];
        if (!d.valid || d.model_number != 777 ||
            d.homing_offset != kHomingOffsets[i] ||
            d.range_min != kRangeMin[i] || d.range_max != kRangeMax[i]) {
            return false;
        }
    }
    return true;
}

bool read_all(double positions_rad[kJointCount]) {
    uint8_t mask = 0;
    bus_stats.read_cycles++;

    for (size_t i = 0; i < kJointCount; ++i) {
        const int raw = servos.ReadPos(kIds[i]);
        if (raw >= 0 && raw < static_cast<int>(kResolution)) {
            positions_rad[i] = raw_to_radians(raw, i);
            mask |= static_cast<uint8_t>(1U << i);
            bus_stats.read_success++;
        } else {
            bus_stats.read_errors++;
        }
    }

    bus_stats.response_mask = mask;
    return mask == 0x3f;
}

bool command_within_limits(const double positions_rad[kJointCount]) {
    for (size_t i = 0; i < kJointCount; ++i) {
        if (!isfinite(positions_rad[i])) {
            return false;
        }
        const long raw = radians_to_raw(positions_rad[i], i);
        if (raw < kRangeMin[i] || raw > kRangeMax[i]) {
            return false;
        }
    }
    return true;
}

bool write_positions(const double positions_rad[kJointCount]) {
    if (!command_within_limits(positions_rad)) {
        bus_stats.write_errors++;
        return false;
    }

    // LeRobot writes only the two-byte Goal_Position register. In particular,
    // do not use SyncWritePosEx here: that also rewrites Goal_Velocity and
    // Acceleration on every command and previously limited the arm to speed
    // 100 / acceleration 10.
    u8 goal_positions[kJointCount * 2];
    for (size_t i = 0; i < kJointCount; ++i) {
        const uint16_t raw = static_cast<uint16_t>(
            radians_to_raw(positions_rad[i], i));
        goal_positions[i * 2] = static_cast<u8>(raw & 0xff);
        goal_positions[i * 2 + 1] = static_cast<u8>((raw >> 8) & 0xff);
    }
    servos.syncWrite(
        const_cast<u8*>(kIds), static_cast<u8>(kJointCount),
        SMS_STS_GOAL_POSITION_L, goal_positions, 2);
    bus_stats.write_success++;
    return true;
}

void disable_torque() {
    for (size_t i = 0; i < kJointCount; ++i) {
        servos.EnableTorque(kIds[i], 0);
    }
    bus_stats.torque_enabled = false;
}

bool arm_at_current_position(const double positions_rad[kJointCount]) {
    // Match the runtime settings applied by LeRobot's FeetechMotorsBus. A
    // velocity value of zero removes the speed=100 value left by the previous
    // firmware, while acceleration 254 matches configure_motors().
    for (size_t i = 0; i < kJointCount; ++i) {
        if (servos.writeByte(kIds[i], SMS_STS_ACC,
                kLeRobotAcceleration) != 1 ||
            servos.writeWord(kIds[i], SMS_STS_GOAL_SPEED_L, 0) != 1) {
            bus_stats.write_errors++;
            return false;
        }
    }

    // Program each goal to the measured pose before enabling torque. This
    // prevents a stale goal register from causing a jump when torque turns on.
    if (!write_positions(positions_rad)) {
        return false;
    }

    for (size_t i = 0; i < kJointCount; ++i) {
        if (servos.EnableTorque(kIds[i], 1) != 1) {
            bus_stats.write_errors++;
            disable_torque();
            return false;
        }
    }
    bus_stats.torque_enabled = true;
    return true;
}

const Stats& stats() {
    return bus_stats;
}

}  // namespace servo_bus
