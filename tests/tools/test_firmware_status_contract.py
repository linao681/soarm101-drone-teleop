from pathlib import Path

ROOT = Path(__file__).parents[2]
MAIN_CPP = ROOT / "firmware" / "xiao_soarm" / "src" / "main.cpp"
PLATFORMIO_INI = ROOT / "firmware" / "xiao_soarm" / "platformio.ini"


def test_firmware_declares_status_message_and_topic():
    source = MAIN_CPP.read_text()
    assert "std_msgs/msg/int32_multi_array.h" in source
    assert '"follower_status"' in source
    assert "status_data[14]" in source
    assert "status_msg" in source


def test_firmware_allocates_two_publishers():
    source = PLATFORMIO_INI.read_text()
    assert "-DRMW_UXRCE_MAX_PUBLISHERS=2" in source
