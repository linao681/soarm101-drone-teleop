#!/usr/bin/env python3
"""Teleoperate a micro-ROS SO-101 follower from a USB-connected SO-101 leader."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState

from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig


JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]
BODY_JOINTS = set(JOINT_NAMES[:-1])
ENCODER_RESOLUTION = 4096.0
TWO_PI = 2.0 * math.pi


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
    return parser.parse_args()


def load_follower_calibration(path: Path) -> dict[str, dict[str, int]]:
    with path.open() as calibration_file:
        calibration = json.load(calibration_file)

    if list(calibration) != JOINT_NAMES:
        raise ValueError(
            f"Unexpected joints in {path}: {list(calibration)}; expected {JOINT_NAMES}"
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


def leader_action_to_follower_radians(
    action: dict[str, float], calibration: dict[str, dict[str, int]]
) -> list[float]:
    positions = []
    for name in JOINT_NAMES:
        key = f"{name}.pos"
        if key not in action or not math.isfinite(action[key]):
            raise ValueError(f"Invalid or missing leader value for {key}")

        normalized = float(action[key])
        if name in BODY_JOINTS:
            normalized = min(100.0, max(-100.0, normalized))
            fraction = (normalized + 100.0) / 200.0
        else:
            normalized = min(100.0, max(0.0, normalized))
            fraction = normalized / 100.0

        minimum = calibration[name]["range_min"]
        maximum = calibration[name]["range_max"]
        raw = minimum + fraction * (maximum - minimum)
        positions.append((raw - ENCODER_RESOLUTION / 2.0) * TWO_PI / ENCODER_RESOLUTION)
    return positions


def leader_delta_to_follower_radians(
    action: dict[str, float],
    leader_origin: dict[str, float],
    follower_origin: list[float],
    calibration: dict[str, dict[str, int]],
) -> list[float]:
    positions = []
    for index, name in enumerate(JOINT_NAMES):
        key = f"{name}.pos"
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
        positions.append((raw - ENCODER_RESOLUTION / 2.0) * TWO_PI / ENCODER_RESOLUTION)
    return positions


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
        self.create_subscription(JointState, "/joint_states", self._state_callback, qos)
        self.publisher = self.create_publisher(JointState, "/joint_command", qos)

    def _state_callback(self, message: JointState) -> None:
        if list(message.name) != JOINT_NAMES or len(message.position) != len(JOINT_NAMES):
            return
        values = list(message.position)
        if not all(math.isfinite(value) for value in values):
            return
        self.latest_positions = values
        self.latest_monotonic = time.monotonic()

    def publish_command(self, positions: list[float]) -> None:
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = JOINT_NAMES
        message.position = positions
        self.publisher.publish(message)


def wait_for_follower(node: WirelessFollowerBridge, timeout: float = 12.0) -> list[float]:
    deadline = time.monotonic() + timeout
    while node.latest_positions is None and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.latest_positions is None:
        raise RuntimeError("No /joint_states received from the wireless follower")
    return list(node.latest_positions)


def arm_at_current_pose(node: WirelessFollowerBridge, current: list[float]) -> None:
    # Let DDS discovery finish, then repeat the no-jump handshake to tolerate
    # best-effort packet loss.
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    for _ in range(10):
        node.publish_command(current)
        rclpy.spin_once(node, timeout_sec=0.05)
        time.sleep(0.05)


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
        if time.monotonic() - node.latest_monotonic > feedback_timeout:
            raise RuntimeError("Follower feedback timed out during startup synchronization")
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
    try:
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

        initial_action = leader.get_action()
        if args.mapping_mode == "relative":
            initial_target = list(follower_start)
        else:
            initial_target = leader_action_to_follower_radians(initial_action, follower_calibration)
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
            now = time.monotonic()
            if now - node.latest_monotonic > args.feedback_timeout:
                raise RuntimeError("Follower feedback timed out; command publishing stopped")

            action = leader.get_action()
            if args.mapping_mode == "relative":
                desired = leader_delta_to_follower_radians(
                    action,
                    initial_action,
                    follower_start,
                    follower_calibration,
                )
            else:
                desired = leader_action_to_follower_radians(action, follower_calibration)
            command = limit_step(command, desired, args.max_step_rad)
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
        if leader.is_connected:
            leader.disconnect()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    run()
