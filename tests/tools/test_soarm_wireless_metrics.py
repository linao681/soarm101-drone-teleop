import csv

import pytest

from tools.soarm_wireless.metrics import METRICS_HEADER, MetricsWriter, summarize_rows


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
