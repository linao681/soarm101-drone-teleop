# XIAO ESP32-C3 无线从臂固件

本目录是 SO-ARM101 从臂的 PlatformIO 工程，使用 Seeed Studio XIAO ESP32-C3
总线舵机适配板，通过 micro-ROS WiFi UDP 控制 6 个 STS3215 舵机。

## 配置 WiFi

复制公开模板：

```bash
cp src/wifi_config.example.h src/wifi_config.h
```

然后编辑 `src/wifi_config.h`，填写：

```cpp
const char* WIFI_SSID = "YOUR_2G4_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* AGENT_IP = "YOUR_COMPUTER_IP";
```

`src/wifi_config.h` 已被 Git 忽略，不能提交到公开仓库。

## 编译与烧录

```bash
pio run
pio run --target upload
```

micro-ROS 静态库位于 `lib/microros/`，ESP32-C3 使用 `riscv32` 工具链。
舵机校准参数写在 `src/servo_bus.cpp` 中，用于启动时的 EEPROM 一致性检查。

## ROS 接口

```text
/joint_states   sensor_msgs/msg/JointState   从臂反馈，约20 Hz
/joint_command  sensor_msgs/msg/JointState   从臂目标位置
```

首次控制命令必须接近从臂当前回读姿态，之后固件会检查校准软限位和单次步进
上限。通信超时后保持最后目标位置。
