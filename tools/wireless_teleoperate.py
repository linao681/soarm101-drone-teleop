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

from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
from tools.soarm_wireless.control import (
    JOINT_NAMES,
    absolute_target,
    capture_relative_origins,
    load_follower_calibration,
    relative_target,
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
    parser.add_argument("--leader-port", required=True, help="Leader USB serial port, e.g. /dev/ttyACM0")
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
        "--startup-duration",
        type=float,
        default=8.0,
        help="Seconds used to blend from the follower pose to the initial leader pose",
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
    return parser.parse_args()


def limit_step(previous: list[float], desired: list[float], maximum: float) -> list[float]:
    return [
        old + min(max(target - old, -maximum), maximum)
        for old, target in zip(previous, desired, strict=True)
    ]


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
        self.last_ack_latency_ms: float | None = None
        self.metrics_writer: MetricsWriter | None = None
        self.last_logged_status_monotonic = 0.0
        self.latest_leader: list[float] | None = None
        self.latest_target: list[float] | None = None
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
        self.latest_status = status
        self.latest_status_monotonic = time.monotonic()
        if status_matches_session(status, self.session_id):
            send_time = self.command_send_times.pop(status.last_applied_sequence, None)
            if send_time is not None:
                self.last_ack_latency_ms = (time.monotonic() - send_time) * 1000.0

    def reset_session(self) -> None:
        self.session_id = secrets.randbits(32)
        self.next_sequence = 1
        self.command_send_times.clear()
        self.last_ack_latency_ms = None

    def set_metrics_writer(self, writer: MetricsWriter | None) -> None:
        self.metrics_writer = writer

    def set_command_context(self, leader_action: dict[str, float], target: list[float]) -> None:
        self.latest_leader = [float(leader_action[f"{name}.pos"]) for name in JOINT_NAMES]
        self.latest_target = list(target)

    def log_latest_status(self) -> None:
        status = self.latest_status
        timestamp = self.latest_status_monotonic
        if (
            self.metrics_writer is None
            or status is None
            or timestamp <= self.last_logged_status_monotonic
        ):
            return
        measured = self.latest_positions or [""] * len(JOINT_NAMES)
        leader = self.latest_leader or [""] * len(JOINT_NAMES)
        target = self.latest_target or [""] * len(JOINT_NAMES)
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
        self.command_send_times[sequence] = time.monotonic()
        while len(self.command_send_times) > 256:
            self.command_send_times.pop(next(iter(self.command_send_times)))
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
) -> list[float]:
    steps = max(1, round(duration * rate))
    command = list(start)
    period = 1.0 / rate
    next_tick = time.monotonic()
    for step in range(1, steps + 1):
        rclpy.spin_once(node, timeout_sec=0.0)
        node.log_latest_status()
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

    follower_calibration = load_follower_calibration(args.follower_calibration)
    leader_config = SO101LeaderConfig(
        port=args.leader_port,
        id=args.leader_id,
        calibration_dir=args.calibration_dir,
        use_degrees=False,
    )
    leader = SO101Leader(leader_config)

    rclpy.init()
    node = WirelessFollowerBridge()
    metrics_writer = MetricsWriter(args.metrics_csv) if args.metrics_csv is not None else None
    try:
        if metrics_writer is not None:
            metrics_writer.__enter__()
        node.set_metrics_writer(metrics_writer)
        print(f"Connecting leader on {args.leader_port}...", flush=True)
        leader.connect(calibrate=False)
        if not leader.is_calibrated:
            raise RuntimeError(
                "Leader EEPROM calibration does not match "
                f"{leader.calibration_fpath}; recalibrate or restore it before teleoperation"
            )
        print(f"Leader calibration matched: {leader.calibration_fpath}", flush=True)

        follower_start = wait_for_follower(node)
        print(
            "Wireless follower feedback:",
            [round(value, 3) for value in follower_start],
            flush=True,
        )
        arm_at_current_pose(node, follower_start)
        print("Follower armed at its measured pose without a jump", flush=True)

        leader_origin = leader.get_action()
        follower_origin = list(follower_start)
        if args.mapping_mode == "relative":
            initial_target = list(follower_start)
        else:
            initial_target = absolute_target(leader_origin, follower_calibration)
        node.set_command_context(leader_origin, initial_target)
        command = startup_blend(
            node,
            follower_start,
            initial_target,
            args.startup_duration,
            args.rate,
            args.max_step_rad,
            args.feedback_timeout,
        )
        print(f"Initial synchronization complete ({args.mapping_mode} mapping)", flush=True)
        print("Live teleoperation active; press Ctrl+C to stop", flush=True)

        period = 1.0 / args.rate
        next_tick = time.monotonic()
        last_report = 0.0
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            node.log_latest_status()
            now = time.monotonic()
            if now - node.latest_monotonic > args.feedback_timeout:
                raise RuntimeError("Follower feedback timed out; command publishing stopped")

            status = node.latest_status
            if (
                status is not None
                and status_matches_session(status, node.session_id)
                and status.state in (FollowerState.HOLDING_TIMEOUT, FollowerState.BUS_FAULT)
            ):
                previous_feedback = node.latest_monotonic
                node.reset_session()
                follower_start = wait_for_follower(node, timeout=5.0, after_monotonic=previous_feedback)
                arm_at_current_pose(node, follower_start)
                leader_origin, follower_origin = capture_relative_origins(
                    leader.get_action(), follower_start
                )
                command = list(follower_start)
                next_tick = time.monotonic()
                print("Follower session recovered with a fresh near-current-pose handshake", flush=True)
                continue

            action = leader.get_action()
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
        if leader.is_connected:
            leader.disconnect()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    run()
