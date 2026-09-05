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
pio test -e native
pio run -e seeed_xiao_esp32c3
pio run --target upload
```

回到仓库根目录后可分析遥操日志：

```bash
python tools/analyze_wireless_log.py logs/teleop_YYYYmmdd_HHMMSS.csv
```

micro-ROS 静态库位于 `lib/microros/`，ESP32-C3 使用 `riscv32` 工具链。
舵机校准参数写在 `src/servo_bus.cpp` 中，用于启动时的 EEPROM 一致性检查。
原生状态机测试和 ESP32-C3 编译通过前不要执行 upload；烧录前再次确认
`src/wifi_config.h` 只存在于本机且不会进入 Git。

## ROS 接口

```text
/joint_states   sensor_msgs/msg/JointState   从臂反馈，约20 Hz
/joint_command  sensor_msgs/msg/JointState   从臂目标位置
/follower_status std_msgs/msg/Int32MultiArray 可靠性状态，约20 Hz，固定14字段
```

首次控制命令必须接近从臂当前回读姿态，之后固件会检查校准软限位和单次步进
上限。控制 tick 为 50 Hz，首次握手容差为 0.05 rad，通信超时 500 ms 后保持最后目标位置。
停止桥接程序不会清除最后目标；物理紧急停止是移除舵机电源。完整状态码和分阶段
测试矩阵见 `../../docs/soarm_wireless_test_matrix.md`。
