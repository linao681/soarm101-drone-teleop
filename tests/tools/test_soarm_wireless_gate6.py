from dataclasses import replace

import pytest

from tools.soarm_wireless.gate6 import (
    GRIPPER_DELTA_RAD,
    Gate6Failure,
    build_target,
    evaluate_completion,
    validate_preflight,
)
from tools.soarm_wireless.protocol import FollowerState, FollowerStatus, RejectReason


@pytest.fixture
def status_waiting():
    return FollowerStatus(
        version=1,
        state=FollowerState.WAITING_HANDSHAKE,
        session_id=7,
        last_received_sequence=0,
        last_applied_sequence=0,
        command_age_ms=0,
        response_mask=0x3F,
        reject_reason=RejectReason.NONE,
        command_timeout_count=0,
        invalid_command_count=0,
        control_reject_count=0,
        read_errors=0,
        write_errors=0,
        rssi_dbm=-40,
    )


@pytest.fixture
def status_active():
    return FollowerStatus(
        version=1,
        state=FollowerState.ACTIVE,
        session_id=7,
        last_received_sequence=2,
        last_applied_sequence=2,
        command_age_ms=10,
        response_mask=0x3F,
        reject_reason=RejectReason.NONE,
        command_timeout_count=0,
        invalid_command_count=0,
        control_reject_count=0,
        read_errors=0,
        write_errors=0,
        rssi_dbm=-40,
    )


def calibration():
    return {"gripper": {"range_min": 0, "range_max": 4095}}


def test_build_target_changes_only_gripper():
    start = [0.0, 0.1, 0.2, 0.3, 0.4, -0.5]
    target = build_target(start, calibration())

    assert target[:-1] == start[:-1]
    assert target[-1] == pytest.approx(start[-1] + GRIPPER_DELTA_RAD)


def test_build_target_rejects_gripper_outside_calibration_range():
    with pytest.raises(Gate6Failure, match="outside follower calibration"):
        build_target([0.0] * 6, {"gripper": {"range_min": 0, "range_max": 2048}})


def test_preflight_requires_all_servos_and_no_rejection(status_waiting):
    validate_preflight(status_waiting, 0, 0)

    status_waiting = replace(status_waiting, response_mask=0x00)
    with pytest.raises(Gate6Failure, match="response mask"):
        validate_preflight(status_waiting, 0, 0)


def test_completion_accepts_positive_gripper_motion(status_active):
    start = [0.0] * 6
    target = build_target(start, calibration())

    evaluate_completion(start, target, target, status_active, 7, 0, 0)


def test_completion_rejects_wrong_direction_and_other_joint_motion(status_active):
    start = [0.0] * 6
    target = build_target(start, calibration())

    wrong_direction = [0.0] * 6
    wrong_direction[-1] = -0.05
    with pytest.raises(Gate6Failure, match="gripper direction"):
        evaluate_completion(start, target, wrong_direction, status_active, 7, 0, 0)

    moved_body_joint = list(target)
    moved_body_joint[0] = 0.04
    with pytest.raises(Gate6Failure, match="unexpected motion"):
        evaluate_completion(start, target, moved_body_joint, status_active, 7, 0, 0)


def test_completion_rejects_status_from_another_session(status_active):
    start = [0.0] * 6
    target = build_target(start, calibration())

    with pytest.raises(Gate6Failure, match="different session"):
        evaluate_completion(start, target, target, status_active, 8, 0, 0)
