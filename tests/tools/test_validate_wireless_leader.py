import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.soarm_wireless.leader_protocol import (
    LeaderStateCode,
    leader_calibration_crc32,
)
from tools.validate_wireless_leader import (
    LeaderCapture,
    atomic_write_json,
    parse_args,
    validate_capture,
)


CALIBRATION = {
    "shoulder_pan": {"id": 1, "drive_mode": 0, "homing_offset": 1084, "range_min": 694, "range_max": 3349},
    "shoulder_lift": {"id": 2, "drive_mode": 0, "homing_offset": -1065, "range_min": 804, "range_max": 3220},
    "elbow_flex": {"id": 3, "drive_mode": 0, "homing_offset": 16, "range_min": 795, "range_max": 3080},
    "wrist_flex": {"id": 4, "drive_mode": 0, "homing_offset": 133, "range_min": 679, "range_max": 3084},
    "wrist_roll": {"id": 5, "drive_mode": 0, "homing_offset": 1925, "range_min": 0, "range_max": 4095},
    "gripper": {"id": 6, "drive_mode": 0, "homing_offset": -1891, "range_min": 1447, "range_max": 2808},
}


def _status(
    *,
    boot=99,
    last_sequence=0,
    state=LeaderStateCode.READY,
    response_mask=0x3F,
    model_match_mask=0x3F,
    torque_off_mask=0x3F,
    read_errors=10,
    torque_errors=4,
    crc=None,
):
    return [
        1,
        int(state),
        boot,
        last_sequence,
        response_mask,
        model_match_mask,
        torque_off_mask,
        leader_calibration_crc32(CALIBRATION) if crc is None else crc,
        100,
        read_errors,
        torque_errors,
        2000,
        -47,
    ]


def _raw(sequence, positions, *, boot=99, response_mask=0x3F):
    return [1, boot, sequence, sequence * 20, response_mask, *positions]


def test_validator_cli_requires_device_id_and_accepts_capture_options():
    args = parse_args(
        [
            "--device-id",
            "usb-leader-serial / mac-aa:bb",
            "--calibration",
            "leader.json",
            "--duration",
            "2.5",
            "--evidence-path",
            "evidence.json",
            "--yes",
        ]
    )

    assert args.device_id == "usb-leader-serial / mac-aa:bb"
    assert args.calibration == Path("leader.json")
    assert args.duration == pytest.approx(2.5)
    assert args.evidence_path == Path("evidence.json")
    assert args.yes is True


def test_validator_records_protocol_identity_health_and_joint_ranges():
    capture = LeaderCapture(CALIBRATION, device_id="usb-leader-serial / mac-aa:bb")
    capture.status_callback(SimpleNamespace(data=_status()))
    capture.raw_callback(SimpleNamespace(data=_raw(1, [700, 2000, 3000, 700, 1000, 1500])), received_at=0.00)
    capture.raw_callback(SimpleNamespace(data=_raw(2, [800, 2100, 3010, 710, 1100, 1600])), received_at=0.02)
    capture.raw_callback(SimpleNamespace(data=_raw(3, [900, 2200, 3020, 720, 1200, 1700])), received_at=0.04)
    capture.status_callback(SimpleNamespace(data=_status(read_errors=10, torque_errors=4)))

    evidence = capture.build_evidence(duration=0.04)

    assert evidence["protocol_version"] == 1
    assert evidence["device_id"] == "usb-leader-serial / mac-aa:bb"
    assert evidence["boot_session_id"] == 99
    assert evidence["masks"] == {"response": 0x3F, "model": 0x3F, "torque_off": 0x3F}
    assert evidence["calibration_crc32"] == leader_calibration_crc32(CALIBRATION)
    assert evidence["sample_frequency_hz"] == pytest.approx(50.0)
    assert evidence["rssi_dbm"] == -47
    assert evidence["read_error_delta"] == 0
    assert evidence["torque_error_delta"] == 0
    assert evidence["raw_ranges"]["shoulder_pan"] == {"min": 700, "max": 900}
    assert evidence["normalized_ranges"]["shoulder_pan"]["min"] < 0
    assert evidence["normalized_ranges"]["shoulder_pan"]["max"] < 0


def test_validator_frequency_uses_requested_duration_not_raw_sample_span():
    capture = LeaderCapture(CALIBRATION, device_id="leader")
    capture.status_callback(SimpleNamespace(data=_status()))
    positions = [700, 2000, 3000, 700, 1000, 1500]
    for sequence, received_at in enumerate((0.00, 0.02, 0.04), start=1):
        capture.raw_callback(
            SimpleNamespace(data=_raw(sequence, positions)), received_at=received_at
        )

    evidence = capture.build_evidence(duration=1.0)

    assert evidence["sample_count"] == 3
    assert evidence["sample_frequency_hz"] == pytest.approx(2.0)
    assert any("sample frequency" in failure for failure in validate_capture(capture, 1.0))


def test_validator_rejects_duplicate_and_older_raw_sequences():
    capture = LeaderCapture(CALIBRATION, device_id="leader")
    capture.status_callback(SimpleNamespace(data=_status(last_sequence=10)))
    positions = [700, 2000, 3000, 700, 1000, 1500]

    capture.raw_callback(SimpleNamespace(data=_raw(11, positions)), received_at=0.00)
    capture.raw_callback(SimpleNamespace(data=_raw(11, positions)), received_at=0.02)
    capture.raw_callback(SimpleNamespace(data=_raw(10, positions)), received_at=0.04)
    capture.raw_callback(SimpleNamespace(data=_raw(9, positions)), received_at=0.06)

    assert [sample.state.sequence for sample in capture.raw_samples] == [11]
    assert capture.rejected_samples == 3
    assert any("rejected" in failure for failure in validate_capture(capture, 1.0))


@pytest.mark.parametrize(
    ("status_kwargs", "raw_kwargs"),
    [
        ({"state": LeaderStateCode.BUS_FAULT}, {}),
        ({"response_mask": 0}, {}),
        ({"model_match_mask": 0}, {}),
        ({"torque_off_mask": 0}, {}),
        ({"crc": 0}, {}),
        ({}, {"boot": 100}),
        ({}, {"response_mask": 0}),
    ],
)
def test_validator_rejects_raw_samples_that_fail_protocol_gates(status_kwargs, raw_kwargs):
    capture = LeaderCapture(CALIBRATION, device_id="leader")
    capture.status_callback(SimpleNamespace(data=_status(**status_kwargs)))
    capture.raw_callback(
        SimpleNamespace(
            data=_raw(
                1,
                [700, 2000, 3000, 700, 1000, 1500],
                **raw_kwargs,
            )
        ),
        received_at=0.00,
    )

    assert capture.raw_samples == []
    assert capture.rejected_samples == 1
    assert any("rejected" in failure for failure in validate_capture(capture, 1.0))


def test_validator_resets_sequence_baseline_when_status_session_changes():
    capture = LeaderCapture(CALIBRATION, device_id="leader")
    positions = [700, 2000, 3000, 700, 1000, 1500]
    capture.status_callback(SimpleNamespace(data=_status(boot=99, last_sequence=100)))
    capture.raw_callback(SimpleNamespace(data=_raw(101, positions)), received_at=0.00)

    capture.status_callback(SimpleNamespace(data=_status(boot=100, last_sequence=5)))
    capture.raw_callback(
        SimpleNamespace(data=_raw(1, positions, boot=100)), received_at=0.02
    )
    capture.raw_callback(
        SimpleNamespace(data=_raw(6, positions, boot=100)), received_at=0.04
    )

    assert [sample.state.sequence for sample in capture.raw_samples] == [101, 6]
    assert capture.rejected_samples == 1


def test_validator_counts_invalid_and_rejected_messages_separately():
    capture = LeaderCapture(CALIBRATION, device_id="leader")
    capture.status_callback(SimpleNamespace(data=_status()))
    capture.raw_callback(SimpleNamespace(data=[1, 99]), received_at=0.00)
    capture.raw_callback(
        SimpleNamespace(
            data=_raw(1, [700, 2000, 3000, 700, 1000, 1500], response_mask=0)
        ),
        received_at=0.02,
    )

    evidence = capture.build_evidence(duration=1.0)

    assert evidence["sample_count"] == 0
    assert evidence["invalid_message_count"] == 1
    assert evidence["rejected_sample_count"] == 1
    failures = validate_capture(capture, 1.0)
    assert any("invalid" in failure for failure in failures)
    assert any("rejected" in failure for failure in failures)


def test_validator_is_read_only_and_writes_evidence_atomically(tmp_path: Path):
    source = Path(__file__).resolve().parents[2] / "tools" / "validate_wireless_leader.py"
    text = source.read_text()
    assert "create_publisher" not in text
    assert '"/joint_command"' not in text

    evidence_path = tmp_path / "leader-evidence.json"
    atomic_write_json(evidence_path, {"result": "PASS"})
    assert json.loads(evidence_path.read_text()) == {"result": "PASS"}
    assert list(tmp_path.glob("leader-evidence.json.*")) == []
