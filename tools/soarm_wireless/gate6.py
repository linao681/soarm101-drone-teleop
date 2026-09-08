from __future__ import annotations

import json
from pathlib import Path

from tools.soarm_wireless.control import JOINT_NAMES, raw_to_radians
from tools.soarm_wireless.protocol import FollowerState, RejectReason

GRIPPER_INDEX = JOINT_NAMES.index("gripper")
GRIPPER_DELTA_RAD = 0.10
POSITION_TOLERANCE_RAD = 0.03


class Gate6Error(RuntimeError):
    """A safety or acceptance condition failed during Gate 6."""


# Keep the plan's public name while using the Ruff-compliant ``Error`` suffix.
Gate6Failure = Gate6Error


def write_evidence(path: Path, evidence: dict[str, object]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def build_target(start: list[float], calibration: dict[str, dict[str, int]]) -> list[float]:
    if len(start) != len(JOINT_NAMES):
        raise Gate6Error("expected six starting joint positions")

    target = list(start)
    target[GRIPPER_INDEX] += GRIPPER_DELTA_RAD
    gripper_calibration = calibration["gripper"]
    low = raw_to_radians(gripper_calibration["range_min"])
    high = raw_to_radians(gripper_calibration["range_max"])
    if not low <= target[GRIPPER_INDEX] <= high:
        raise Gate6Error("gripper target is outside follower calibration")
    return target


def validate_preflight(status, read_errors: int, write_errors: int) -> None:
    if status.response_mask != 0x3F:
        raise Gate6Error(f"servo response mask is 0x{status.response_mask:02x}")
    if status.state not in (FollowerState.WAITING_HANDSHAKE, FollowerState.HOLDING_TIMEOUT):
        raise Gate6Error(f"follower state is {status.state.name}")
    if status.reject_reason is not RejectReason.NONE:
        raise Gate6Error(f"follower rejection is {status.reject_reason.name}")
    if status.read_errors != read_errors or status.write_errors != write_errors:
        raise Gate6Error("bus error counters changed during preflight")


def evaluate_completion(
    start: list[float],
    target: list[float],
    measured: list[float],
    status,
    expected_session_id: int,
    read_errors: int,
    write_errors: int,
) -> None:
    if status.session_id != expected_session_id:
        raise Gate6Error("follower status belongs to a different session")
    if status.response_mask != 0x3F or status.state is not FollowerState.ACTIVE:
        raise Gate6Error("follower is not active with all servos online")
    if status.reject_reason is not RejectReason.NONE:
        raise Gate6Error(f"follower rejection is {status.reject_reason.name}")
    if status.read_errors != read_errors or status.write_errors != write_errors:
        raise Gate6Error("bus error counters increased")
    if measured[GRIPPER_INDEX] - start[GRIPPER_INDEX] <= 0.0:
        raise Gate6Error("gripper direction was not positive")
    if abs(measured[GRIPPER_INDEX] - target[GRIPPER_INDEX]) > POSITION_TOLERANCE_RAD:
        raise Gate6Error("gripper did not reach the requested target")
    for index, value in enumerate(measured):
        if index != GRIPPER_INDEX and abs(value - start[index]) > POSITION_TOLERANCE_RAD:
            raise Gate6Error(f"unexpected motion on {JOINT_NAMES[index]}")
