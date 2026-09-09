from dataclasses import replace

import pytest

from tools.soarm_wireless.leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
)
from tools.soarm_wireless.leader_source import LeaderUnavailable, WirelessLeaderTracker


@pytest.fixture
def calibration():
    return {
        "shoulder_pan": {"id": 1, "drive_mode": 0, "homing_offset": 1084, "range_min": 694, "range_max": 3349},
        "shoulder_lift": {"id": 2, "drive_mode": 0, "homing_offset": -1065, "range_min": 804, "range_max": 3220},
        "elbow_flex": {"id": 3, "drive_mode": 0, "homing_offset": 16, "range_min": 795, "range_max": 3080},
        "wrist_flex": {"id": 4, "drive_mode": 0, "homing_offset": 133, "range_min": 679, "range_max": 3084},
        "wrist_roll": {"id": 5, "drive_mode": 0, "homing_offset": 1925, "range_min": 0, "range_max": 4095},
        "gripper": {"id": 6, "drive_mode": 0, "homing_offset": -1891, "range_min": 1447, "range_max": 2808},
    }


@pytest.fixture
def ready_status(calibration):
    return LeaderStatus(
        version=1,
        state=LeaderStateCode.READY,
        boot_session_id=7,
        last_sequence=0,
        response_mask=0x3F,
        model_match_mask=0x3F,
        torque_off_mask=0x3F,
        calibration_crc32=leader_calibration_crc32(calibration),
        read_cycles=10,
        read_errors=0,
        torque_errors=0,
        uptime_ms=1000,
        rssi_dbm=-42,
    )


@pytest.fixture
def raw_state():
    return LeaderRawState(
        version=1,
        boot_session_id=7,
        sequence=1,
        uptime_ms=1010,
        response_mask=0x3F,
        raw_positions=(694, 2012, 3080, 679, 2047, 2808),
    )


def test_tracker_accepts_only_ready_matching_status(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration, stale_timeout_s=0.150)
    tracker.on_status(ready_status, received_at=1.0)
    assert tracker.on_raw_state(raw_state, received_at=1.01)
    assert tracker.get_action(now=1.10)["shoulder_pan.pos"] == pytest.approx(-100.0)


def test_tracker_rejects_crc_mismatch(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(replace(ready_status, calibration_crc32=0), 1.0)
    assert not tracker.on_raw_state(raw_state, 1.01)
    with pytest.raises(LeaderUnavailable, match="calibration"):
        tracker.get_action(1.02)


def test_tracker_rejects_duplicate_and_old_sequence(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(ready_status, 1.0)
    assert tracker.on_raw_state(raw_state, 1.01)
    assert not tracker.on_raw_state(replace(raw_state, sequence=raw_state.sequence), 1.02)
    assert not tracker.on_raw_state(replace(raw_state, sequence=raw_state.sequence - 1), 1.03)


def test_tracker_becomes_unavailable_after_150_ms(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration, stale_timeout_s=0.150)
    tracker.on_status(ready_status, 1.0)
    tracker.on_raw_state(raw_state, 1.01)
    with pytest.raises(LeaderUnavailable, match="stale"):
        tracker.get_action(1.161)


def test_new_boot_session_resets_sequence_gate(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(ready_status, 1.0)
    tracker.on_raw_state(raw_state, 1.01)
    new_status = replace(ready_status, boot_session_id=99, last_sequence=0)
    tracker.on_status(new_status, 2.0)
    assert tracker.on_raw_state(replace(raw_state, boot_session_id=99, sequence=1), 2.01)
