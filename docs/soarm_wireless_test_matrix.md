# SO-ARM101 无线可靠性测试矩阵

本矩阵是 SO-ARM101 主从遥操作的分阶段验收记录。测试必须按 1 到 10 的顺序执行；任一闸门失败，都要先修复并重新验证，不能跳到下一闸门。机械臂测试时保持机械支撑、清空运动空间，并由操作员随时准备断开舵机电源。

截至 2026-09-06，本文档中的 PC-only、原生固件和 ESP32-C3 编译证据已保存；需要真实机械臂、舵机电源或 WiFi 状态变化的闸门仍标记为“未执行”。没有实机观察和证据文件，不把它们写成通过。

## 控制协议和安全边界

### 控制状态

| 数值 | 状态 | 含义 |
|---:|---|---|
| 0 | `WAITING_HANDSHAKE` | 尚未用当前测量姿态完成无跳变握手 |
| 1 | `ACTIVE` | 当前会话有效，允许按速度上限向目标移动 |
| 2 | `HOLDING_TIMEOUT` | 超过 500 ms 未收到命令，保持最后已应用目标 |
| 3 | `BUS_FAULT` | 舵机总线或写入失败，禁止继续写目标 |

### 拒绝原因

| 数值 | 原因 |
|---:|---|
| 0 | `NONE` |
| 1 | `BAD_SHAPE` |
| 2 | `BAD_NAME` |
| 3 | `NONFINITE` |
| 4 | `OUT_OF_RANGE` |
| 5 | `STALE_COMMAND` |
| 6 | `BUS_NOT_READY` |
| 7 | `HANDSHAKE_MISMATCH` |
| 8 | `WRITE_FAILED` |

命令 ID 放在 `sensor_msgs/msg/JointState.header.frame_id`，格式为
`S1:<session_id>:<sequence>`，实际传输使用两个 8 位十六进制字段，例如
`S1:89abcdef:10203040`。会话 ID 在恢复时重新生成；序列号按无符号 32 位回绕比较，旧会话的命令不能重新激活从臂。

### `/follower_status` 状态数组

主题类型为 `std_msgs/msg/Int32MultiArray`，固定 14 个整数，顺序如下：

| 下标 | 字段 |
|---:|---|
| 0 | `version` |
| 1 | `state` |
| 2 | `session_id` |
| 3 | `last_received_sequence` |
| 4 | `last_applied_sequence` |
| 5 | `command_age_ms` |
| 6 | `response_mask`，正常为 `0x3f` |
| 7 | `reject_reason` |
| 8 | `command_timeout_count` |
| 9 | `invalid_command_count` |
| 10 | `control_reject_count` |
| 11 | `read_errors` |
| 12 | `write_errors` |
| 13 | `rssi_dbm` |

固件控制 tick 为 50 Hz，关节状态和从臂状态发布为 20 Hz。超时阈值为 500 ms；首次握手要求每个关节与当前回读姿态的差值不超过 0.05 rad。每个控制 tick 的最大速度为：`shoulder_pan=0.8`、`shoulder_lift=0.8`、`elbow_flex=0.8`、`wrist_flex=1.2`、`wrist_roll=1.5`、`gripper=1.5` rad/s。

停止桥接程序后，从臂保留最后一个已应用目标；物理紧急停止是移除舵机电源，而不是依赖软件停止命令。

## 分阶段闸门

每一行都要补齐：测试日期、固件 Git commit、测试操作员、电源安排、结果和证据路径。这里的“未执行”不是通过；在硬件证据补齐前，不得发布“实机测试通过”的结论。

| 闸门 | 测试与通过标准 | 日期 | 固件 commit | 操作员 | 电源安排 | 结果 | 证据路径 |
|---:|---|---|---|---|---|---|---|
| 1 | PC-only pytest 和 lint；可靠性相关测试全部通过 | 2026-09-06 | `edf76d7` | Codex | 无硬件 | 通过（可靠性范围）；全仓库 baseline 另有既有 OpenCV PNG fixture 失败 | 终端日志；`tests/tools/` |
| 2 | `pio test -e native`；状态机测试全部通过 | 2026-09-06 | `edf76d7` | Codex | 无硬件 | 通过，6/6 | `firmware/xiao_soarm/.pio/` |
| 3 | ESP32-C3 编译成功，不上传 | 2026-09-06 | `edf76d7` | Codex | 无硬件 | 通过；未烧录 | `firmware/xiao_soarm/.pio/` |
| 4 | XIAO 仅 USB 供电、舵机电源断开；确认 ROS entities 和 `/follower_status` 发布 | 2026-09-08 | `68ad76b` | linao | USB 供电，舵机电源断开 | 通过；状态持续发布，`response_mask=0x00`、`BUS_NOT_READY`，未发送运动命令 | `logs/gate-04/2026-09-08-usb-only.md` |
| 5 | 机械支撑从臂；首次握手无可见跳动 | 2026-09-08 | `68ad76b` | linao | 舵机电源接通，机械臂受支撑 | 通过；首次同步使用从臂实测姿态，操作员确认无可见跳动 | `logs/gate-05/2026-09-08-no-jump-handshake.md` |
| 6 | 单关节小动作，命令步长限制为 0.10 rad；方向正确且收到确认 | 2026-09-08 | `68ad76b` | linao | 舵机电源接通，机械臂受支撑，空间清空 | 通过；夹爪正向移动，其他五关节未动；响应掩码 `0x3f`，拒绝和读写错误均为 0 | `logs/gate-06/2026-09-08-gripper-step.md`; `logs/gate-06/gate6-20260908-175300.json` |
| 7 | 六关节慢动作；速度限制、温度、电压正常且无拒绝 | 待补 | 待补 | 待补 | 机械支撑，持续观察电源 | 未执行 | 待补：`logs/gate-07/` |
| 8 | 停止桥接超过 500 ms；进入 `HOLDING_TIMEOUT`、保持姿态并近当前姿态重新握手 | 待补 | 待补 | 待补 | 机械支撑，随时可断电 | 未执行 | 待补：`logs/gate-08/` |
| 9 | 禁用并恢复 WiFi；生成新会话且不重放旧目标 | 待补 | 待补 | 待补 | 机械支撑，网络可控 | 未执行 | 待补：`logs/gate-09/` |
| 10 | 连续运行 10 分钟；保存 CSV，零总线故障、零非法命令、零意外拒绝且无可见跳动 | 待补 | 待补 | 待补 | 机械支撑，监控温度/电压 | 未执行 | 待补：`logs/teleop_*.csv` |

## 可复现实验命令

```bash
./start_soarm_demo.sh
python tools/analyze_wireless_log.py logs/teleop_YYYYmmdd_HHMMSS.csv
cd firmware/xiao_soarm && pio test -e native
cd firmware/xiao_soarm && pio run -e seeed_xiao_esp32c3
```

开始硬件闸门前，先运行：

```bash
ros2 topic list | rg '/joint_command|/joint_states|/follower_status'
ros2 topic echo /follower_status --once
```

闸门 6 应使用 `--max-step-rad 0.10` 的受限实验配置；闸门 8 和 9 要保存状态数组、会话 ID、序列号和动作前后关节姿态。闸门 10 结束后使用分析器输出作为证据，并把 CSV 路径填回本表。

## 停止条件

出现以下任一情况立即停止后续修改或实机动作，并保存串口、ROS、CSV 和 Git 状态：双 publisher 超出内存限制、`Int32MultiArray` 类型支持缺失、首次握手出现可见跳动、超时/WiFi 恢复重放旧目标、响应掩码不是 `0x3f`、校准不匹配、或电压/温度诊断无效。
