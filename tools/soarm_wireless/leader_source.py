from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Int32MultiArray

from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig

from .leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
    load_leader_calibration,
    normalize_leader_raw,
)
from .protocol import is_newer_sequence


class LeaderUnavailable(RuntimeError):
    pass


class WiredLeaderSource:
    """Common leader-source adapter for the existing USB SO-101 leader."""

    def __init__(
        self,
        port: str,
        leader_id: str = "leader_recal",
        calibration_dir: Path = Path("/home/linao/so101_lerobot/cali"),
        *,
        leader=None,
    ) -> None:
        if leader is None:
            config = SO101LeaderConfig(
                port=port,
                id=leader_id,
                calibration_dir=calibration_dir,
                use_degrees=False,
            )
            leader = SO101Leader(config)
        self._leader = leader

    @property
    def is_connected(self) -> bool:
        return bool(self._leader.is_connected)

    @property
    def boot_session_id(self) -> None:
        return None

    def connect(self) -> None:
        self._leader.connect(calibrate=False)
        if not self._leader.is_calibrated:
            raise RuntimeError(
                "Leader EEPROM calibration does not match "
                f"{self._leader.calibration_fpath}; recalibrate or restore it before teleoperation"
            )

    def get_action(self, now: float | None = None) -> dict[str, float]:
        del now
        return dict(self._leader.get_action())

    def disconnect(self) -> None:
        if self._leader.is_connected:
            self._leader.disconnect()


class WirelessLeaderSource:
    """ROS adapter that gates raw leader samples through ``WirelessLeaderTracker``."""

    def __init__(self, node, calibration_path: Path, stale_timeout_s: float = 0.150) -> None:
        self._node = node
        self._tracker = WirelessLeaderTracker(
            load_leader_calibration(Path(calibration_path)), stale_timeout_s=stale_timeout_s
        )
        self._connected = False
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._raw_subscription = node.create_subscription(
            Int32MultiArray, "/leader/raw_state", self._raw_callback, qos
        )
        self._status_subscription = node.create_subscription(
            Int32MultiArray, "/leader/status", self._status_callback, qos
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def boot_session_id(self) -> int | None:
        sample = self._tracker.sample
        return None if sample is None else sample.boot_session_id

    @property
    def last_error(self) -> str:
        return self._tracker.last_error

    def connect(self) -> None:
        self._connected = True

    def get_action(self, now: float | None = None) -> dict[str, float]:
        if not self._connected:
            raise LeaderUnavailable("wireless leader source is disconnected")
        return self._tracker.get_action(time.monotonic() if now is None else now)

    def disconnect(self) -> None:
        self._connected = False
        self._tracker.reset()

    def _status_callback(self, message: Int32MultiArray) -> None:
        try:
            status = LeaderStatus.from_array(list(message.data))
        except (TypeError, ValueError):
            self._tracker.last_error = "invalid_status"
            return
        self._tracker.on_status(status, received_at=time.monotonic())

    def _raw_callback(self, message: Int32MultiArray) -> None:
        try:
            state = LeaderRawState.from_array(list(message.data))
        except (TypeError, ValueError):
            self._tracker.last_error = "invalid_raw_state"
            return
        self._tracker.on_raw_state(state, received_at=time.monotonic())


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

    @property
    def sample(self) -> LeaderSample | None:
        return self._sample

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
