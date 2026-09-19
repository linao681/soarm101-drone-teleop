# SO-ARM101 双无线主从遥操作与无人机机械臂实验

本项目基于 Hugging Face LeRobot、ROS 2 Humble、micro-ROS 和两块 Seeed Studio
XIAO ESP32-C3，实现 SO-ARM101 主臂与从臂的双无线遥操作。系统同时保留 USB
有线主臂回退模式，并已完成无人机初步搭载和简单空中抓取实验。

## 当前能力

- 无线主臂读取 6 个 STS3215 舵机位置，通过 Wi-Fi 发布主臂状态。
- 无线从臂接收目标位置、驱动 6 个舵机并反馈关节与可靠性状态。
- 电脑运行 ROS 2/micro-ROS 桥接程序，支持手机热点 IP 变化后的 agent 自动发现。
- 支持启动无跳变、序列号校验、旧命令拒绝、断线保持和恢复后平滑追赶。
- 支持 `wireless` 无线主臂与 `wired` USB 主臂两种输入模式。
- 每次遥操可记录 ACK 延迟、RSSI、反馈频率和关节跟踪误差 CSV 日志。
- 已进行无人机搭载机械臂的初步飞行和简单空中抓取验证。

## 系统链路

```text
主臂舵机
  ├─ 无线模式：主臂 XIAO ── Wi-Fi / micro-ROS ──┐
  └─ 有线模式：USB 舵机控制板 ──────────────────┤
                                                  ▼
                                      Ubuntu 遥操作桥接程序
                                                  │
                                         Wi-Fi / micro-ROS
                                                  ▼
                                       从臂 XIAO → 从臂舵机
```

无线主臂只读取位置并确保舵机扭矩关闭；从臂负责执行位置目标。电脑上的
`tools/wireless_teleoperate.py` 完成校准映射、会话握手、断线恢复和指标记录。

## 目录说明

- `start_soarm_demo.sh`：网络、micro-ROS、主从臂状态预检与一键启动。
- `tools/wireless_teleoperate.py`：有线/无线主臂到无线从臂的遥操作桥。
- `tools/soarm_agent_discovery.py`：向两个 XIAO 广播电脑当前 agent 地址。
- `firmware/xiao_soarm/`：无线从臂 XIAO ESP32-C3 固件。
- `firmware/xiao_soarm_leader/`：无线主臂 XIAO ESP32-C3 固件。
- `cali/`：当前主从臂校准文件。
- `tests/tools/`：协议、启动器、恢复逻辑和 README 契约测试。
- `docs/soarm_wireless_test_matrix.md`：分阶段实机测试矩阵。
- `logs/`：已保存的实机测试证据和指标日志。

## 环境要求

- Ubuntu 22.04
- ROS 2 Humble
- LeRobot Python 环境（当前项目使用 `lerobot_so101`）
- PlatformIO
- micro-ROS agent
- 2.4 GHz Wi-Fi 或手机热点
- 两块 XIAO ESP32-C3 总线舵机适配板（双无线模式）

## Wi-Fi 配置

分别复制主、从臂模板：

```bash
cp firmware/xiao_soarm/src/wifi_config.example.h \
  firmware/xiao_soarm/src/wifi_config.h
cp firmware/xiao_soarm_leader/src/wifi_config.example.h \
  firmware/xiao_soarm_leader/src/wifi_config.h
```

在两个本地 `wifi_config.h` 中填写相同的 2.4 GHz Wi-Fi 名称和密码。这两个文件
已被 Git 忽略，包含凭据，不能提交到公开仓库。XIAO 通过 discovery 获取电脑当前
IP，手机热点重新分配电脑地址时不需要把固定电脑 IP 写入固件。

启动器会把 NetworkManager 连接名称与 `SOARM_WIFI_SSID` 比较；默认使用该环境
变量的预设值。使用自定义网络时，启动前设置连接名称对应的 SSID，例如：

```bash
export SOARM_WIFI_SSID="your-network-name"
```

## 固件测试、编译与烧录

先验证再烧录无线从臂：

```bash
(cd firmware/xiao_soarm && \
  pio test -e native && \
  pio run -e seeed_xiao_esp32c3 && \
  pio run -e seeed_xiao_esp32c3 --target upload)
```

无线主臂：

```bash
(cd firmware/xiao_soarm_leader && \
  pio test -e native && \
  pio run -e seeed_xiao_esp32c3 && \
  pio run -e seeed_xiao_esp32c3 --target upload)
```

烧录前应确认连接的是对应 XIAO，并在接通舵机电源前完成 USB 冒烟检查。

## 快速启动

进入项目并激活环境：

```bash
cd so101_lerobot
conda activate lerobot_so101
```

双无线主从臂（默认模式）：

```bash
./start_soarm_demo.sh
# 等价于：
./start_soarm_demo.sh --leader wireless
```

USB 有线主臂 + 无线从臂回退模式：

```bash
./start_soarm_demo.sh --leader wired
```

只做预检，不启动舵机遥操：

```bash
./start_soarm_demo.sh --leader wireless --check
```

如需指定 LeRobot Python：

```bash
export SOARM_PYTHON=/path/to/lerobot_so101/bin/python
```

## 校准与安全

启动器执行本地校准结构和范围验证、舵机 EEPROM/固件快照检查。重新校准后同步更新校准文件和固件；不匹配时系统会拒绝进入控制。

启动前必须机械支撑机械臂、清空运动空间，并确保可以立即断开舵机电源。按
`Ctrl+C` 停止程序后，从臂保持最后位置；这不是物理急停。物理紧急停止方式是
移除舵机电源。

## 验证状态

已完成协议、状态机、启动预检、无跳变握手、断线恢复、有线回退和短时间双无线实机遥操验证；十分钟无线耐久测试尚未执行。完整测试顺序和证据要求见
[`docs/soarm_wireless_test_matrix.md`](docs/soarm_wireless_test_matrix.md)。

分析遥操日志：

```bash
python tools/analyze_wireless_log.py logs/teleop_YYYYmmdd_HHMMSS.csv
```

## 上游项目与许可证

本仓库基于 [Hugging Face LeRobot](https://github.com/huggingface/lerobot)，保留其
许可证、版权说明和贡献者文件。项目新增内容集中在 SO-ARM101 双无线遥操作、
micro-ROS 固件、可靠性机制以及无人机搭载实验。

详情请参阅 [LICENSE](LICENSE)、[CONTRIBUTING.md](CONTRIBUTING.md) 和上游
[LeRobot 文档](https://huggingface.co/docs/lerobot)。
