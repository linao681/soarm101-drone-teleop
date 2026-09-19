import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.soarm_wireless.leader_source as leader_source_module
from tools.soarm_wireless.leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
)
from tools.soarm_wireless.leader_source import (
    LeaderUnavailable,
    WiredLeaderSource,
    WirelessLeaderSource,
    WirelessLeaderTracker,
)


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


def test_wired_source_preserves_eeprom_calibration_matching(monkeypatch, tmp_path: Path):
    calls = []

    class FakeLeader:
        is_connected = False
        is_calibrated = True
        calibration_fpath = tmp_path / "leader.json"

        def __init__(self, config):
            calls.append(("construct", config))

        def connect(self, *, calibrate):
            calls.append(("connect", calibrate))
            self.is_connected = True

        def get_action(self):
            calls.append(("get_action",))
            return {"shoulder_pan.pos": 12.0}

        def disconnect(self):
            calls.append(("disconnect",))
            self.is_connected = False

    monkeypatch.setattr(leader_source_module, "SO101Leader", FakeLeader)
    source = WiredLeaderSource(
        port="/dev/leader",
        leader_id="my_leader",
        calibration_dir=tmp_path,
    )

    source.connect()

    assert calls[0][0] == "construct"
    assert calls[0][1].port == "/dev/leader"
    assert calls[0][1].id == "my_leader"
    assert calls[1] == ("connect", False)
    assert source.is_connected
    assert source.get_action(now=12.0) == {"shoulder_pan.pos": 12.0}
    source.disconnect()
    assert calls[-1] == ("disconnect",)


def test_wireless_source_subscribes_with_best_effort_depth_one_and_parses_topics(
    monkeypatch, calibration, ready_status, raw_state, tmp_path: Path
):
    calibration_path = tmp_path / "leader.json"
    calibration_path.write_text(json.dumps(calibration))

    class FakeNode:
        def __init__(self):
            self.subscriptions = []

        def create_subscription(self, *args):
            self.subscriptions.append(args)
            return args

    node = FakeNode()
    times = iter((1.0, 1.01))
    monkeypatch.setattr(leader_source_module.time, "monotonic", lambda: next(times))

    source = WirelessLeaderSource(node, calibration_path, stale_timeout_s=0.15)

    assert len(node.subscriptions) == 2
    raw_type, raw_topic, raw_callback, raw_qos = node.subscriptions[0]
    status_type, status_topic, status_callback, status_qos = node.subscriptions[1]
    assert raw_type.__name__ == "Int32MultiArray"
    assert raw_topic == "/leader/raw_state"
    assert status_type.__name__ == "Int32MultiArray"
    assert status_topic == "/leader/status"
    for qos in (raw_qos, status_qos):
        assert qos.depth == 1
        assert str(qos.history).endswith("KEEP_LAST")
        assert str(qos.reliability).endswith("BEST_EFFORT")
    status_callback(SimpleNamespace(data=[
        ready_status.version,
        int(ready_status.state),
        ready_status.boot_session_id,
        ready_status.last_sequence,
        ready_status.response_mask,
        ready_status.model_match_mask,
        ready_status.torque_off_mask,
        ready_status.calibration_crc32,
        ready_status.read_cycles,
        ready_status.read_errors,
        ready_status.torque_errors,
        ready_status.uptime_ms,
        ready_status.rssi_dbm,
    ]))
    raw_callback(SimpleNamespace(data=[
        raw_state.version,
        raw_state.boot_session_id,
        raw_state.sequence,
        raw_state.uptime_ms,
        raw_state.response_mask,
        *raw_state.raw_positions,
    ]))

    source.connect()
    assert source.is_connected
    assert source.get_action(now=1.10)["shoulder_pan.pos"] == pytest.approx(-100.0)


def test_wireless_source_never_returns_last_action_after_stale_timeout(
    monkeypatch, calibration, ready_status, raw_state, tmp_path: Path
):
    calibration_path = tmp_path / "leader.json"
    calibration_path.write_text(json.dumps(calibration))

    class FakeNode:
        def create_subscription(self, *args):
            setattr(self, args[1].replace("/", "_"), args[2])
            return args

    node = FakeNode()
    times = iter((1.0, 1.01))
    monkeypatch.setattr(leader_source_module.time, "monotonic", lambda: next(times))
    source = WirelessLeaderSource(node, calibration_path, stale_timeout_s=0.15)
    source.connect()
    node._leader_status(SimpleNamespace(data=[
        ready_status.version, int(ready_status.state), ready_status.boot_session_id,
        ready_status.last_sequence, ready_status.response_mask, ready_status.model_match_mask,
        ready_status.torque_off_mask, ready_status.calibration_crc32, ready_status.read_cycles,
        ready_status.read_errors, ready_status.torque_errors, ready_status.uptime_ms,
        ready_status.rssi_dbm,
    ]))
    node._leader_raw_state(SimpleNamespace(data=[
        raw_state.version, raw_state.boot_session_id, raw_state.sequence, raw_state.uptime_ms,
        raw_state.response_mask, *raw_state.raw_positions,
    ]))

    assert source.get_action(now=1.01)["shoulder_pan.pos"] == pytest.approx(-100.0)
    with pytest.raises(LeaderUnavailable, match="stale"):
        source.get_action(now=1.161)
