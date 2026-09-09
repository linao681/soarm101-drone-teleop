#!/usr/bin/env python3
"""Teleoperate a micro-ROS SO-101 follower from a USB-connected SO-101 leader."""

from __future__ import annotations

import argparse
import math
import secrets
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import Int32MultiArray

from tools.soarm_wireless.control import (
    JOINT_NAMES,
    absolute_target,
    load_follower_calibration,
    relative_target,
)
from tools.soarm_wireless.leader_source import (
    LeaderUnavailable,
    WiredLeaderSource,
    WirelessLeaderSource,
)
from tools.soarm_wireless.metrics import MetricsWriter
from tools.soarm_wireless.protocol import (
    FollowerState,
    FollowerStatus,
    encode_command_id,
    is_newer_sequence,
    status_matches_session,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge a LeRobot SO-101 leader to a wireless micro-ROS follower."
    )
    parser.add_argument(
        "--leader-mode",
        choices=("wired", "wireless"),
        default="wired",
        help="Use the USB leader or the wireless leader input",
    )
    parser.add_argument(
        "--leader-port",
        default=None,
        help="Leader USB serial port, e.g. /dev/ttyACM0 (wired mode only)",
    )
    parser.add_argument("--leader-id", default="leader_recal", help="Leader calibration file stem")
    parser.add_argument(
        "--calibration-dir",
        type=Path,
        default=Path("/home/linao/so101_lerobot/cali"),
        help="Directory containing the leader calibration JSON",
    )
    parser.add_argument(
        "--follower-calibration",
        type=Path,
        default=Path("/home/linao/so101_lerobot/cali/follower_recal.json"),
    )
    parser.add_argument("--rate", type=float, default=30.0, help="Command rate in Hz")
    parser.add_argument(
        "--max-step-rad",
        type=float,
        default=0.24,
        help="Maximum change per joint and command; firmware limit is 0.25 rad",
    )
    parser.add_argument(
        "--feedback-timeout",
        type=float,
        default=0.5,
        help="Stop publishing if follower feedback is older than this many seconds",
    )
    parser.add_argument(
        "--recovery-timeout",
        type=float,
        default=5.0,
        help="Seconds to wait for feedback to return after a WiFi interruption",
    )
    parser.add_argument(
        "--startup-duration",
        type=float,
        default=8.0,
        help="Seconds used to blend from the follower pose to the initial leader pose",
    )
    parser.add_argument(
        "--leader-recovery-blend-duration",
        "--recovery-blend-duration",
        dest="leader_recovery_blend_duration",
        type=float,
        default=1.0,
        help="Seconds used to smoothly catch up after follower session recovery",
    )
    parser.add_argument(
        "--leader-stale-timeout",
        type=float,
        default=0.15,
        help="Seconds after which the latest wireless leader sample is unavailable",
    )
    parser.add_argument(
        "--mapping-mode",
        choices=("relative", "absolute"),
        default="relative",
        help=(
            "relative keeps the follower still at startup and follows leader deltas; "
            "absolute maps the leader's calibrated pose directly"
        ),
    )
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        default=None,
        help="Write accepted follower status samples to this CSV path",
    )
    args = parser.parse_args()
    if args.leader_mode == "wired" and not args.leader_port:
        parser.error("--leader-port is required when --leader-mode is wired")
    return args


def limit_step(previous: list[float], desired: list[float], maximum: float) -> list[float]:
    return [
        old + min(max(target - old, -maximum), maximum)
        for old, target in zip(previous, desired, strict=True)
    ]


def update_feedback_recovery(
    now: float,
    latest_feedback: float,
    stale_since: float | None,
    feedback_timeout: float,
    recovery_timeout: float,
) -> float | None:
    """Track a temporary feedback outage without publishing stale targets."""
    if now - latest_feedback <= feedback_timeout:
        return None
    if stale_since is None:
        return now
    if now - stale_since > recovery_timeout:
        raise RuntimeError("Follower feedback recovery timed out; command publishing stopped")
    return stale_since


def compute_recovery_target(
    action: dict[str, float],
    leader_origin: dict[str, float],
    follower_origin: list[float],
    follower_calibration: dict[str, dict[str, int]],
    mapping_mode: str,
) -> list[float]:
    if mapping_mode == "relative":
        return relative_target(action, leader_origin, follower_origin, follower_calibration)
    return absolute_target(action, follower_calibration)


def update_leader_sample_context(node: WirelessFollowerBridge, leader_source, now: float) -> None:
    setter = getattr(node, "set_leader_sample", None)
    if callable(setter):
        setter(getattr(leader_source, "sample_metadata", None), now=now)


def build_leader_source(args: argparse.Namespace, node) -> WiredLeaderSource | WirelessLeaderSource:
    if args.leader_mode == "wireless":
        calibration_path = args.calibration_dir / f"{args.leader_id}.json"
        return WirelessLeaderSource(node, calibration_path, args.leader_stale_timeout)
    if not args.leader_port:
        raise ValueError("--leader-port is required when --leader-mode is wired")
    return WiredLeaderSource(
        port=args.leader_port,
        leader_id=args.leader_id,
        calibration_dir=args.calibration_dir,
    )


def forward_leader_command(
    node: WirelessFollowerBridge,
    leader_source,
    now: float,
    command: list[float],
    leader_origin: dict[str, float],
    follower_origin: list[float],
    follower_calibration: dict[str, dict[str, int]],
    mapping_mode: str,
    max_step: float,
) -> tuple[list[float], dict[str, float] | None, bool]:
    """Forward one leader action, never publishing when the leader is unavailable."""
    try:
        action = leader_source.get_action(now)
    except LeaderUnavailable:
        return command, None, False
    desired = compute_recovery_target(
        action,
        leader_origin,
        follower_origin,
        follower_calibration,
        mapping_mode,
    )
    command = limit_step(command, desired, max_step)
    node.set_command_context(action, command)
    update_leader_sample_context(node, leader_source, now)
    node.publish_command(command)
    return command, action, True


def recover_leader_session(
    node: WirelessFollowerBridge,
    leader_source,
    now: float,
    leader_origin: dict[str, float],
    follower_origin: list[float],
    follower_calibration: dict[str, dict[str, int]],
    mapping_mode: str,
    recovery_blend_duration: float,
    rate: float,
    max_step: float,
    feedback_timeout: float,
    *,
    action: dict[str, float] | None = None,
    after_monotonic: float = 0.0,
) -> list[float]:
    """Re-arm the follower at its measured pose and catch up to the live leader."""
    follower_start = wait_for_follower(node, timeout=5.0, after_monotonic=after_monotonic)
    action = leader_source.get_action(time.monotonic())
    node.reset_session()
    arm_at_current_pose(node, follower_start)
    recovery_target = compute_recovery_target(
        action,
        leader_origin,
        follower_origin,
        follower_calibration,
        mapping_mode,
    )
    node.set_command_context(action, recovery_target)
    update_leader_sample_context(node, leader_source, time.monotonic())
    return startup_blend(
        node,
        follower_start,
        recovery_target,
        recovery_blend_duration,
        rate,
        max_step,
        feedback_timeout,
        leader_source=leader_source,
    )


class WirelessFollowerBridge(Node):
    def __init__(self) -> None:
        super().__init__("so101_wireless_teleoperate")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.latest_positions: list[float] | None = None
        self.latest_monotonic = 0.0
        self.latest_status: FollowerStatus | None = None
        self.latest_status_monotonic = 0.0
        self.session_id = secrets.randbits(32)
        self.next_sequence = 1
        self.command_send_times: dict[int, float] = {}
        self.command_leader_samples: dict[tuple[int, int], dict[str, int | float]] = {}
        self.command_control_chain_ack_latencies: dict[tuple[int, int], float] = {}
        self.last_ack_latency_ms: float | None = None
        self.last_control_chain_ack_latency_ms: float | None = None
        self.metrics_writer: MetricsWriter | None = None
        self.last_logged_status_monotonic = 0.0
        self.latest_leader: list[float] | None = None
        self.latest_target: list[float] | None = None
        self.latest_leader_sample: dict[str, int | float] | None = None
        self.pending_leader_sample: dict[str, int | float] | None = None
        self.previous_leader_sample_key: tuple[int, int] | None = None
        self.previous_leader_sample_received_at: float | None = None
        self.leader_recovery_count = 0
        self.last_command_sequence = 0
        self.create_subscription(JointState, "/joint_states", self._state_callback, qos)
        self.create_subscription(Int32MultiArray, "/follower_status", self._status_callback, qos)
        self.publisher = self.create_publisher(JointState, "/joint_command", qos)

    def _state_callback(self, message: JointState) -> None:
        if tuple(message.name) != JOINT_NAMES or len(message.position) != len(JOINT_NAMES):
            return
        values = list(message.position)
        if not all(math.isfinite(value) for value in values):
            return
        self.latest_positions = values
        self.latest_monotonic = time.monotonic()

    def _status_callback(self, message: Int32MultiArray) -> None:
        try:
            status = FollowerStatus.from_array(list(message.data))
        except ValueError:
            return
        if not status_matches_session(status, self.session_id):
            return
        self.latest_status = status
        received_at = time.monotonic()
        self.latest_status_monotonic = received_at
        send_time = self.command_send_times.pop(status.last_applied_sequence, None)
        if send_time is not None:
            self.last_ack_latency_ms = (received_at - send_time) * 1000.0
        command_key = (status.session_id, status.last_applied_sequence)
        leader_sample = self.command_leader_samples.get(command_key)
        if (
            leader_sample is not None
            and command_key not in self.command_control_chain_ack_latencies
        ):
            latency_ms = (
                received_at - float(leader_sample["received_at"])
            ) * 1000.0
            self.last_control_chain_ack_latency_ms = latency_ms
            self.command_control_chain_ack_latencies[command_key] = latency_ms

    def reset_session(self) -> None:
        self.session_id = secrets.randbits(32)
        self.next_sequence = 1
        self.command_send_times.clear()
        self.command_leader_samples.clear()
        self.command_control_chain_ack_latencies.clear()
        self.pending_leader_sample = None
        self.last_ack_latency_ms = None
        self.last_control_chain_ack_latency_ms = None

    def set_metrics_writer(self, writer: MetricsWriter | None) -> None:
        self.metrics_writer = writer

    def set_command_context(self, leader_action: dict[str, float], target: list[float]) -> None:
        self.latest_leader = [float(leader_action[f"{name}.pos"]) for name in JOINT_NAMES]
        self.latest_target = list(target)

    def set_leader_sample(
        self, metadata: dict[str, int | float] | None, *, now: float
    ) -> None:
        if metadata is None:
            self.pending_leader_sample = None
            return
        sample = dict(metadata)
        session_id = int(sample["boot_session_id"])
        sequence = int(sample["sequence"])
        received_at = float(sample["received_at"])
        sample["sample_age_ms"] = max(0.0, (now - received_at) * 1000.0)
        if self.previous_leader_sample_key == (session_id, sequence):
            sample["sample_gap_ms"] = (
                self.latest_leader_sample.get("sample_gap_ms", "")
                if self.latest_leader_sample
                else ""
            )
        else:
            if (
                self.previous_leader_sample_key is not None
                and self.previous_leader_sample_key[0] != session_id
            ):
                self.leader_recovery_count += 1
            sample["sample_gap_ms"] = (
                (received_at - self.previous_leader_sample_received_at) * 1000.0
                if (
                    self.previous_leader_sample_received_at is not None
                    and self.previous_leader_sample_key is not None
                    and self.previous_leader_sample_key[0] == session_id
                )
                else ""
            )
            self.previous_leader_sample_key = (session_id, sequence)
            self.previous_leader_sample_received_at = received_at
        self.latest_leader_sample = sample
        self.pending_leader_sample = sample

    def log_latest_status(self) -> None:
        status = self.latest_status
        timestamp = self.latest_status_monotonic
        if (
            self.metrics_writer is None
            or status is None
            or timestamp <= self.last_logged_status_monotonic
        ):
            return
        if not status_matches_session(status, self.session_id):
            return
        measured = self.latest_positions or [""] * len(JOINT_NAMES)
        leader = self.latest_leader or [""] * len(JOINT_NAMES)
        target = self.latest_target or [""] * len(JOINT_NAMES)
        owns_status = status_matches_session(status, self.session_id)
        command_key = (status.session_id, status.last_applied_sequence)
        leader_sample = (
            self.command_leader_samples.get(command_key) if owns_status else None
        ) or {}
        control_chain_ack_latency = (
            self.command_control_chain_ack_latencies.get(command_key, "")
            if owns_status
            else ""
        )
        row: dict[str, object] = {
            "host_monotonic_s": timestamp,
            "session_id": status.session_id,
            "command_sequence": self.last_command_sequence,
            "applied_sequence": status.last_applied_sequence,
            "state": int(status.state),
            "reject_reason": int(status.reject_reason),
            "command_age_ms": status.command_age_ms,
            "ack_latency_ms": (
                self.last_ack_latency_ms
                if status_matches_session(status, self.session_id)
                else ""
            ),
            "rssi_dbm": status.rssi_dbm,
            "response_mask": status.response_mask,
            "leader_boot_session_id": leader_sample.get("boot_session_id", ""),
            "leader_sample_sequence": leader_sample.get("sequence", ""),
            "leader_sample_gap_ms": leader_sample.get("sample_gap_ms", ""),
            "leader_sample_age_ms": leader_sample.get("sample_age_ms", ""),
            "leader_response_mask": leader_sample.get("response_mask", ""),
            "leader_model_mask": leader_sample.get("model_mask", ""),
            "leader_torque_off_mask": leader_sample.get("torque_off_mask", ""),
            "leader_calibration_crc32": leader_sample.get("calibration_crc32", ""),
            "leader_read_errors": leader_sample.get("read_errors", ""),
            "leader_torque_errors": leader_sample.get("torque_errors", ""),
            "leader_rssi_dbm": leader_sample.get("rssi_dbm", ""),
            "leader_recovery_count": self.leader_recovery_count if leader_sample else "",
            "control_chain_ack_latency_ms": control_chain_ack_latency,
        }
        row.update({f"leader_{index}": value for index, value in enumerate(leader)})
        row.update({f"target_{index}": value for index, value in enumerate(target)})
        row.update({f"measured_{index}": value for index, value in enumerate(measured)})
        self.metrics_writer.write(row)
        self.last_logged_status_monotonic = timestamp

    def publish_command(self, positions: list[float]) -> int:
        sequence = self.next_sequence
        self.next_sequence = (sequence + 1) & 0xFFFFFFFF
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = encode_command_id(self.session_id, sequence)
        message.name = JOINT_NAMES
        message.position = positions
        self.publisher.publish(message)
        self.last_command_sequence = sequence
        sent_at = time.monotonic()
        self.command_send_times[sequence] = sent_at
        pending_leader_sample = getattr(self, "pending_leader_sample", None)
        if pending_leader_sample is not None:
            command_leader_samples = getattr(self, "command_leader_samples", None)
            if command_leader_samples is None:
                command_leader_samples = self.command_leader_samples = {}
            command_leader_samples[(self.session_id, sequence)] = dict(pending_leader_sample)
        while len(self.command_send_times) > 256:
            old_sequence = next(iter(self.command_send_times))
            self.command_send_times.pop(old_sequence)
            command_key = (self.session_id, old_sequence)
            getattr(self, "command_leader_samples", {}).pop(command_key, None)
            getattr(self, "command_control_chain_ack_latencies", {}).pop(command_key, None)
        return sequence

    def owns_active_status(self) -> bool:
        status = self.latest_status
        return (
            status is not None
            and status_matches_session(status, self.session_id)
            and status.state is FollowerState.ACTIVE
            and status.response_mask == 0x3F
        )


def wait_for_follower(
    node: WirelessFollowerBridge, timeout: float = 12.0, after_monotonic: float = 0.0
) -> list[float]:
    deadline = time.monotonic() + timeout
    while (
        (node.latest_positions is None or node.latest_monotonic <= after_monotonic)
        and time.monotonic() < deadline
    ):
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.latest_positions is None or node.latest_monotonic <= after_monotonic:
        raise RuntimeError("No /joint_states received from the wireless follower")
    return list(node.latest_positions)


def wait_for_leader(node: WirelessFollowerBridge, leader_source, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    last_error: LeaderUnavailable | None = None
    while True:
        try:
            return leader_source.get_action(time.monotonic())
        except LeaderUnavailable as error:
            last_error = error
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            raise RuntimeError(f"Leader did not become ready within {timeout:.1f}s") from last_error
        rclpy.spin_once(node, timeout_sec=min(0.1, remaining))


def arm_at_current_pose(
    node: WirelessFollowerBridge, current: list[float], timeout: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout
    first_sequence: int | None = None
    while time.monotonic() < deadline:
        sequence = node.publish_command(current)
        if first_sequence is None:
            first_sequence = sequence
        rclpy.spin_once(node, timeout_sec=0.02)
        node.log_latest_status()
        status = node.latest_status
        if (
            first_sequence is not None
            and status is not None
            and status_matches_session(status, node.session_id)
            and status.state is FollowerState.ACTIVE
            and status.response_mask == 0x3F
            and (
                status.last_received_sequence == first_sequence
                or is_newer_sequence(status.last_received_sequence, first_sequence)
            )
        ):
            return
        time.sleep(0.08)
    status_text = "no status"
    if node.latest_status is not None:
        status_text = (
            f"state={node.latest_status.state.name}, "
            f"reject={node.latest_status.reject_reason.name}, "
            f"mask=0x{node.latest_status.response_mask:02x}"
        )
    raise RuntimeError(f"Follower arming was not confirmed within {timeout:.1f}s ({status_text})")


def startup_blend(
    node: WirelessFollowerBridge,
    start: list[float],
    target: list[float],
    duration: float,
    rate: float,
    max_step: float,
    feedback_timeout: float,
    *,
    leader_source=None,
) -> list[float]:
    steps = max(1, round(duration * rate))
    command = list(start)
    period = 1.0 / rate
    next_tick = time.monotonic()
    for step in range(1, steps + 1):
        rclpy.spin_once(node, timeout_sec=0.0)
        node.log_latest_status()
        if leader_source is not None:
            now = time.monotonic()
            leader_source.get_action(now)
            update_leader_sample_context(node, leader_source, now)
        else:
            node.set_leader_sample(None, now=time.monotonic())
        if time.monotonic() - node.latest_monotonic > feedback_timeout:
            raise RuntimeError("Follower feedback timed out during startup synchronization")
        if node.latest_status is not None and status_matches_session(
            node.latest_status, node.session_id
        ) and node.latest_status.state is not FollowerState.ACTIVE:
            raise RuntimeError(
                f"Follower left ACTIVE state during startup: {node.latest_status.state.name}"
            )
        fraction = step / steps
        smooth = fraction * fraction * (3.0 - 2.0 * fraction)
        desired = [
            begin + (end - begin) * smooth
            for begin, end in zip(start, target, strict=True)
        ]
        command = limit_step(command, desired, max_step)
        node.publish_command(command)
        next_tick += period
        time.sleep(max(0.0, next_tick - time.monotonic()))
    return command


def run() -> None:
    args = parse_args()
    if args.rate <= 0.0:
        raise ValueError("--rate must be positive")
    if not 0.0 < args.max_step_rad < 0.25:
        raise ValueError("--max-step-rad must be between 0 and the firmware's 0.25-rad limit")
    if args.feedback_timeout <= 0.0 or args.recovery_timeout <= 0.0:
        raise ValueError("--feedback-timeout and --recovery-timeout must be positive")
    if args.startup_duration <= 0.0 or args.leader_recovery_blend_duration <= 0.0:
        raise ValueError("--startup-duration and --recovery-blend-duration must be positive")
    if args.leader_stale_timeout <= 0.0:
        raise ValueError("--leader-stale-timeout must be positive")

    follower_calibration = load_follower_calibration(args.follower_calibration)

    rclpy.init()
    node = WirelessFollowerBridge()
    metrics_writer = MetricsWriter(args.metrics_csv) if args.metrics_csv is not None else None
    leader_source = None
    try:
        if metrics_writer is not None:
            metrics_writer.__enter__()
        node.set_metrics_writer(metrics_writer)
        leader_source = build_leader_source(args, node)
        if args.leader_mode == "wired":
            print(f"Connecting leader on {args.leader_port}...", flush=True)
        else:
            print("Waiting for a ready wireless leader sample...", flush=True)
        leader_source.connect()
        if args.leader_mode == "wired":
            print("Leader EEPROM calibration matched", flush=True)

        follower_start = wait_for_follower(node)
        print(
            "Wireless follower feedback:",
            [round(value, 3) for value in follower_start],
            flush=True,
        )
        arm_at_current_pose(node, follower_start)
        print("Follower armed at its measured pose without a jump", flush=True)

        leader_origin = wait_for_leader(node, leader_source)
        follower_origin = list(follower_start)
        if args.mapping_mode == "relative":
            initial_target = list(follower_start)
        else:
            initial_target = absolute_target(leader_origin, follower_calibration)
        node.set_command_context(leader_origin, initial_target)
        update_leader_sample_context(node, leader_source, time.monotonic())
        command = startup_blend(
            node,
            follower_start,
            initial_target,
            args.startup_duration,
            args.rate,
            args.max_step_rad,
            args.feedback_timeout,
            leader_source=leader_source,
        )
        print(f"Initial synchronization complete ({args.mapping_mode} mapping)", flush=True)
        print("Live teleoperation active; press Ctrl+C to stop", flush=True)

        period = 1.0 / args.rate
        next_tick = time.monotonic()
        last_report = 0.0
        stale_since: float | None = None
        leader_outage = False
        leader_session_id = leader_source.boot_session_id
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            node.log_latest_status()
            now = time.monotonic()
            stale_since = update_feedback_recovery(
                now,
                node.latest_monotonic,
                stale_since,
                args.feedback_timeout,
                args.recovery_timeout,
            )
            if stale_since is not None:
                time.sleep(min(period, 0.05))
                continue

            try:
                action = leader_source.get_action(now)
            except LeaderUnavailable:
                leader_outage = True
                time.sleep(min(period, 0.05))
                continue

            session_changed = (
                leader_source.boot_session_id is not None
                and leader_session_id is not None
                and leader_source.boot_session_id != leader_session_id
            )
            if leader_outage or session_changed:
                try:
                    command = recover_leader_session(
                        node=node,
                        leader_source=leader_source,
                        now=now,
                        leader_origin=leader_origin,
                        follower_origin=follower_origin,
                        follower_calibration=follower_calibration,
                        mapping_mode=args.mapping_mode,
                        recovery_blend_duration=args.leader_recovery_blend_duration,
                        rate=args.rate,
                        max_step=args.max_step_rad,
                        feedback_timeout=args.feedback_timeout,
                        action=action,
                    )
                except LeaderUnavailable:
                    leader_outage = True
                    continue
                leader_outage = False
                leader_session_id = leader_source.boot_session_id
                next_tick = time.monotonic()
                print(
                    "Leader input recovered with a fresh follower session and smooth catch-up",
                    flush=True,
                )
                continue

            status = node.latest_status
            if (
                status is not None
                and status_matches_session(status, node.session_id)
                and status.state in (FollowerState.HOLDING_TIMEOUT, FollowerState.BUS_FAULT)
            ):
                previous_feedback = node.latest_monotonic
                try:
                    command = recover_leader_session(
                        node=node,
                        leader_source=leader_source,
                        now=now,
                        leader_origin=leader_origin,
                        follower_origin=follower_origin,
                        follower_calibration=follower_calibration,
                        mapping_mode=args.mapping_mode,
                        recovery_blend_duration=args.leader_recovery_blend_duration,
                        rate=args.rate,
                        max_step=args.max_step_rad,
                        feedback_timeout=args.feedback_timeout,
                        action=action,
                        after_monotonic=previous_feedback,
                    )
                except LeaderUnavailable:
                    leader_outage = True
                    continue
                next_tick = time.monotonic()
                print(
                    "Follower session recovered with a fresh handshake and smooth catch-up",
                    flush=True,
                )
                continue

            if args.mapping_mode == "relative":
                desired = relative_target(
                    action,
                    leader_origin,
                    follower_origin,
                    follower_calibration,
                )
            else:
                desired = absolute_target(action, follower_calibration)
            command = limit_step(command, desired, args.max_step_rad)
            node.set_command_context(action, command)
            update_leader_sample_context(node, leader_source, now)
            node.publish_command(command)

            if now - last_report >= 1.0:
                last_report = now
                print(
                    "leader:",
                    [round(action[f"{name}.pos"], 1) for name in JOINT_NAMES],
                    " follower:",
                    [round(value, 2) for value in (node.latest_positions or [])],
                    flush=True,
                )

            next_tick += period
            time.sleep(max(0.0, next_tick - time.monotonic()))
    except KeyboardInterrupt:
        print("Teleoperation stopped by user; follower holds its last commanded pose", flush=True)
    finally:
        if metrics_writer is not None:
            metrics_writer.__exit__(None, None, None)
        if leader_source is not None:
            leader_source.disconnect()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    run()
