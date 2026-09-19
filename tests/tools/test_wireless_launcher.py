from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_wireless_launcher_exports_project_root_for_bridge_imports():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()
    expected = 'PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$BRIDGE" ' + "\\"

    assert expected in launcher


def test_wireless_launcher_defaults_to_current_recalibrated_pair():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'FOLLOWER_CALIBRATION="${SOARM_FOLLOWER_CALIBRATION:-$CALIBRATION_DIR/follower_recal.json}"' in launcher
    assert 'LEADER_ID="${SOARM_LEADER_ID:-leader_recal}"' in launcher


def test_wireless_launcher_waits_for_topics_before_echoing_them():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert "wait_for_topic_message()" in launcher
    assert "ros2 topic list" in launcher


def test_wireless_launcher_allows_wifi_recovery_window_override():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'RECOVERY_TIMEOUT="${SOARM_RECOVERY_TIMEOUT:-15}"' in launcher
    assert '    --recovery-timeout "$RECOVERY_TIMEOUT" \\' in launcher


def test_wireless_launcher_forwards_recovery_blend_duration():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'RECOVERY_BLEND_DURATION="${SOARM_RECOVERY_BLEND_DURATION:-1}"' in launcher
    assert '    --recovery-blend-duration "$RECOVERY_BLEND_DURATION" \\' in launcher


def test_check_mode_does_not_require_leader_hardware():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    guarded_checks = """if [[ "$LEADER_MODE" == "wired" && "$CHECK_ONLY" == false ]]; then
    [[ -f \"$CALIBRATION_DIR/$LEADER_ID.json\" ]] ||
        fail \"找不到主臂校准：$CALIBRATION_DIR/$LEADER_ID.json\"
    [[ -e \"$LEADER_PORT\" ]] ||
        fail \"没有检测到主臂驱动板。请连接普通 USB 舵机驱动板：$LEADER_PORT\"
fi"""
    assert guarded_checks in launcher
    assert 'echo "预检通过：从臂 WiFi、micro-ROS、状态反馈和所选主臂输入均已就绪；未启动舵机遥操"' in launcher


def test_launcher_defaults_to_wireless_and_keeps_explicit_modes():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'LEADER_MODE="wireless"' in launcher
    assert 'case "$1" in' in launcher
    assert '--leader)' in launcher
    assert 'wired|wireless' in launcher
    assert 'eval ' not in launcher


def test_launcher_checks_usb_and_calibration_only_for_wired_leader():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    wired_guard = 'if [[ "$LEADER_MODE" == "wired" && "$CHECK_ONLY" == false ]]; then'
    assert wired_guard in launcher
    guard_start = launcher.index(wired_guard)
    guard_end = launcher.index("fi", guard_start)
    wired_block = launcher[guard_start:guard_end]
    assert '[[ -f "$CALIBRATION_DIR/$LEADER_ID.json" ]]' in wired_block
    assert '[[ -e "$LEADER_PORT" ]]' in wired_block


def test_wireless_launcher_waits_for_leader_topics_and_does_not_pin_agent_ip():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'wait_for_topic_message /leader/raw_state' in launcher
    assert 'wait_for_topic_message /leader/status' in launcher
    assert "EXPECTED_AGENT_IP" not in launcher
    assert 'ip -4 -o address show dev "$WIFI_DEVICE"' in launcher
    assert 'BROADCAST_IP' in launcher


def test_wireless_launcher_parses_ros2_yaml_document_output():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert "parse_ros2_int_array_field" in launcher


def test_wireless_launcher_starts_discovery_with_computed_addresses():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'tools/soarm_agent_discovery.py' in launcher
    assert '--bind-ip "$CURRENT_IP"' in launcher
    assert '--broadcast-ip "$BROADCAST_IP"' in launcher
    assert 'for (i = 1; i <= NF; i++)' in launcher


def test_wireless_launcher_starts_discovery_for_wired_and_wireless_leaders():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    discovery_start = launcher.index('echo "[3/4] 正在启动 agent discovery')
    preceding_text = launcher[:discovery_start].rstrip()

    assert not preceding_text.endswith('if [[ "$LEADER_MODE" == "wireless" ]]; then')


def test_wireless_launcher_cleanup_only_terminates_owned_processes():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'STARTED_AGENT_PID=""' in launcher
    assert 'STARTED_DISCOVERY_PID=""' in launcher
    assert 'kill "$STARTED_AGENT_PID"' in launcher
    assert 'kill "$STARTED_DISCOVERY_PID"' in launcher
    assert 'pkill' not in launcher
    assert 'killall' not in launcher


def test_wireless_launcher_forwards_mode_and_one_second_leader_recovery():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert '    --leader-mode "$LEADER_MODE" \\' in launcher
    assert '    --leader-recovery-blend-duration "$LEADER_RECOVERY_BLEND_DURATION" \\' in launcher
