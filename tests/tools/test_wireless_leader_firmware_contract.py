from pathlib import Path


ROOT = Path(__file__).parents[2]
LEADER_SRC = ROOT / "firmware/xiao_soarm_leader/src"
PLATFORMIO = ROOT / "firmware/xiao_soarm_leader/platformio.ini"


def source_text() -> str:
    return "\n".join(path.read_text() for path in sorted(LEADER_SRC.glob("*.cpp")))


def platformio_text() -> str:
    return PLATFORMIO.read_text()


def test_leader_firmware_is_read_only_and_publishes_contract_topics():
    text = source_text()
    for required in (
        '"/leader/raw_state"',
        '"/leader/status"',
        "RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT",
        "LEADER_RAW_FIELD_COUNT = 11",
        "LEADER_STATUS_FIELD_COUNT = 13",
        "READ_PERIOD_MS = 20",
        "Torque_Enable",
        "read_torque_enable",
    ):
        assert required in text
    for forbidden in (
        "Goal_Position",
        "SMS_STS_GOAL_POSITION_L",
        "SyncWritePosEx",
        "write_positions",
        "rclc_subscription_init",
    ):
        assert forbidden not in text


def test_leader_build_disables_generated_micro_ros_subscriptions():
    assert "-DRMW_UXRCE_MAX_SUBSCRIPTIONS=0" in platformio_text()
    assert "-DRMW_UXRCE_MAX_SUBSCRIBERS=0" not in platformio_text()


def test_leader_accepts_signed_servo_positions_only_after_clean_read():
    text = source_text()
    assert "const bool valid_read = servos.Err == 0 && raw >= INT16_MIN && raw <= INT16_MAX;" in text
