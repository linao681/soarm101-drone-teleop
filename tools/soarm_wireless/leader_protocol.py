from __future__ import annotations

import json
import math
import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .control import JOINT_NAMES


LEADER_PROTOCOL_VERSION = 1
LEADER_RAW_FIELD_COUNT = 11
LEADER_STATUS_FIELD_COUNT = 13
EXPECTED_MODEL_NUMBER = 777
_JOINT_MASK = 0x3F


class LeaderStateCode(IntEnum):
    STARTING = 0
    WAITING_AGENT = 1
    READY = 2
    BUS_FAULT = 3


@dataclass(frozen=True)
class LeaderRawState:
    version: int
    boot_session_id: int
    sequence: int
    uptime_ms: int
    response_mask: int
    raw_positions: tuple[int, int, int, int, int, int]

    @classmethod
    def from_array(cls, values: Sequence[int]) -> LeaderRawState:
        if len(values) != LEADER_RAW_FIELD_COUNT:
            raise ValueError(
                f"Leader raw state must contain exactly {LEADER_RAW_FIELD_COUNT} integers"
            )
        if values[0] != LEADER_PROTOCOL_VERSION:
            raise ValueError(f"Unsupported leader raw state version: {values[0]}")
        response_mask = int(values[4])
        if not 0 <= response_mask <= _JOINT_MASK:
            raise ValueError(f"Invalid leader response mask: {response_mask}")
        return cls(
            version=int(values[0]),
            boot_session_id=int(values[1]) & 0xFFFFFFFF,
            sequence=int(values[2]) & 0xFFFFFFFF,
            uptime_ms=int(values[3]) & 0xFFFFFFFF,
            response_mask=response_mask,
            raw_positions=tuple(int(value) for value in values[5:]),
        )


@dataclass(frozen=True)
class LeaderStatus:
    version: int
    state: LeaderStateCode
    boot_session_id: int
    last_sequence: int
    response_mask: int
    model_match_mask: int
    torque_off_mask: int
    calibration_crc32: int
    read_cycles: int
    read_errors: int
    torque_errors: int
    uptime_ms: int
    rssi_dbm: int

    @classmethod
    def from_array(cls, values: Sequence[int]) -> LeaderStatus:
        if len(values) != LEADER_STATUS_FIELD_COUNT:
            raise ValueError(
                f"Leader status must contain exactly {LEADER_STATUS_FIELD_COUNT} integers"
            )
        if values[0] != LEADER_PROTOCOL_VERSION:
            raise ValueError(f"Unsupported leader status version: {values[0]}")
        try:
            state = LeaderStateCode(values[1])
        except ValueError as error:
            raise ValueError(f"Unknown leader state code: {values[1]}") from error
        masks = tuple(int(value) for value in values[4:7])
        if any(not 0 <= mask <= _JOINT_MASK for mask in masks):
            raise ValueError(f"Invalid leader status mask: {masks}")
        return cls(
            version=int(values[0]),
            state=state,
            boot_session_id=int(values[2]) & 0xFFFFFFFF,
            last_sequence=int(values[3]) & 0xFFFFFFFF,
            response_mask=masks[0],
            model_match_mask=masks[1],
            torque_off_mask=masks[2],
            calibration_crc32=int(values[7]) & 0xFFFFFFFF,
            read_cycles=int(values[8]) & 0xFFFFFFFF,
            read_errors=int(values[9]) & 0xFFFFFFFF,
            torque_errors=int(values[10]) & 0xFFFFFFFF,
            uptime_ms=int(values[11]) & 0xFFFFFFFF,
            rssi_dbm=int(values[12]),
        )


def _validate_calibration(calibration: dict) -> dict[str, dict[str, int]]:
    if tuple(calibration) != JOINT_NAMES:
        raise ValueError(
            f"Unexpected joints in calibration: {list(calibration)}; expected {list(JOINT_NAMES)}"
        )
    for expected_id, name in enumerate(JOINT_NAMES, start=1):
        values = calibration[name]
        if values.get("id") != expected_id:
            raise ValueError(f"{name} has ID {values.get('id')}, expected {expected_id}")
        try:
            homing_offset = int(values["homing_offset"])
            range_min = int(values["range_min"])
            range_max = int(values["range_max"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid calibration values for {name}: {values}") from error
        if not all(math.isfinite(float(value)) for value in (homing_offset, range_min, range_max)):
            raise ValueError(f"Non-finite calibration values for {name}: {values}")
        if range_min >= range_max:
            raise ValueError(f"Invalid range for {name}: {values}")
        if values.get("drive_mode", 0) not in (0, 1):
            raise ValueError(f"Unsupported drive_mode for {name}: {values.get('drive_mode')}")
    return calibration


def load_leader_calibration(path: Path) -> dict[str, dict[str, int]]:
    with path.open() as calibration_file:
        calibration = json.load(calibration_file)
    if not isinstance(calibration, dict):
        raise ValueError(f"Leader calibration must be an object: {path}")
    return _validate_calibration(calibration)


def leader_calibration_crc32(calibration: dict[str, dict[str, int]]) -> int:
    calibration = _validate_calibration(calibration)
    payload = b"".join(
        struct.pack(
            "<BHhHH",
            values["id"],
            EXPECTED_MODEL_NUMBER,
            values["homing_offset"],
            values["range_min"],
            values["range_max"],
        )
        for values in (calibration[name] for name in JOINT_NAMES)
    )
    return zlib.crc32(payload) & 0xFFFFFFFF


def normalize_leader_raw(
    raw_positions: Sequence[int], calibration: dict[str, dict[str, int]]
) -> dict[str, float]:
    calibration = _validate_calibration(calibration)
    if len(raw_positions) != len(JOINT_NAMES):
        raise ValueError(f"Leader raw state must contain exactly {len(JOINT_NAMES)} positions")
    action = {}
    for raw, name in zip(raw_positions, JOINT_NAMES):
        values = calibration[name]
        range_min = values["range_min"]
        range_max = values["range_max"]
        bounded = min(range_max, max(range_min, raw))
        if name == "gripper":
            norm = ((bounded - range_min) / (range_max - range_min)) * 100
            normalized = 100 - norm if values.get("drive_mode", 0) else norm
        else:
            norm = (((bounded - range_min) / (range_max - range_min)) * 200) - 100
            normalized = -norm if values.get("drive_mode", 0) else norm
        action[f"{name}.pos"] = normalized
    return action
