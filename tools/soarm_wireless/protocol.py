from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum

PROTOCOL_VERSION = 1
STATUS_FIELD_COUNT = 14


class FollowerState(IntEnum):
    WAITING_HANDSHAKE = 0
    ACTIVE = 1
    HOLDING_TIMEOUT = 2
    BUS_FAULT = 3


class RejectReason(IntEnum):
    NONE = 0
    BAD_SHAPE = 1
    BAD_NAME = 2
    NONFINITE = 3
    OUT_OF_RANGE = 4
    STALE_COMMAND = 5
    BUS_NOT_READY = 6
    HANDSHAKE_MISMATCH = 7
    WRITE_FAILED = 8


def encode_command_id(session_id: int, sequence: int) -> str:
    return f"S1:{session_id & 0xFFFFFFFF:08x}:{sequence & 0xFFFFFFFF:08x}"


def decode_command_id(frame_id: str) -> tuple[int, int]:
    parts = frame_id.split(":")
    if len(parts) != 3 or parts[0] != "S1" or any(len(part) != 8 for part in parts[1:]):
        raise ValueError(f"Malformed SO-ARM command ID: {frame_id!r}")
    try:
        return int(parts[1], 16), int(parts[2], 16)
    except ValueError as error:
        raise ValueError(f"Malformed SO-ARM command ID: {frame_id!r}") from error


def is_newer_sequence(sequence: int, previous: int) -> bool:
    distance = (sequence - previous) & 0xFFFFFFFF
    return 0 < distance < 0x80000000


@dataclass(frozen=True)
class FollowerStatus:
    version: int
    state: FollowerState
    session_id: int
    last_received_sequence: int
    last_applied_sequence: int
    command_age_ms: int
    response_mask: int
    reject_reason: RejectReason
    command_timeout_count: int
    invalid_command_count: int
    control_reject_count: int
    read_errors: int
    write_errors: int
    rssi_dbm: int

    @classmethod
    def from_array(cls, values: Sequence[int]) -> FollowerStatus:
        if len(values) != STATUS_FIELD_COUNT:
            raise ValueError(f"Follower status must contain exactly {STATUS_FIELD_COUNT} integers")
        if values[0] != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported follower status version: {values[0]}")
        try:
            state = FollowerState(values[1])
            reject_reason = RejectReason(values[7])
        except ValueError as error:
            raise ValueError(f"Unknown follower status enum value: {error}") from error
        return cls(
            version=int(values[0]),
            state=state,
            session_id=int(values[2]) & 0xFFFFFFFF,
            last_received_sequence=int(values[3]) & 0xFFFFFFFF,
            last_applied_sequence=int(values[4]) & 0xFFFFFFFF,
            command_age_ms=int(values[5]),
            response_mask=int(values[6]),
            reject_reason=reject_reason,
            command_timeout_count=int(values[8]),
            invalid_command_count=int(values[9]),
            control_reject_count=int(values[10]),
            read_errors=int(values[11]),
            write_errors=int(values[12]),
            rssi_dbm=int(values[13]),
        )


def status_matches_session(status: FollowerStatus, session_id: int) -> bool:
    return status.session_id == (session_id & 0xFFFFFFFF)
