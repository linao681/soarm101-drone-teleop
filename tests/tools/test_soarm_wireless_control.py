import json
import math
from pathlib import Path

import pytest

from tools.soarm_wireless.control import (
    JOINT_NAMES,
    absolute_target,
    load_follower_calibration,
    relative_target,
)


@pytest.fixture
def calibration():
    path = Path(__file__).parents[2] / "cali" / "follower_recal.json"
    return json.loads(path.read_text())


def raw_to_radians(raw: float) -> float:
    return (raw - 2048.0) * (2.0 * math.pi) / 4096.0


def test_relative_target_starts_at_follower_pose(calibration):
    leader = {f"{name}.pos": 0.0 for name in JOINT_NAMES}
    follower = [0.1, -0.2, 0.3, -0.4, 0.5, 0.0]
    assert relative_target(leader, leader, follower, calibration) == pytest.approx(follower)


def test_absolute_target_clamps_body_and_gripper(calibration):
    action = {f"{name}.pos": 500.0 for name in JOINT_NAMES}
    result = absolute_target(action, calibration)
    expected_raw = [calibration[name]["range_max"] for name in JOINT_NAMES]
    assert result == pytest.approx([raw_to_radians(raw) for raw in expected_raw])


def test_calibration_rejects_wrong_joint_order(tmp_path, calibration):
    reversed_data = dict(reversed(list(calibration.items())))
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(reversed_data))
    with pytest.raises(ValueError, match="Unexpected joints"):
        load_follower_calibration(path)
