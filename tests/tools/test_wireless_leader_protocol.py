import json
from pathlib import Path

import pytest

from tools.soarm_wireless.leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
    load_leader_calibration,
    normalize_leader_raw,
    parse_ros2_int_array_field,
)


CALIBRATION = {
    "shoulder_pan": {"id": 1, "drive_mode": 0, "homing_offset": 1084, "range_min": 694, "range_max": 3349},
    "shoulder_lift": {"id": 2, "drive_mode": 0, "homing_offset": -1065, "range_min": 804, "range_max": 3220},
    "elbow_flex": {"id": 3, "drive_mode": 0, "homing_offset": 16, "range_min": 795, "range_max": 3080},
    "wrist_flex": {"id": 4, "drive_mode": 0, "homing_offset": 133, "range_min": 679, "range_max": 3084},
    "wrist_roll": {"id": 5, "drive_mode": 0, "homing_offset": 1925, "range_min": 0, "range_max": 4095},
    "gripper": {"id": 6, "drive_mode": 0, "homing_offset": -1891, "range_min": 1447, "range_max": 2808},
}


def test_current_leader_calibration_has_stable_crc():
    assert leader_calibration_crc32(CALIBRATION) == 0x9D36C031


def test_raw_state_decodes_signed_positions_and_unsigned_ids():
    state = LeaderRawState.from_array([1, -1, -2, 1234, 63, -20, 100, 200, 300, 4095, 5000])
    assert state.boot_session_id == 0xFFFFFFFF
    assert state.sequence == 0xFFFFFFFE
    assert state.response_mask == 0x3F
    assert state.raw_positions == (-20, 100, 200, 300, 4095, 5000)


def test_status_requires_exact_shape_and_known_state():
    status = LeaderStatus.from_array([1, 2, 7, 9, 63, 63, 63, -1, 100, 0, 0, 2000, -42])
    assert status.state is LeaderStateCode.READY
    assert status.calibration_crc32 == 0xFFFFFFFF
    with pytest.raises(ValueError, match="13"):
        LeaderStatus.from_array([1] * 12)


def test_ros2_int_array_field_parser_ignores_yaml_document_separator():
    output = "[1, 2, 7, 9, 63, 63, 63, -1, 100, 0, 0, 2000, -42]\n---\n"

    assert parse_ros2_int_array_field(output) == [
        1,
        2,
        7,
        9,
        63,
        63,
        63,
        -1,
        100,
        0,
        0,
        2000,
        -42,
    ]


def test_normalization_matches_lerobot_ranges():
    raw = [694, 2012, 3080, 679, 2047, 2808]
    action = normalize_leader_raw(raw, CALIBRATION)
    assert action["shoulder_pan.pos"] == pytest.approx(-100.0)
    assert action["shoulder_lift.pos"] == pytest.approx(0.0, abs=0.1)
    assert action["elbow_flex.pos"] == pytest.approx(100.0)
    assert action["wrist_flex.pos"] == pytest.approx(-100.0)
    assert action["wrist_roll.pos"] == pytest.approx(-0.02442, abs=0.01)
    assert action["gripper.pos"] == pytest.approx(100.0)


def test_loader_rejects_wrong_ids(tmp_path: Path):
    path = tmp_path / "leader.json"
    path.write_text('{"shoulder_pan":{"id":6}}')
    with pytest.raises(ValueError, match="joints|ID"):
        load_leader_calibration(path)


def test_loader_rejects_non_mapping_joint_entry(tmp_path: Path):
    path = tmp_path / "leader.json"
    calibration = dict(CALIBRATION)
    calibration["elbow_flex"] = []
    path.write_text(json.dumps(calibration))
    with pytest.raises(ValueError, match="mapping|elbow_flex"):
        load_leader_calibration(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("homing_offset", 1084.5),
        ("range_min", -1),
        ("range_max", 65536),
    ],
)
def test_crc_rejects_non_integral_or_unrepresentable_calibration(field: str, value):
    calibration = dict(CALIBRATION)
    calibration["shoulder_pan"] = {**CALIBRATION["shoulder_pan"], field: value}
    with pytest.raises(ValueError, match="integer|representable|range"):
        leader_calibration_crc32(calibration)
