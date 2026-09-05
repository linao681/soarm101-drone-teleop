from __future__ import annotations

import csv
import math
import time
from collections.abc import Iterable, Mapping
from pathlib import Path

METRICS_HEADER = [
    "host_monotonic_s",
    "session_id",
    "command_sequence",
    "applied_sequence",
    "state",
    "reject_reason",
    "command_age_ms",
    "ack_latency_ms",
    "rssi_dbm",
    "response_mask",
    "leader_0",
    "leader_1",
    "leader_2",
    "leader_3",
    "leader_4",
    "leader_5",
    "target_0",
    "target_1",
    "target_2",
    "target_3",
    "target_4",
    "target_5",
    "measured_0",
    "measured_1",
    "measured_2",
    "measured_3",
    "measured_4",
    "measured_5",
]


class MetricsWriter:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._stream = None
        self._writer = None
        self._last_flush = 0.0

    def __enter__(self) -> MetricsWriter:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._stream, fieldnames=METRICS_HEADER)
        self._writer.writeheader()
        self._stream.flush()
        self._last_flush = time.monotonic()
        return self

    def write(self, row: Mapping[str, object]) -> None:
        if self._writer is None or self._stream is None:
            raise RuntimeError("MetricsWriter must be used as a context manager")
        self._writer.writerow({field: row.get(field, "") for field in METRICS_HEADER})
        if time.monotonic() - self._last_flush >= 1.0:
            self._stream.flush()
            self._last_flush = time.monotonic()

    def flush(self) -> None:
        if self._stream is not None:
            self._stream.flush()
            self._last_flush = time.monotonic()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.flush()
        if self._stream is not None:
            self._stream.close()
        self._stream = None
        self._writer = None


def _float(row: Mapping[str, object], key: str) -> float | None:
    value = row.get(key, "")
    if value in ("", None):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _int(row: Mapping[str, object], key: str) -> int | None:
    value = _float(row, key)
    return None if value is None else int(value)


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def summarize_rows(rows: Iterable[Mapping[str, object]]) -> dict[str, float | int]:
    rows = list(rows)
    timestamps = [value for row in rows if (value := _float(row, "host_monotonic_s")) is not None]
    command_sequences = {
        sequence
        for row in rows
        if (sequence := _int(row, "command_sequence")) is not None and sequence != 0
    }
    applied_sequences = {
        sequence
        for row in rows
        if (sequence := _int(row, "applied_sequence")) is not None and sequence != 0
    }
    ack_latencies = [
        value for row in rows if (value := _float(row, "ack_latency_ms")) is not None
    ]
    rssi_values = [value for row in rows if (value := _float(row, "rssi_dbm")) is not None]

    summary: dict[str, float | int] = {
        "commands_sent": len(command_sequences),
        "commands_applied": len(applied_sequences),
        "application_ratio": (
            len(applied_sequences) / len(command_sequences) if command_sequences else 0.0
        ),
        "feedback_samples": len(timestamps),
        "feedback_rate_hz": 0.0,
        "max_feedback_gap_ms": 0.0,
        "ack_latency_p50_ms": 0.0,
        "ack_latency_p95_ms": 0.0,
        "ack_latency_p99_ms": 0.0,
        "minimum_rssi_dbm": min(rssi_values) if rssi_values else 0.0,
        "timeout_count": sum(_int(row, "state") == 2 for row in rows),
        "rejections_total": sum(
            (_int(row, "reject_reason") or 0) != 0 for row in rows
        ),
        "run_duration_s": 0.0,
        "joint_rmse_rad": 0.0,
        "joint_max_error_rad": 0.0,
    }
    if len(timestamps) >= 2:
        duration = max(0.0, timestamps[-1] - timestamps[0])
        summary["run_duration_s"] = duration
        summary["feedback_rate_hz"] = len(timestamps) / duration if duration else 0.0
        summary["max_feedback_gap_ms"] = max(
            0.0,
            max(
                (current - previous) * 1000.0
                for previous, current in zip(timestamps, timestamps[1:], strict=False)
            ),
        )
    if ack_latencies:
        summary["ack_latency_p50_ms"] = _nearest_rank(ack_latencies, 0.50)
        summary["ack_latency_p95_ms"] = _nearest_rank(ack_latencies, 0.95)
        summary["ack_latency_p99_ms"] = _nearest_rank(ack_latencies, 0.99)

    squared_errors: list[float] = []
    for joint in range(6):
        joint_errors = []
        for row in rows:
            measured = _float(row, f"measured_{joint}")
            target = _float(row, f"target_{joint}")
            if measured is not None and target is not None:
                joint_errors.append(abs(measured - target))
        squared_errors.extend(error * error for error in joint_errors)
        summary[f"joint_{joint}_rmse_rad"] = (
            math.sqrt(sum(error * error for error in joint_errors) / len(joint_errors))
            if joint_errors
            else 0.0
        )
        summary[f"joint_{joint}_max_error_rad"] = max(joint_errors, default=0.0)

    if squared_errors:
        summary["joint_rmse_rad"] = math.sqrt(sum(squared_errors) / len(squared_errors))
        summary["joint_max_error_rad"] = math.sqrt(max(squared_errors))

    rejection_codes = sorted(
        {
            reason
            for row in rows
            if (reason := _int(row, "reject_reason")) is not None and reason != 0
        }
    )
    for reason in rejection_codes:
        summary[f"reject_reason_{reason}_count"] = sum(
            _int(row, "reject_reason") == reason for row in rows
        )
    return summary
