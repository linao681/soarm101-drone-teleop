import csv
from types import SimpleNamespace

import pytest
from builtin_interfaces.msg import Time

from tools.soarm_wireless.metrics import METRICS_HEADER, MetricsWriter, summarize_rows
from tools.wireless_teleoperate import WirelessFollowerBridge

LEADER_METRICS_FIELDS = {
    "leader_boot_session_id",
    "leader_sample_sequence",
    "leader_sample_gap_ms",
    "leader_sample_age_ms",
    "leader_response_mask",
    "leader_model_mask",
    "leader_torque_off_mask",
    "leader_calibration_crc32",
    "leader_read_errors",
    "leader_torque_errors",
    "leader_rssi_dbm",
    "leader_recovery_count",
    "control_chain_ack_latency_ms",
}


@pytest.fixture
def sample_rows():
    rows = []
    for index, timestamp in enumerate((0.00, 0.05, 0.17, 0.22, 0.27), start=1):
        row = {
            "host_monotonic_s": timestamp,
            "session_id": 7,
            "command_sequence": index,
            "applied_sequence": index if index != 3 else 0,
            "state": 1,
            "reject_reason": 0 if index != 3 else 5,
            "command_age_ms": 20,
            "ack_latency_ms": 10.0 + index,
            "rssi_dbm": -48,
            "response_mask": 63,
        }
        for joint in range(6):
            row[f"leader_{joint}"] = 0.0
            row[f"target_{joint}"] = 0.0
            row[f"measured_{joint}"] = 0.1
        rows.append(row)
    return rows


def test_summary_computes_loss_latency_gap_and_tracking_error(sample_rows):
    summary = summarize_rows(sample_rows)
    assert summary["commands_sent"] == 5
    assert summary["commands_applied"] == 4
    assert summary["application_ratio"] == pytest.approx(0.8)
    assert summary["max_feedback_gap_ms"] == pytest.approx(120.0)
    assert summary["joint_rmse_rad"] == pytest.approx(0.1)


def test_metrics_writer_uses_stable_header(tmp_path, sample_rows):
    path = tmp_path / "wireless.csv"
    with MetricsWriter(path) as writer:
        writer.write(sample_rows[0])

    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == METRICS_HEADER
    assert len(rows) == 2


def test_header_includes_wireless_leader_health_fields():
    assert set(METRICS_HEADER) >= LEADER_METRICS_FIELDS


@pytest.fixture
def wireless_leader_rows():
    rows = []
    for index, (timestamp, sequence, recovery, latency) in enumerate(
        ((10.00, 100, 0, 40.0), (10.02, 101, 0, 60.0), (10.04, 2, 1, 82.0)),
        start=1,
    ):
        row = {
            "host_monotonic_s": timestamp,
            "session_id": 7,
            "command_sequence": index,
            "applied_sequence": index,
            "state": 1,
            "reject_reason": 0,
            "command_age_ms": 20,
            "ack_latency_ms": 10.0 + index,
            "rssi_dbm": -48,
            "response_mask": 63,
            "leader_boot_session_id": 7 if recovery == 0 else 8,
            "leader_sample_sequence": sequence,
            "leader_sample_gap_ms": 20.0,
            "leader_sample_age_ms": 4.0,
            "leader_response_mask": 63,
            "leader_model_mask": 63,
            "leader_torque_off_mask": 63,
            "leader_calibration_crc32": 0x12345678,
            "leader_read_errors": 0,
            "leader_torque_errors": 0,
            "leader_rssi_dbm": -42,
            "leader_recovery_count": recovery,
            "control_chain_ack_latency_ms": latency,
        }
        for joint in range(6):
            row[f"leader_{joint}"] = 0.0
            row[f"target_{joint}"] = 0.0
            row[f"measured_{joint}"] = 0.1
        rows.append(row)
    return rows


def test_summary_computes_wireless_leader_rate_recovery_and_control_chain(
    wireless_leader_rows,
):
    summary = summarize_rows(wireless_leader_rows)

    assert summary["leader_sample_rate_hz"] == pytest.approx(50.0)
    assert summary["leader_max_sample_gap_ms"] == pytest.approx(20.0)
    assert summary["leader_recovery_count"] == 1
    assert summary["control_chain_ack_latency_p50_ms"] == 60.0
    assert summary["control_chain_ack_latency_p95_ms"] == 82.0
    assert summary["control_chain_ack_latency_p99_ms"] == 82.0
    assert summary["commands_sent"] == 3
    assert summary["ack_latency_p95_ms"] == 13.0


def test_summary_deduplicates_leader_samples_and_excludes_session_switch_gaps():
    rows = []
    for sequence, session_id, gap_ms, duplicate_count in (
        (100, 1, "", 2),
        (101, 1, 100.0, 4),
        (1, 2, "", 3),
        (2, 2, 25.0, 1),
    ):
        for _ in range(duplicate_count):
            rows.append(
                {
                    "leader_boot_session_id": session_id,
                    "leader_sample_sequence": sequence,
                    "leader_sample_gap_ms": gap_ms,
                }
            )

    summary = summarize_rows(rows)

    assert summary["leader_sample_rate_hz"] == pytest.approx(16.0)
    assert summary["leader_max_sample_gap_ms"] == pytest.approx(100.0)
    assert summary["leader_recovery_count"] == 1


def test_bridge_uses_pc_leader_receive_time_for_control_chain_ack(monkeypatch):
    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 7
    bridge.next_sequence = 4
    bridge.last_command_sequence = 0
    bridge.command_send_times = {}
    bridge.command_leader_samples = {}
    bridge.command_control_chain_ack_latencies = {}
    bridge.latest_leader_sample = None
    bridge.pending_leader_sample = None
    bridge.previous_leader_sample_key = None
    bridge.previous_leader_sample_received_at = None
    bridge.leader_recovery_count = 0
    bridge.last_ack_latency_ms = None
    bridge.last_control_chain_ack_latency_ms = None
    bridge.publisher = SimpleNamespace(publish=lambda message: None)
    bridge.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(to_msg=lambda: Time())
    )
    monkeypatch.setattr("tools.wireless_teleoperate.time.monotonic", lambda: 10.082)

    bridge.set_leader_sample(
        {
            "boot_session_id": 7,
            "sequence": 100,
            "received_at": 10.000,
        },
        now=10.001,
    )
    bridge.publish_command([0.0] * 6)
    bridge._status_callback(
        SimpleNamespace(data=[1, 1, 7, 4, 4, 9999, 63, 0, 0, 0, 0, 0, 0, -48])
    )

    assert bridge.last_control_chain_ack_latency_ms == pytest.approx(82.0)


def test_bridge_keeps_first_control_chain_ack_latency_for_duplicate_status(monkeypatch):
    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 7
    bridge.command_send_times = {4: 10.5}
    bridge.command_leader_samples = {(7, 4): {"received_at": 10.0}}
    bridge.command_control_chain_ack_latencies = {}
    bridge.last_ack_latency_ms = None
    bridge.last_control_chain_ack_latency_ms = None
    status_message = SimpleNamespace(
        data=[1, 1, 7, 4, 4, 9999, 63, 0, 0, 0, 0, 0, 0, -48]
    )
    monotonic_values = iter((11.0, 12.0))
    monkeypatch.setattr(
        "tools.wireless_teleoperate.time.monotonic", lambda: next(monotonic_values)
    )

    bridge._status_callback(status_message)
    bridge._status_callback(status_message)

    assert bridge.last_control_chain_ack_latency_ms == pytest.approx(1000.0)
    assert bridge.command_control_chain_ack_latencies[(7, 4)] == pytest.approx(1000.0)
    assert bridge.last_ack_latency_ms == pytest.approx(500.0)
