import pytest

from tools.soarm_wireless.control import capture_relative_origins
from tools.soarm_wireless.protocol import (
    FollowerStatus,
    decode_command_id,
    encode_command_id,
    is_newer_sequence,
    status_matches_session,
)


def test_command_id_round_trip():
    encoded = encode_command_id(0x89ABCDEF, 0x10203040)
    assert encoded == "S1:89abcdef:10203040"
    assert decode_command_id(encoded) == (0x89ABCDEF, 0x10203040)


@pytest.mark.parametrize("bad", ["", "S2:00000001:00000002", "S1:xyz:1", "S1:1"])
def test_command_id_rejects_malformed_input(bad):
    with pytest.raises(ValueError):
        decode_command_id(bad)


def test_status_requires_exact_schema_length():
    with pytest.raises(ValueError, match="14 integers"):
        FollowerStatus.from_array([1, 2])


def test_sequence_wrap_is_forward_progress():
    assert is_newer_sequence(0x00000000, 0xFFFFFFFF)
    assert not is_newer_sequence(0xFFFFFFFF, 0x00000000)


def test_foreign_session_status_is_not_owned():
    values = [1, 1, 0x12345678, 4, 4, 10, 0x3F, 0, 0, 0, 0, 0, 0, -50]
    status = FollowerStatus.from_array(values)
    assert status_matches_session(status, 0x12345678)
    assert not status_matches_session(status, 0x87654321)


def test_recovery_origins_are_copies():
    leader = {"shoulder_pan.pos": 12.0}
    follower = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    leader_origin, follower_origin = capture_relative_origins(leader, follower)
    leader["shoulder_pan.pos"] = 99.0
    follower[0] = 99.0
    assert leader_origin == {"shoulder_pan.pos": 12.0}
    assert follower_origin == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
