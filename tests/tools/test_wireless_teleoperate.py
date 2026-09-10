from pathlib import Path
from types import SimpleNamespace

import pytest
from builtin_interfaces.msg import Time

import tools.wireless_teleoperate as teleoperate
from tools.soarm_wireless.leader_source import LeaderUnavailable
from tools.soarm_wireless.protocol import FollowerStatus
from tools.wireless_teleoperate import (
    WirelessFollowerBridge,
    compute_recovery_target,
    drain_ros_callbacks,
    forward_leader_command,
    parse_args,
    recover_leader_session,
    startup_blend,
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


def test_drain_ros_callbacks_services_all_ready_wireless_topics(monkeypatch):
    calls = []
    node = object()

    monkeypatch.setattr(
        teleoperate.rclpy,
        "spin_once",
        lambda received_node, timeout_sec: calls.append((received_node, timeout_sec)),
    )

    drain_ros_callbacks(node, max_callbacks=8)

    assert calls == [(node, 0.0)] * 8


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


def test_recovery_blend_duration_has_one_second_default():
    source = (Path(__file__).parents[2] / "tools" / "wireless_teleoperate.py").read_text()

    assert '"--recovery-blend-duration"' in source
    assert "default=1.0" in source


def test_wireless_cli_does_not_require_a_serial_port_and_keeps_30hz_default(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["wireless_teleoperate.py", "--leader-mode", "wireless"],
    )

    args = parse_args()

    assert args.leader_mode == "wireless"
    assert args.leader_port is None
    assert args.leader_stale_timeout == pytest.approx(0.15)
    assert args.leader_recovery_blend_duration == pytest.approx(1.0)
    assert args.rate == pytest.approx(30.0)


def test_wait_for_leader_spins_until_initial_action_is_ready(monkeypatch):
    events = []
    action = {"shoulder_pan.pos": 1.0}

    class Source:
        def __init__(self):
            self.attempts = 0

        def get_action(self, now):
            events.append(("get_action", now))
            self.attempts += 1
            if self.attempts == 1:
                raise LeaderUnavailable("leader sample unavailable: no_sample")
            return action

    class Node:
        pass

    def fake_spin_once(node, timeout_sec):
        events.append(("spin_once", timeout_sec))

    monkeypatch.setattr(teleoperate.rclpy, "spin_once", fake_spin_once)

    result = teleoperate.wait_for_leader(Node(), Source(), timeout=1.0)

    assert result == action
    assert [event[0] for event in events] == ["get_action", "spin_once", "get_action"]


def test_wait_for_leader_times_out_with_clear_error(monkeypatch):
    clock = {"now": 0.0}

    class Source:
        def get_action(self, now):
            raise LeaderUnavailable("leader sample unavailable: no_sample")

    class Node:
        pass

    def fake_spin_once(node, timeout_sec):
        clock["now"] += 0.2

    monkeypatch.setattr(teleoperate.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(teleoperate.rclpy, "spin_once", fake_spin_once)

    with pytest.raises(RuntimeError, match="Leader.*ready"):
        teleoperate.wait_for_leader(Node(), Source(), timeout=0.5)


def test_leader_outage_never_publishes_a_command():
    class Source:
        def get_action(self, now):
            raise LeaderUnavailable("leader sample is stale")

    node = SimpleNamespace(publish_calls=[])
    node.publish_command = lambda positions: node.publish_calls.append(positions)
    command = [0.1] * 6

    next_command, action, published = forward_leader_command(
        node=node,
        leader_source=Source(),
        now=10.0,
        command=command,
        leader_origin={f"{name}.pos": 0.0 for name in teleoperate.JOINT_NAMES},
        follower_origin=[0.0] * 6,
        follower_calibration={
            name: {"id": index, "range_min": 0, "range_max": 4095}
            for index, name in enumerate(teleoperate.JOINT_NAMES, start=1)
        },
        mapping_mode="relative",
        max_step=0.24,
    )

    assert next_command == command
    assert action is None
    assert not published
    assert node.publish_calls == []


def test_recovery_reads_pose_resets_session_handshakes_and_blends_current_target(
    monkeypatch,
):
    events = []
    current_pose = [0.3] * 6
    leader_origin = {f"{name}.pos": 0.0 for name in teleoperate.JOINT_NAMES}
    stale_action = {f"{name}.pos": 5.0 for name in teleoperate.JOINT_NAMES}
    fresh_action = {f"{name}.pos": 50.0 for name in teleoperate.JOINT_NAMES}
    calibration = {
        name: {"id": index, "range_min": 0, "range_max": 4095}
        for index, name in enumerate(teleoperate.JOINT_NAMES, start=1)
    }

    class Node:
        def reset_session(self):
            events.append(("reset_session",))

        def set_command_context(self, received_action, target):
            events.append(("set_command_context", received_action, target))

    class Source:
        boot_session_id = 9

        def get_action(self, now):
            events.append(("get_action", now))
            return fresh_action

    def fake_wait(node, timeout, after_monotonic=0.0):
        events.append(("wait_for_follower", timeout, after_monotonic))
        return current_pose

    def fake_arm(node, pose):
        events.append(("arm_at_current_pose", pose))

    def fake_blend(node, start, target, duration, rate, max_step, feedback_timeout, **kwargs):
        events.append(("startup_blend", start, target, duration, rate, max_step, feedback_timeout, kwargs))
        return target

    monkeypatch.setattr(teleoperate, "wait_for_follower", fake_wait)
    monkeypatch.setattr(teleoperate, "arm_at_current_pose", fake_arm)
    monkeypatch.setattr(teleoperate, "startup_blend", fake_blend)
    monkeypatch.setattr(teleoperate.time, "monotonic", lambda: 22.75)

    result = recover_leader_session(
        node=Node(),
        leader_source=Source(),
        now=12.5,
        leader_origin=leader_origin,
        follower_origin=[0.0] * 6,
        follower_calibration=calibration,
        mapping_mode="relative",
        recovery_blend_duration=1.0,
        rate=30.0,
        max_step=0.24,
        feedback_timeout=0.5,
        action=stale_action,
    )

    expected = compute_recovery_target(
        fresh_action, leader_origin, [0.0] * 6, calibration, "relative"
    )
    assert result == pytest.approx(expected)
    assert events[0] == ("wait_for_follower", 5.0, 0.0)
    assert events[1] == ("get_action", 22.75)
    assert events[2] == ("reset_session",)
    assert events[3] == ("arm_at_current_pose", current_pose)
    blend = next(event for event in events if event[0] == "startup_blend")
    assert blend[1] == current_pose
    assert blend[2] == pytest.approx(expected)
    assert blend[3:7] == (1.0, 30.0, 0.24, 0.5)
    assert blend[7]["leader_source"].boot_session_id == 9


def test_recovery_aborts_before_reset_or_arm_when_fresh_leader_is_unavailable(
    monkeypatch,
):
    events = []
    leader_origin = {f"{name}.pos": 0.0 for name in teleoperate.JOINT_NAMES}
    stale_action = {f"{name}.pos": 5.0 for name in teleoperate.JOINT_NAMES}
    calibration = {
        name: {"id": index, "range_min": 0, "range_max": 4095}
        for index, name in enumerate(teleoperate.JOINT_NAMES, start=1)
    }

    class Node:
        def reset_session(self):
            events.append(("reset_session",))

        def set_command_context(self, received_action, target):
            events.append(("set_command_context", received_action, target))

    class Source:
        def get_action(self, now):
            events.append(("get_action", now))
            raise LeaderUnavailable("leader sample is stale")

    current_pose = [0.3] * 6

    def fake_wait(node, timeout, after_monotonic=0.0):
        events.append(("wait_for_follower", timeout, after_monotonic))
        return current_pose

    def fake_arm(node, pose):
        events.append(("arm_at_current_pose", pose))

    def fake_blend(node, start, target, duration, rate, max_step, feedback_timeout, **kwargs):
        events.append(("startup_blend",))
        return target

    monkeypatch.setattr(teleoperate, "wait_for_follower", fake_wait)
    monkeypatch.setattr(teleoperate, "arm_at_current_pose", fake_arm)
    monkeypatch.setattr(teleoperate, "startup_blend", fake_blend)
    monkeypatch.setattr(teleoperate.time, "monotonic", lambda: 31.5)

    with pytest.raises(LeaderUnavailable, match="stale"):
        recover_leader_session(
            node=Node(),
            leader_source=Source(),
            now=12.5,
            leader_origin=leader_origin,
            follower_origin=[0.0] * 6,
            follower_calibration=calibration,
            mapping_mode="relative",
            recovery_blend_duration=1.0,
            rate=30.0,
            max_step=0.24,
            feedback_timeout=0.5,
            action=stale_action,
        )

    assert events == [("wait_for_follower", 5.0, 0.0), ("get_action", 31.5)]


def test_recovery_blend_stops_publishing_after_a_later_leader_outage(monkeypatch):
    action = {"shoulder_pan.pos": 0.0}

    class Node:
        latest_monotonic = teleoperate.time.monotonic()
        latest_status = None

        def __init__(self):
            self.publish_calls = []

        def log_latest_status(self):
            pass

        def publish_command(self, positions):
            self.publish_calls.append(list(positions))

    class Source:
        def __init__(self):
            self.calls = 0

        def get_action(self, now):
            self.calls += 1
            if self.calls == 2:
                raise LeaderUnavailable("leader sample is stale")
            return action

    node = Node()
    monkeypatch.setattr(teleoperate.rclpy, "spin_once", lambda node, timeout_sec: None)

    with pytest.raises(LeaderUnavailable, match="stale"):
        startup_blend(
            node=node,
            start=[0.0] * 6,
            target=[0.1] * 6,
            duration=0.02,
            rate=100.0,
            max_step=0.24,
            feedback_timeout=1.0,
            leader_source=Source(),
        )

    assert len(node.publish_calls) == 1


def test_recovery_handshake_does_not_bind_pending_sample_before_first_live_command(
    monkeypatch,
):
    action = {f"{name}.pos": 0.0 for name in teleoperate.JOINT_NAMES}
    calibration = {
        name: {"id": index, "range_min": 0, "range_max": 4095}
        for index, name in enumerate(teleoperate.JOINT_NAMES, start=1)
    }

    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 7
    bridge.next_sequence = 11
    bridge.last_command_sequence = 0
    bridge.command_send_times = {}
    bridge.command_leader_samples = {}
    bridge.command_control_chain_ack_latencies = {}
    bridge.previous_leader_sample_key = None
    bridge.previous_leader_sample_received_at = None
    bridge.leader_recovery_count = 0
    bridge.pending_leader_sample = {
        "boot_session_id": 1,
        "sequence": 99,
        "received_at": 10.0,
    }
    bridge.latest_leader_sample = bridge.pending_leader_sample.copy()
    bridge.publisher = _Publisher()
    bridge.get_clock = lambda: _Clock()

    class Source:
        sample_metadata = {
            "boot_session_id": 2,
            "sequence": 1,
            "received_at": 20.0,
        }

        def get_action(self, now):
            return action

    source = Source()

    monkeypatch.setattr(teleoperate, "wait_for_follower", lambda *args, **kwargs: [0.0] * 6)
    monkeypatch.setattr(teleoperate, "arm_at_current_pose", lambda node, pose: node.publish_command(pose))
    monkeypatch.setattr(
        teleoperate,
        "startup_blend",
        lambda node, start, target, *args, **kwargs: (node.publish_command(target), target)[1],
    )
    monkeypatch.setattr(teleoperate.time, "monotonic", lambda: 20.1)

    recover_leader_session(
        node=bridge,
        leader_source=source,
        now=20.0,
        leader_origin={f"{name}.pos": 0.0 for name in teleoperate.JOINT_NAMES},
        follower_origin=[0.0] * 6,
        follower_calibration=calibration,
        mapping_mode="relative",
        recovery_blend_duration=1.0,
        rate=30.0,
        max_step=0.24,
        feedback_timeout=0.5,
    )

    assert bridge.command_leader_samples[(bridge.session_id, 2)]["sequence"] == 1
    assert (bridge.session_id, 1) not in bridge.command_leader_samples


def test_foreign_follower_status_does_not_write_leader_sample_or_chain_fields(monkeypatch):
    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 7
    bridge.command_leader_samples = {
        (7, 4): {"boot_session_id": 9, "sequence": 100, "received_at": 10.0}
    }
    bridge.command_control_chain_ack_latencies = {(7, 4): 82.0}
    bridge.last_ack_latency_ms = 41.0
    bridge.latest_leader_sample = bridge.command_leader_samples[(7, 4)]
    bridge.latest_leader = [0.0] * 6
    bridge.latest_target = [0.0] * 6
    bridge.latest_positions = [0.1] * 6
    bridge.last_command_sequence = 4
    bridge.leader_recovery_count = 0
    bridge.metrics_writer = SimpleNamespace(rows=[], write=lambda row: bridge.metrics_writer.rows.append(row))
    bridge.last_logged_status_monotonic = 10.0
    monkeypatch.setattr("tools.wireless_teleoperate.time.monotonic", lambda: 11.0)

    bridge.latest_status = FollowerStatus.from_array(
        [1, 1, 7, 4, 4, 9999, 63, 0, 0, 0, 0, 0, 0, -48]
    )
    bridge.latest_status_monotonic = 10.0
    bridge._status_callback(
        SimpleNamespace(data=[1, 1, 8, 4, 4, 9999, 63, 0, 0, 0, 0, 0, 0, -48])
    )
    bridge.log_latest_status()

    assert bridge.latest_status.session_id == 7
    assert bridge.latest_status_monotonic == 10.0
    assert bridge.metrics_writer.rows == []


def test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta():
    source = (Path(__file__).parents[2] / "tools" / "validate_wireless_gate6.py").read_text()

    assert 'parser.add_argument("--yes", action="store_true")' in source
    assert "sys.path.insert" in source
    assert "GRIPPER_DELTA_RAD" in source
    assert "arm_at_current_pose(node, start)" in source
    assert "node.publish_command(target)" in source
    assert "write_evidence" in source
