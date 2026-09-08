from pathlib import Path
from types import SimpleNamespace

import pytest
from builtin_interfaces.msg import Time

from tools.wireless_teleoperate import (
    WirelessFollowerBridge,
    compute_recovery_target,
    update_feedback_recovery,
)


class _Publisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


class _Clock:
    def now(self):
        return SimpleNamespace(to_msg=Time)


def test_publish_command_records_sequence_for_metrics(monkeypatch):
    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 0x12345678
    bridge.next_sequence = 7
    bridge.last_command_sequence = 0
    bridge.command_send_times = {}
    bridge.publisher = _Publisher()
    bridge.get_clock = lambda: _Clock()
    monkeypatch.setattr("tools.wireless_teleoperate.time.monotonic", lambda: 12.5)

    sequence = bridge.publish_command([0.0] * 6)

    assert sequence == 7
    assert bridge.last_command_sequence == 7


def test_feedback_recovery_waits_for_reconnect_window():
    stale_since = update_feedback_recovery(
        now=10.0,
        latest_feedback=9.0,
        stale_since=None,
        feedback_timeout=0.5,
        recovery_timeout=5.0,
    )
    assert stale_since == 10.0
    assert update_feedback_recovery(
        now=10.5,
        latest_feedback=9.0,
        stale_since=stale_since,
        feedback_timeout=0.5,
        recovery_timeout=5.0,
    ) == 10.0


def test_feedback_recovery_fails_after_reconnect_window():
    with pytest.raises(RuntimeError, match="feedback recovery timed out"):
        update_feedback_recovery(
            now=15.1,
            latest_feedback=9.0,
            stale_since=10.0,
            feedback_timeout=0.5,
            recovery_timeout=5.0,
        )


def test_recovery_target_catches_up_to_leader_motion_during_outage():
    calibration = {
        name: {"id": index, "range_min": 0, "range_max": 4095}
        for index, name in enumerate(
            ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"),
            start=1,
        )
    }
    leader_origin = {f"{name}.pos": 0.0 for name in calibration}
    current_leader = {f"{name}.pos": 50.0 for name in calibration}
    follower_origin = [0.0] * 6

    target = compute_recovery_target(
        current_leader,
        leader_origin,
        follower_origin,
        calibration,
        mapping_mode="relative",
    )

    assert all(value > 0.0 for value in target)


def test_recovery_blend_duration_has_three_second_default():
    source = (Path(__file__).parents[2] / "tools" / "wireless_teleoperate.py").read_text()

    assert '"--recovery-blend-duration"' in source
    assert "default=3.0" in source


def test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta():
    source = (Path(__file__).parents[2] / "tools" / "validate_wireless_gate6.py").read_text()

    assert 'parser.add_argument("--yes", action="store_true")' in source
    assert "sys.path.insert" in source
    assert "GRIPPER_DELTA_RAD" in source
    assert "arm_at_current_pose(node, start)" in source
    assert "node.publish_command(target)" in source
    assert "write_evidence" in source
