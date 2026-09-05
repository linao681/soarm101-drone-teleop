from __future__ import annotations

import json
import math
from pathlib import Path

JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)
BODY_JOINTS = frozenset(JOINT_NAMES[:-1])
ENCODER_RESOLUTION = 4096.0
TWO_PI = 2.0 * math.pi


def raw_to_radians(raw: float) -> float:
    return (raw - ENCODER_RESOLUTION / 2.0) * TWO_PI / ENCODER_RESOLUTION


def load_follower_calibration(path: Path) -> dict[str, dict[str, int]]:
    with path.open() as calibration_file:
        calibration = json.load(calibration_file)
    if tuple(calibration) != JOINT_NAMES:
        raise ValueError(
            f"Unexpected joints in {path}: {list(calibration)}; expected {list(JOINT_NAMES)}"
        )
    for expected_id, name in enumerate(JOINT_NAMES, start=1):
        values = calibration[name]
        if values["id"] != expected_id:
            raise ValueError(f"{name} has ID {values['id']}, expected {expected_id}")
        if values["range_min"] >= values["range_max"]:
            raise ValueError(f"Invalid range for {name}: {values}")
        if values.get("drive_mode", 0) != 0:
            raise ValueError(f"Unsupported nonzero drive_mode for {name}")
    return calibration


def absolute_target(action, calibration):
    positions = []
    for name in JOINT_NAMES:
        key = f"{name}.pos"
        if key not in action:
            raise ValueError(f"Invalid or missing leader value for {key}")
        value = float(action[key])
        if not math.isfinite(value):
            raise ValueError(f"Invalid leader value for {key}")
        low, high = (-100.0, 100.0) if name in BODY_JOINTS else (0.0, 100.0)
        fraction = (min(high, max(low, value)) - low) / (high - low)
        raw = calibration[name]["range_min"] + fraction * (
            calibration[name]["range_max"] - calibration[name]["range_min"]
        )
        positions.append(raw_to_radians(raw))
    return positions


def relative_target(action, leader_origin, follower_origin, calibration):
    positions = []
    for index, name in enumerate(JOINT_NAMES):
        key = f"{name}.pos"
        if key not in action or key not in leader_origin:
            raise ValueError(f"Invalid or missing leader value for {key}")
        value = float(action[key])
        origin = float(leader_origin[key])
        if not math.isfinite(value) or not math.isfinite(origin):
            raise ValueError(f"Invalid leader value for {key}")
        normalized_span = 200.0 if name in BODY_JOINTS else 100.0
        raw_span = calibration[name]["range_max"] - calibration[name]["range_min"]
        follower_origin_raw = (
            follower_origin[index] * ENCODER_RESOLUTION / TWO_PI
            + ENCODER_RESOLUTION / 2.0
        )
        raw = follower_origin_raw + (value - origin) * raw_span / normalized_span
        raw = min(calibration[name]["range_max"], max(calibration[name]["range_min"], raw))
        positions.append(raw_to_radians(raw))
    return positions
