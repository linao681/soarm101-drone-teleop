#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROS_SETUP="/opt/ros/humble/setup.bash"
if [[ -x "${SOARM_PYTHON:-}" ]]; then
    PYTHON="$SOARM_PYTHON"
elif [[ -x "/home/linao/miniforge3/envs/lerobot_so101/bin/python" ]]; then
    PYTHON="/home/linao/miniforge3/envs/lerobot_so101/bin/python"
else
    PYTHON="python3"
fi
BRIDGE="$PROJECT_DIR/tools/wireless_teleoperate.py"
CALIBRATION_DIR="$PROJECT_DIR/cali"
FOLLOWER_CALIBRATION="${SOARM_FOLLOWER_CALIBRATION:-$CALIBRATION_DIR/my_follower.json}"

# These values match the WiFi transport compiled into the XIAO firmware.
EXPECTED_WIFI_SSID="${SOARM_WIFI_SSID:-vivoX100s}"
EXPECTED_AGENT_IP="${SOARM_AGENT_IP:-10.141.235.21}"
AGENT_PORT="${SOARM_AGENT_PORT:-8888}"

# Use the controller's stable USB identity instead of the changing ttyACM number.
DEFAULT_LEADER_PORT="/dev/serial/by-id/usb-1a86_USB_Single_Serial_5A4B048657-if00"
LEADER_PORT="${SOARM_LEADER_PORT:-$DEFAULT_LEADER_PORT}"
LEADER_ID="${SOARM_LEADER_ID:-my_leader}"

AGENT_LOG_DIR="$PROJECT_DIR/logs"
AGENT_LOG="$AGENT_LOG_DIR/micro_ros_agent.log"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
METRICS_LOG="$AGENT_LOG_DIR/teleop_${RUN_ID}.csv"
RECOVERY_TIMEOUT="${SOARM_RECOVERY_TIMEOUT:-15}"
STARTED_AGENT_PID=""
CHECK_ONLY=false

if [[ "${1:-}" == "--check" ]]; then
    CHECK_ONLY=true
elif [[ $# -ne 0 ]]; then
    echo "用法: $0 [--check]" >&2
    exit 2
fi

cleanup() {
    if [[ -n "$STARTED_AGENT_PID" ]] && kill -0 "$STARTED_AGENT_PID" 2>/dev/null; then
        kill "$STARTED_AGENT_PID" 2>/dev/null || true
        wait "$STARTED_AGENT_PID" 2>/dev/null || true
    fi
    if [[ -f "$METRICS_LOG" ]]; then
        echo "指标日志分析命令：$PYTHON $PROJECT_DIR/tools/analyze_wireless_log.py $METRICS_LOG"
    fi
}
trap cleanup EXIT

fail() {
    echo
    echo "启动失败：$*" >&2
    exit 1
}

wait_for_topic_message() {
    local topic="$1"
    local deadline=$((SECONDS + 15))

    while (( SECONDS < deadline )); do
        if ros2 topic list 2>/dev/null | grep -Fxq "$topic"; then
            if timeout 2s ros2 topic echo "$topic" --once >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 1
    done

    return 124
}

# Hold an advisory lock for the whole run. Two bridge processes reading the
# same Feetech serial bus can corrupt replies and produce false model numbers.
exec 9>"/tmp/soarm_wireless_teleop.lock"
if ! flock -n 9; then
    fail "无线遥操已经在运行，请先在原终端按 Ctrl+C 停止"
fi

echo "=== SO-ARM101 无线遥操启动 ==="

[[ -r "$ROS_SETUP" ]] || fail "找不到 ROS2 Humble：$ROS_SETUP"
[[ -x "$PYTHON" ]] || fail "找不到 lerobot_so101 Python：$PYTHON"
[[ -f "$BRIDGE" ]] || fail "找不到遥操程序：$BRIDGE"
[[ -f "$FOLLOWER_CALIBRATION" ]] || \
    fail "找不到从臂校准：$FOLLOWER_CALIBRATION"
if ! $CHECK_ONLY; then
    [[ -f "$CALIBRATION_DIR/$LEADER_ID.json" ]] ||
        fail "找不到主臂校准：$CALIBRATION_DIR/$LEADER_ID.json"
    [[ -e "$LEADER_PORT" ]] ||
        fail "没有检测到主臂驱动板。请连接普通 USB 舵机驱动板：$LEADER_PORT"
fi

WIFI_DEVICE="$(
    nmcli -t -f DEVICE,TYPE,STATE device status |
        awk -F: '$2 == "wifi" && $3 == "connected" { print $1; exit }'
)"
[[ -n "$WIFI_DEVICE" ]] || fail "电脑没有连接 WiFi"

CURRENT_SSID="$(nmcli -g GENERAL.CONNECTION device show "$WIFI_DEVICE")"
CURRENT_IP="$(
    ip -4 -o address show dev "$WIFI_DEVICE" |
        awk 'NR == 1 { split($4, address, "/"); print address[1] }'
)"

[[ "$CURRENT_SSID" == "$EXPECTED_WIFI_SSID" ]] || \
    fail "当前 WiFi 是 '$CURRENT_SSID'，XIAO 固件需要 '$EXPECTED_WIFI_SSID'"
[[ "$CURRENT_IP" == "$EXPECTED_AGENT_IP" ]] || \
    fail "电脑当前 IP 是 '$CURRENT_IP'，XIAO 固件需要 '$EXPECTED_AGENT_IP'"

echo "[1/4] 网络正常：$CURRENT_SSID，电脑 IP $CURRENT_IP"
if $CHECK_ONLY; then
    echo "[2/4] --check 模式：跳过主臂硬件检查"
else
    echo "[2/4] 主臂驱动板：$LEADER_PORT -> $(readlink -f "$LEADER_PORT")"
fi

# ROS setup files legitimately probe optional unset variables, so temporarily
# relax nounset while sourcing them and restore strict mode immediately after.
set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
set -u
mkdir -p "$AGENT_LOG_DIR"

if pgrep -f "[m]icro_ros_agent.*udp4.*--port ${AGENT_PORT}" >/dev/null; then
    echo "[3/4] micro-ROS agent 已运行：UDP $AGENT_PORT"
else
    echo "[3/4] 正在启动 micro-ROS agent：UDP $AGENT_PORT"
    snap run micro-ros-agent udp4 --port "$AGENT_PORT" -v4 \
        >"$AGENT_LOG" 2>&1 &
    STARTED_AGENT_PID=$!
    sleep 1
    kill -0 "$STARTED_AGENT_PID" 2>/dev/null || \
        fail "micro-ROS agent 启动失败，请查看 $AGENT_LOG"
fi

echo "[4/4] 等待无线从臂上线……"
if ! wait_for_topic_message /joint_states; then
    fail "15 秒内没有收到 /joint_states。请检查从臂 5V 电源、XIAO 天线和手机热点"
fi
if ! wait_for_topic_message /follower_status; then
    fail "收到关节状态，但没有 /follower_status；请确认 XIAO 已烧录可靠性固件"
fi

if $CHECK_ONLY; then
    echo "预检通过：从臂 WiFi、micro-ROS 和状态反馈均已就绪；未检查主臂"
    echo "--check 完成，未启动舵机遥操"
    exit 0
fi

echo "预检通过：主臂、从臂、WiFi、micro-ROS 和从臂状态反馈均已就绪"

echo
echo "本次指标日志：$METRICS_LOG"
echo "即将从双方当前位置无跳变启动，按 Ctrl+C 停止。"
echo "从臂停止后会保持最后位置。"
echo

PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$BRIDGE" \
    --leader-port "$LEADER_PORT" \
    --leader-id "$LEADER_ID" \
    --calibration-dir "$CALIBRATION_DIR" \
    --follower-calibration "$FOLLOWER_CALIBRATION" \
    --mapping-mode relative \
    --rate 30 \
    --max-step-rad 0.24 \
    --recovery-timeout "$RECOVERY_TIMEOUT" \
    --metrics-csv "$METRICS_LOG"
