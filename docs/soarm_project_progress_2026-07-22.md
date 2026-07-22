# SO-ARM101 无线遥操项目进度总结

日期：2026-07-22

## 项目目标

使用普通舵机驱动板将 SO-ARM101 主臂连接到 Ubuntu 笔记本，通过 LeRobot 读取主臂动作；从臂使用 Seeed Studio XIAO ESP32-C3 总线舵机适配板，通过 micro-ROS WiFi UDP 接收控制，实现无线主从遥操。后续将从臂倒挂安装在无人机下方，由两名操作者分别控制无人机和机械臂。

当前通信结构：

```text
SO-ARM101 主臂
    ↓ 普通 USB 舵机驱动板
Ubuntu 22.04 笔记本（LeRobot + ROS2 Humble）
    ↓ micro-ROS / WiFi UDP
XIAO ESP32-C3 总线舵机适配板
    ↓ 1 Mbps UART 总线
SO-ARM101 从臂
```

## 今日总体成果

项目已经达到“可用于比赛桌面演示的无线主从遥操”阶段：主从臂完成重新校准，新从臂固件完成烧录，六个关节能够稳定无线跟随，响应速度已经接近 LeRobot 有线遥操，并完成一键启动脚本。

| 任务 | 状态 |
|---|---|
| 新从臂重新校准 | 已完成 |
| 主臂重新校准 | 已完成 |
| 新校准参数适配 XIAO 固件 | 已完成 |
| XIAO 固件编译、烧录和诊断 | 已完成 |
| XIAO 拔掉 USB 后无线独立运行 | 已完成 |
| LeRobot 主臂到 micro-ROS 从臂桥接 | 已完成 |
| 主从关节对应与跟随验证 | 已完成 |
| 跟随速度优化 | 已完成 |
| 一键启动及重复启动保护 | 已完成 |
| 无线距离与干扰测试 | 待完成 |
| 无人机安装和飞行测试 | 待无人机到货 |

## 1. 从臂重新校准

从臂使用普通 USB 舵机驱动板重新完成 LeRobot 校准，校准 ID 为 `follower_recal`。

校准文件：

```text
/home/linao/so101_lerobot/cali/follower_recal.json
```

校准结果：

| 关节 | ID | Homing Offset | MIN | MAX |
|---|---:|---:|---:|---:|
| shoulder_pan | 1 | -1073 | 793 | 3384 |
| shoulder_lift | 2 | -1917 | 789 | 3189 |
| elbow_flex | 3 | 1029 | 864 | 3135 |
| wrist_flex | 4 | -81 | 834 | 3206 |
| wrist_roll | 5 | -940 | 0 | 4095 |
| gripper | 6 | 311 | 1656 | 3189 |

校准程序只要求手动记录五个关节，是因为 `wrist_roll` 被自动设置为完整范围 `0～4095`。

## 2. 主臂重新校准

主臂使用普通 USB 舵机驱动板重新完成 LeRobot 校准，校准 ID 为 `leader_recal`。

校准文件：

```text
/home/linao/so101_lerobot/cali/leader_recal.json
```

校准结果：

| 关节 | ID | Homing Offset | MIN | MAX |
|---|---:|---:|---:|---:|
| shoulder_pan | 1 | 1076 | 728 | 3464 |
| shoulder_lift | 2 | -1029 | 775 | 3178 |
| elbow_flex | 3 | -61 | 891 | 3139 |
| wrist_flex | 4 | -33 | 863 | 3238 |
| wrist_roll | 5 | 1855 | 0 | 4095 |
| gripper | 6 | 1997 | 1671 | 3002 |

重新校准后，主从臂前四个主体关节的有效行程已经比较接近，改善了之前二号关节跟随偏差明显的问题。

## 3. XIAO 固件校准适配

XIAO PlatformIO 项目：

```text
/home/linao/soarm_xiao_test
```

舵机控制文件：

```text
/home/linao/soarm_xiao_test/src/servo_bus.cpp
```

固件已经改为使用 `follower_recal.json` 中的六个舵机 ID、Homing Offset、最小位置和最大位置。固件启动后会读取舵机 EEPROM 并进行一致性检查；校准不匹配时拒绝写入舵机。

烧录后的诊断结果：

- `servo_mask=0x3f`：六个舵机全部在线。
- `calib=1`：舵机 EEPROM 与固件校准完全一致。
- 舵机读取错误为 0。
- WiFi RSSI 约为 `-37～-44 dBm`。
- `/joint_states` 稳定发布约 20 Hz。
- XIAO USB-C 拔除后，适配板依靠外部 5V 电源继续无线运行。

## 4. 无线遥操桥接

桥接程序：

```text
/home/linao/so101_lerobot/tools/wireless_teleoperate.py
```

主要功能：

- 通过 LeRobot 读取 USB 主臂。
- 订阅无线从臂 `/joint_states`。
- 发布 `/joint_command`。
- 默认加载 `leader_recal.json` 和 `follower_recal.json`。
- 支持相对映射和绝对映射，比赛演示默认使用相对映射。
- 启动时以双方当前位置为基准，不会突然跳到固定姿态。
- 检查从臂反馈超时。
- 限制关节校准范围和单次命令变化。
- 从臂重启后必须通过当前位置握手才能重新启用控制。

当前话题：

```text
/joint_states   sensor_msgs/msg/JointState  从臂反馈，约20 Hz
/joint_command  sensor_msgs/msg/JointState  从臂目标位置
```

## 5. 跟随速度优化

最初无线遥操能够工作，但跟随明显偏慢。定位到两层人工限速：

```text
XIAO固件：speed=100，acceleration=10
电脑桥接：每周期最多变化0.05 rad
```

标准 LeRobot 从臂主要同步写入 `Goal_Position`，不会在每条命令中强制写入上述低速参数。因此完成以下改动：

- 不再使用会同时改写速度和加速度的 `SyncWritePosEx`。
- 改为只同步写两字节 `Goal_Position`。
- 启用控制时将舵机加速度设置为 `254`。
- 清除旧固件留下的 `Goal_Velocity=100` 限制。
- 遥操命令频率从 20 Hz 提高到 30 Hz。
- 电脑端单周期最大变化提高到 `0.24 rad`。
- 固件仍保留 `0.25 rad` 单周期拒绝阈值。
- 校准范围、首次握手和舵机在线检查全部保留。

实测结果：无线跟随速度已经接近 LeRobot 有线遥操，动作效果良好。

## 6. 一键启动

一键启动脚本：

```text
/home/linao/so101_lerobot/start_soarm_demo.sh
```

启动命令：

```bash
cd /home/linao/so101_lerobot
./start_soarm_demo.sh
```

只检查环境、不启动遥操：

```bash
./start_soarm_demo.sh --check
```

停止遥操：

```text
Ctrl+C
```

脚本会自动完成：

- 检查当前 WiFi 是否为 `vivoX100s`。
- 检查电脑 IP 是否为固件预设的 `10.133.64.21`。
- 使用主臂驱动板稳定设备路径，而不是易变化的 `/dev/ttyACM0`。
- 检查主从臂校准文件。
- 检查或启动 UDP 8888 的 micro-ROS agent。
- 等待 `/joint_states` 上线。
- 使用相对映射、30 Hz 和 `0.24 rad` 步进启动遥操。
- 失败时输出中文故障提示。

主臂稳定设备路径：

```text
/dev/serial/by-id/usb-1a86_USB_Single_Serial_5A4B048657-if00
```

## 7. 今日遇到并解决的问题

### ROS 环境脚本与 Bash 严格模式冲突

`/opt/ros/humble/setup.bash` 会读取可选的未定义变量，与 `set -u` 冲突。现已在加载 ROS 环境时临时关闭 `nounset`，加载完成后立即恢复。

### 重复遥操进程抢占主臂串口

测试时同时运行了两个遥操进程，两个程序同时读取 Feetech 总线，导致一号舵机型号被错误读取为 `2090`，而不是正确型号 `777`。舵机本身没有损坏，这是串口响应被并发读取造成的数据错误。

一键脚本已经增加运行锁：已有遥操实例运行时，第二次启动会直接退出并提示先在原终端按 `Ctrl+C`。

## 8. 通信方案决策

讨论和比较了普通 2.4 GHz WiFi、5 GHz WiFi、蜂窝 5G、ESP-NOW LR、LoRa、ELRS/CRSF 和数传电台。

比赛演示阶段决定：

- 继续使用现有 micro-ROS WiFi UDP，不在比赛前更换通信架构。
- 当前使用手机热点 `vivoX100s`。
- 如果比赛现场手机热点不稳定，再更换专用 2.4 GHz 便携路由器。
- ESP-NOW LR 等方案作为比赛后的升级方向。

## 9. 当前状态

记录本文档时：

- micro-ROS agent 正在 UDP 8888 上运行。
- XIAO 无线从臂持续发布 `/joint_states`。
- 无线遥操进程已停止。
- `/joint_command` 当前没有发布者。
- 从臂保持最后目标位置，不会继续跟随主臂。
- 一键脚本的预检和完整启动流程均已验证。

## 10. 尚未完成

- 通信失联的明显状态提示。
- 电脑、XIAO 和从臂全部断电后的冷启动恢复测试。
- 5、10、20、30 米无线距离测试。
- 无人机电机和电调工作时的 EMI 干扰测试。
- 无人机倒挂安装后的关节方向和范围验证。
- 无人机侧供电、BEC、电流余量和接地方案。
- 比赛现场一页式操作与故障处理说明。
- 实际低高度悬停和两人协同演示。

## 11. 下一步计划

1. 增加通信失联提示和安全状态显示。
2. 测试电脑重启、XIAO 重启、从臂断电重连后的完整恢复流程。
3. 在地面依次进行 5、10、20、30 米距离测试。
4. 整理比赛现场启动、停止、急停和故障处理说明。
5. 无人机到货后安装倒挂从臂，检查方向、重心、供电和结构强度。
6. 先进行不开桨地面联调，再做低高度悬停测试。
7. 最后验证两人协同操作：一人控制无人机，一人通过主臂控制从臂。

## 常用命令

启动比赛演示：

```bash
cd /home/linao/so101_lerobot
./start_soarm_demo.sh
```

单独启动 micro-ROS agent：

```bash
snap run micro-ros-agent udp4 --port 8888
```

检查从臂反馈频率：

```bash
source /opt/ros/humble/setup.bash
ros2 topic hz /joint_states
```

检查从臂反馈内容：

```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /joint_states --once
```
