from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_wireless_launcher_exports_project_root_for_bridge_imports():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()
    expected = 'PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$BRIDGE" ' + "\\"

    assert expected in launcher


def test_wireless_launcher_defaults_to_current_recalibrated_pair():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'FOLLOWER_CALIBRATION="${SOARM_FOLLOWER_CALIBRATION:-$CALIBRATION_DIR/my_follower.json}"' in launcher
    assert 'LEADER_ID="${SOARM_LEADER_ID:-my_leader}"' in launcher


def test_wireless_launcher_waits_for_topics_before_echoing_them():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert "wait_for_topic_message()" in launcher
    assert "ros2 topic list" in launcher


def test_wireless_launcher_allows_wifi_recovery_window_override():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    assert 'RECOVERY_TIMEOUT="${SOARM_RECOVERY_TIMEOUT:-15}"' in launcher
    assert '    --recovery-timeout "$RECOVERY_TIMEOUT" \\' in launcher


def test_check_mode_does_not_require_leader_hardware():
    launcher = (PROJECT_ROOT / "start_soarm_demo.sh").read_text()

    guarded_checks = """if ! $CHECK_ONLY; then
    [[ -f \"$CALIBRATION_DIR/$LEADER_ID.json\" ]] ||
        fail \"找不到主臂校准：$CALIBRATION_DIR/$LEADER_ID.json\"
    [[ -e \"$LEADER_PORT\" ]] ||
        fail \"没有检测到主臂驱动板。请连接普通 USB 舵机驱动板：$LEADER_PORT\"
fi"""
    assert guarded_checks in launcher
    assert 'echo "预检通过：从臂 WiFi、micro-ROS 和状态反馈均已就绪；未检查主臂"' in launcher
