#!/usr/bin/env python3
"""Run the supervised SO-ARM101 wireless Gate 6 gripper test."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# The project-root bootstrap intentionally precedes project imports.
# ruff: noqa: E402

# Make ``python tools/validate_wireless_gate6.py`` work without requiring the
# caller to set PYTHONPATH, matching the documented Gate 6 command.
PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import rclpy

from tools.soarm_wireless.control import load_follower_calibration
from tools.soarm_wireless.gate6 import (
    GRIPPER_DELTA_RAD,
    POSITION_TOLERANCE_RAD,
    Gate6Error,
    build_target,
    evaluate_completion,
    validate_preflight,
    write_evidence,
)
from tools.soarm_wireless.protocol import FollowerState, RejectReason, is_newer_sequence
from tools.wireless_teleoperate import (
    WirelessFollowerBridge,
    arm_at_current_pose,
    wait_for_follower,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SO-ARM101 wireless Gate 6")
    parser.add_argument("--follower-calibration", type=Path, required=True)
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path("logs/gate-06") / f"gate6-{time.strftime('%Y%m%d-%H%M%S')}.json",
    )
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def require_confirmation(yes: bool) -> None:
    if yes:
        return
    print("Support the follower, clear the workspace, and be ready to remove servo power.")
    if input("Type MOVE to publish the +0.10 rad gripper command: ") != "MOVE":
        raise Gate6Error("operator did not confirm MOVE")


def status_to_list(status) -> list[int] | None:
    if status is None:
        return None
    return [
        status.version,
        int(status.state),
        status.session_id,
        status.last_received_sequence,
        status.last_applied_sequence,
        status.command_age_ms,
        status.response_mask,
        int(status.reject_reason),
        status.command_timeout_count,
        status.invalid_command_count,
        status.control_reject_count,
        status.read_errors,
        status.write_errors,
        status.rssi_dbm,
    ]


def current_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def wait_for_preflight_status(node: WirelessFollowerBridge, timeout_s: float = 1.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.02)
        if node.latest_status is not None and node.latest_positions is not None:
            return node.latest_status
    raise Gate6Error("no fresh follower status received during preflight")


def publish_until_acknowledged(
    node: WirelessFollowerBridge,
    target: list[float],
    expected_session_id: int,
    baseline_read_errors: int,
    baseline_write_errors: int,
    timeout_s: float = 3.0,
) -> int:
    deadline = time.monotonic() + timeout_s
    first_sequence = node.publish_command(target)
    next_publish = time.monotonic() + 0.05
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.02)
        if time.monotonic() - node.latest_monotonic > 0.5:
            raise Gate6Error("follower feedback became stale during movement")
        status = node.latest_status
        if status is None:
            continue
        if status.session_id != expected_session_id:
            raise Gate6Error("movement acknowledgment belongs to a different session")
        if status.response_mask != 0x3F or status.state is not FollowerState.ACTIVE:
            raise Gate6Error("follower left ACTIVE or lost a servo")
        if status.reject_reason is not RejectReason.NONE:
            raise Gate6Error(f"follower rejected movement: {status.reject_reason.name}")
        if status.read_errors != baseline_read_errors or status.write_errors != baseline_write_errors:
            raise Gate6Error("bus error counters increased during movement")
        if status.last_applied_sequence == first_sequence or is_newer_sequence(
            status.last_applied_sequence, first_sequence
        ):
            return first_sequence
        if time.monotonic() >= next_publish:
            node.publish_command(target)
            next_publish += 0.05
        time.sleep(0.03)
    raise Gate6Error("movement command was not acknowledged within 3 seconds")


def wait_for_measured_target(
    node: WirelessFollowerBridge, target: list[float], timeout_s: float = 1.0
) -> list[float]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.02)
        measured = node.latest_positions
        if measured is not None and all(
            abs(value - desired) <= POSITION_TOLERANCE_RAD
            for value, desired in zip(measured, target, strict=True)
        ):
            return list(measured)
    raise Gate6Error("follower did not reach the requested measured pose")


def run(args: argparse.Namespace) -> int:
    evidence: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": current_git_commit(),
        "joint": "gripper",
        "delta_rad": GRIPPER_DELTA_RAD,
        "result": "FAIL",
        "evidence_path": str(args.evidence_path),
    }
    node: WirelessFollowerBridge | None = None
    try:
        calibration = load_follower_calibration(args.follower_calibration)
        rclpy.init()
        node = WirelessFollowerBridge()
        start = wait_for_follower(node)
        status = wait_for_preflight_status(node)
        baseline_read_errors = status.read_errors
        baseline_write_errors = status.write_errors
        validate_preflight(status, baseline_read_errors, baseline_write_errors)
        target = build_target(start, calibration)
        evidence.update(
            {
                "session_id": node.session_id,
                "start": start,
                "target": target,
                "status_initial": status_to_list(status),
                "baseline_read_errors": baseline_read_errors,
                "baseline_write_errors": baseline_write_errors,
            }
        )
        require_confirmation(args.yes)
        handshake_first_sequence = node.next_sequence
        arm_at_current_pose(node, start)
        handshake_last_sequence = (node.next_sequence - 1) & 0xFFFFFFFF
        evidence.update(
            {
                "handshake_first_sequence": handshake_first_sequence,
                "handshake_last_sequence": handshake_last_sequence,
            }
        )
        movement_sequence = publish_until_acknowledged(
            node,
            target,
            node.session_id,
            baseline_read_errors,
            baseline_write_errors,
        )
        final = wait_for_measured_target(node, target)
        evaluate_completion(
            start,
            target,
            final,
            node.latest_status,
            node.session_id,
            baseline_read_errors,
            baseline_write_errors,
        )
        evidence.update(
            {
                "result": "PASS",
                "measured_final": final,
                "deltas": [value - begin for value, begin in zip(final, start, strict=True)],
                "movement_sequence": movement_sequence,
                "ack_latency_ms": node.last_ack_latency_ms,
            }
        )
        print(f"Gate 6 PASS; evidence: {args.evidence_path}")
        return 0
    except Exception as error:
        evidence["failure_reason"] = str(error)
        print(f"Gate 6 FAILED: {error}")
        return 1
    finally:
        if node is not None:
            evidence["status_final"] = status_to_list(node.latest_status)
            node.destroy_node()
        write_evidence(args.evidence_path, evidence)
        if rclpy.ok():
            rclpy.shutdown()


def main() -> None:
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
