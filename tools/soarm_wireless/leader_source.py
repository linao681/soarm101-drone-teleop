from __future__ import annotations

from dataclasses import dataclass

from .leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
    normalize_leader_raw,
)
from .protocol import is_newer_sequence


class LeaderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class LeaderSample:
    boot_session_id: int
    sequence: int
    received_at: float
    action: dict[str, float]


class WirelessLeaderTracker:
    def __init__(self, calibration, stale_timeout_s=0.150):
        self._calibration = calibration
        self._calibration_crc32 = leader_calibration_crc32(calibration)
        self._stale_timeout_s = stale_timeout_s
        self.reset()

    def on_status(self, status: LeaderStatus, received_at: float) -> None:
        previous_status = self._status
        self._status = status
        self._status_received_at = received_at

        if previous_status is None or status.boot_session_id != previous_status.boot_session_id:
            self._last_sequence = status.last_sequence
            self._sample = None

        if status.state is not LeaderStateCode.READY:
            self.last_error = "status_not_ready"
        elif status.calibration_crc32 != self._calibration_crc32:
            self.last_error = "calibration_mismatch"
        elif not self._status_masks_ready(status):
            self.last_error = "status_mask_incomplete"
        elif self._sample is None:
            self.last_error = "no_sample"

    def on_raw_state(self, state: LeaderRawState, received_at: float) -> bool:
        status = self._status
        if status is None:
            return self._reject("status_missing")
        if status.state is not LeaderStateCode.READY:
            return self._reject("status_not_ready")
        if status.boot_session_id != state.boot_session_id:
            return self._reject("session_mismatch")
        if status.calibration_crc32 != self._calibration_crc32:
            return self._reject("calibration_mismatch")
        if not self._status_masks_ready(status) or state.response_mask != 0x3F:
            return self._reject("response_mask_incomplete")
        if self._last_sequence is not None and not is_newer_sequence(
            state.sequence, self._last_sequence
        ):
            return self._reject("sequence_not_newer")

        self._sample = LeaderSample(
            boot_session_id=state.boot_session_id,
            sequence=state.sequence,
            received_at=received_at,
            action=normalize_leader_raw(state.raw_positions, self._calibration),
        )
        self._last_sequence = state.sequence
        self.last_error = ""
        return True

    def get_action(self, now: float) -> dict[str, float]:
        status = self._status
        if status is None:
            self.last_error = "status_missing"
            raise LeaderUnavailable("leader status unavailable")
        if status.state is not LeaderStateCode.READY:
            self.last_error = "status_not_ready"
            raise LeaderUnavailable("leader is not ready")
        if status.calibration_crc32 != self._calibration_crc32:
            self.last_error = "calibration_mismatch"
            raise LeaderUnavailable("leader calibration mismatch")
        if not self._status_masks_ready(status):
            self.last_error = "status_mask_incomplete"
            raise LeaderUnavailable("leader status masks incomplete")
        if self._sample is None:
            if not self.last_error:
                self.last_error = "no_sample"
            raise LeaderUnavailable(f"leader sample unavailable: {self.last_error}")
        if self.sample_age(now) > self._stale_timeout_s:
            self.last_error = "sample_stale"
            raise LeaderUnavailable("leader sample is stale")
        return dict(self._sample.action)

    def sample_age(self, now: float) -> float | None:
        if self._sample is None:
            return None
        return now - self._sample.received_at

    def reset(self) -> None:
        self._status: LeaderStatus | None = None
        self._status_received_at: float | None = None
        self._sample: LeaderSample | None = None
        self._last_sequence: int | None = None
        self.last_error = "status_missing"

    @staticmethod
    def _status_masks_ready(status: LeaderStatus) -> bool:
        return (
            status.response_mask == 0x3F
            and status.model_match_mask == 0x3F
            and status.torque_off_mask == 0x3F
        )

    def _reject(self, error: str) -> bool:
        self.last_error = error
        return False
