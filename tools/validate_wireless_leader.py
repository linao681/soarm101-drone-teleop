#!/usr/bin/env python3
"""Collect read-only evidence from the wireless SO-ARM101 leader."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

# Make ``python tools/validate_wireless_leader.py`` work from the documented
# project-root command without requiring the caller to set PYTHONPATH.
PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32MultiArray

from tools.soarm_wireless.control import JOINT_NAMES
from tools.soarm_wireless.leader_protocol import (
    LEADER_PROTOCOL_VERSION,
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
    load_leader_calibration,
    normalize_leader_raw,
)
from tools.soarm_wireless.protocol import is_newer_sequence


JOINT_MASK = 0x3F
MIN_SAMPLE_FREQUENCY_HZ = 45.0
MAX_SAMPLE_FREQUENCY_HZ = 55.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True, help="Non-secret USB serial or MAC identity")
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path("logs/wireless-leader") / "leader-validation.json",
    )
    parser.add_argument("--yes", action="store_true", help="Skip the OBSERVED operator prompt")
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("--duration must be positive")
    return args


def require_observed(yes: bool) -> None:
    if yes:
        return
    print("Keep the leader safely supported and observe its six-joint feedback.")
    if input("Type OBSERVED to start the read-only capture: ") != "OBSERVED":
        raise RuntimeError("operator did not confirm OBSERVED")


@dataclass(frozen=True)
class CapturedRaw:
    state: LeaderRawState
    received_at: float


class LeaderCapture:
    """Protocol-aware in-memory capture used by the ROS node and tests."""

    def __init__(self, calibration: dict[str, dict[str, int]], device_id: str) -> None:
        self.calibration = calibration
        self.device_id = device_id
        self.expected_crc32 = leader_calibration_crc32(calibration)
        self.first_status: LeaderStatus | None = None
        self.latest_status: LeaderStatus | None = None
        self.raw_samples: list[CapturedRaw] = []
        self.invalid_messages = 0
        self.rejected_samples = 0
        self._last_sequence: int | None = None

    def status_callback(self, message: SimpleNamespace) -> None:
        try:
            status = LeaderStatus.from_array(list(message.data))
        except (TypeError, ValueError):
            self.invalid_messages += 1
            return
        previous_status = self.latest_status
        if self.first_status is None:
            self.first_status = status
        self.latest_status = status
        if previous_status is None or status.boot_session_id != previous_status.boot_session_id:
            self._last_sequence = status.last_sequence

    def raw_callback(self, message: SimpleNamespace, received_at: float | None = None) -> None:
        try:
            state = LeaderRawState.from_array(list(message.data))
        except (TypeError, ValueError):
            self.invalid_messages += 1
            return
        status = self.latest_status
        if status is None:
            self.rejected_samples += 1
            return
        if status.state is not LeaderStateCode.READY:
            self.rejected_samples += 1
            return
        if any(
            mask != JOINT_MASK
            for mask in (status.response_mask, status.model_match_mask, status.torque_off_mask)
        ):
            self.rejected_samples += 1
            return
        if status.calibration_crc32 != self.expected_crc32:
            self.rejected_samples += 1
            return
        if state.boot_session_id != status.boot_session_id:
            self.rejected_samples += 1
            return
        if state.response_mask != JOINT_MASK:
            self.rejected_samples += 1
            return
        if self._last_sequence is not None and not is_newer_sequence(
            state.sequence, self._last_sequence
        ):
            self.rejected_samples += 1
            return
        self.raw_samples.append(
            CapturedRaw(state, time.monotonic() if received_at is None else received_at)
        )
        self._last_sequence = state.sequence

    def build_evidence(self, duration: float) -> dict[str, object]:
        status = self.latest_status
        samples = self.raw_samples
        frequency = (len(samples) - 1) / duration if len(samples) >= 2 and duration > 0 else 0.0

        raw_ranges = {
            name: {
                "min": min((sample.state.raw_positions[index] for sample in samples), default=None),
                "max": max((sample.state.raw_positions[index] for sample in samples), default=None),
            }
            for index, name in enumerate(JOINT_NAMES)
        }
        normalized_values = {name: [] for name in JOINT_NAMES}
        for sample in samples:
            normalized = normalize_leader_raw(sample.state.raw_positions, self.calibration)
            for name in JOINT_NAMES:
                normalized_values[name].append(normalized[f"{name}.pos"])
        normalized_ranges = {
            name: {
                "min": min(values, default=None),
                "max": max(values, default=None),
            }
            for name, values in normalized_values.items()
        }

        initial_read = self.first_status.read_errors if self.first_status else None
        final_read = status.read_errors if status else None
        initial_torque = self.first_status.torque_errors if self.first_status else None
        final_torque = status.torque_errors if status else None
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "device_id": self.device_id,
            "protocol_version": LEADER_PROTOCOL_VERSION,
            "duration_s": duration,
            "boot_session_id": None if status is None else status.boot_session_id,
            "state": None if status is None else status.state.name,
            "masks": None
            if status is None
            else {
                "response": status.response_mask,
                "model": status.model_match_mask,
                "torque_off": status.torque_off_mask,
            },
            "calibration_crc32": None if status is None else status.calibration_crc32,
            "expected_calibration_crc32": self.expected_crc32,
            "sample_count": len(samples),
            "sample_frequency_hz": frequency,
            "rssi_dbm": None if status is None else status.rssi_dbm,
            "read_error_delta": None
            if initial_read is None or final_read is None
            else final_read - initial_read,
            "torque_error_delta": None
            if initial_torque is None or final_torque is None
            else final_torque - initial_torque,
            "raw_ranges": raw_ranges,
            "normalized_ranges": normalized_ranges,
            "invalid_message_count": self.invalid_messages,
            "rejected_sample_count": self.rejected_samples,
        }


def validate_capture(capture: LeaderCapture, duration: float) -> list[str]:
    status = capture.latest_status
    failures: list[str] = []
    if status is None:
        return ["no leader status received"]
    if status.state is not LeaderStateCode.READY:
        failures.append(f"leader state is {status.state.name}, expected READY")
    if any(
        mask != JOINT_MASK
        for mask in (status.response_mask, status.model_match_mask, status.torque_off_mask)
    ):
        failures.append("leader status masks are not 0x3f")
    if status.calibration_crc32 != capture.expected_crc32:
        failures.append("leader calibration CRC does not match the selected calibration")
    evidence = capture.build_evidence(duration)
    frequency = float(evidence["sample_frequency_hz"])
    if not MIN_SAMPLE_FREQUENCY_HZ <= frequency <= MAX_SAMPLE_FREQUENCY_HZ:
        failures.append(f"leader sample frequency is {frequency:.2f} Hz, expected 45-55 Hz")
    if evidence["read_error_delta"] != 0:
        failures.append("leader read error counter increased")
    if evidence["torque_error_delta"] != 0:
        failures.append("leader torque error counter increased")
    if not capture.raw_samples:
        failures.append("no leader raw state samples received")
    if any(sample.state.boot_session_id != status.boot_session_id for sample in capture.raw_samples):
        failures.append("leader raw samples span multiple boot sessions")
    if capture.invalid_messages:
        failures.append("invalid leader protocol messages were received")
    return failures


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


class LeaderValidatorNode(Node):
    def __init__(self, capture: LeaderCapture) -> None:
        super().__init__("soarm_wireless_leader_validator")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Int32MultiArray, "/leader/raw_state", capture.raw_callback, qos)
        self.create_subscription(Int32MultiArray, "/leader/status", capture.status_callback, qos)


def run(args: argparse.Namespace) -> int:
    evidence: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "device_id": args.device_id,
        "result": "FAIL",
        "evidence_path": str(args.evidence_path),
    }
    node: LeaderValidatorNode | None = None
    capture: LeaderCapture | None = None
    try:
        calibration = load_leader_calibration(args.calibration)
        capture = LeaderCapture(calibration, args.device_id)
        require_observed(args.yes)
        rclpy.init()
        node = LeaderValidatorNode(capture)
        started = time.monotonic()
        while time.monotonic() - started < args.duration:
            rclpy.spin_once(node, timeout_sec=min(0.05, args.duration))
        evidence.update(capture.build_evidence(args.duration))
        failures = validate_capture(capture, args.duration)
        evidence["failures"] = failures
        if not failures:
            evidence["result"] = "PASS"
            print(f"Wireless leader PASS; evidence: {args.evidence_path}")
            return 0
        print("Wireless leader FAILED: " + "; ".join(failures))
        return 1
    except Exception as error:
        evidence["failure_reason"] = str(error)
        print(f"Wireless leader FAILED: {error}")
        return 1
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        atomic_write_json(args.evidence_path, evidence)


def main() -> None:
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
