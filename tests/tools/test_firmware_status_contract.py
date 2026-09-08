import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
MAIN_CPP = ROOT / "firmware" / "xiao_soarm" / "src" / "main.cpp"
PLATFORMIO_INI = ROOT / "firmware" / "xiao_soarm" / "platformio.ini"
SERVO_BUS_CPP = ROOT / "firmware" / "xiao_soarm" / "src" / "servo_bus.cpp"
FOLLOWER_CALIBRATION = ROOT / "cali" / "my_follower.json"


def test_firmware_declares_status_message_and_topic():
    source = MAIN_CPP.read_text()
    assert "std_msgs/msg/int32_multi_array.h" in source
    assert '"follower_status"' in source
    assert "status_data[14]" in source
    assert "status_msg" in source


def test_firmware_allocates_two_publishers():
    source = PLATFORMIO_INI.read_text()
    assert "-DRMW_UXRCE_MAX_PUBLISHERS=2" in source


def _firmware_calibration_array(source: str, name: str) -> list[int]:
    match = re.search(
        rf"constexpr int16_t {name}\[kJointCount\]\s*=\s*\{{([^}}]+)\}};",
        source,
    )
    assert match is not None, f"missing firmware calibration array: {name}"
    return [int(value.strip()) for value in match.group(1).split(",")]


def test_firmware_calibration_matches_active_follower_file():
    source = SERVO_BUS_CPP.read_text()
    calibration = json.loads(FOLLOWER_CALIBRATION.read_text())
    joints = sorted(calibration.values(), key=lambda joint: joint["id"])

    assert _firmware_calibration_array(source, "kHomingOffsets") == [
        joint["homing_offset"] for joint in joints
    ]
    assert _firmware_calibration_array(source, "kRangeMin") == [joint["range_min"] for joint in joints]
    assert _firmware_calibration_array(source, "kRangeMax") == [joint["range_max"] for joint in joints]
