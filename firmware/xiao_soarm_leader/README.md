# SO-101 wireless leader firmware

This dedicated XIAO ESP32-C3 firmware reads the six leader actuator positions,
confirms model identity and torque-off state, and publishes fixed-length
`std_msgs/msg/Int32MultiArray` messages:

- `/leader/raw_state` at 50 Hz, with 11 fields;
- `/leader/status` at 10 Hz, with 13 fields.

The leader has no ROS subscriptions and never writes actuator position, speed,
acceleration, homing, or limit registers. Its only actuator write is disabling
torque and confirming the readback.

## Local WiFi configuration

For a real device, copy `src/wifi_config.example.h` to
`src/wifi_config.h` and fill in the local SSID and password. The local file is
ignored by Git. If it is absent, PlatformIO uses the empty example values so a
credential-free compile can still verify the firmware; those values cannot
connect a device to WiFi.

## Build and test

```bash
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
```

These commands compile only. Uploading is intentionally a separate operation.
