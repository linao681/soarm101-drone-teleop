import pytest

from tools.soarm_wireless.protocol import (
    FollowerStatus,
    decode_command_id,
    encode_command_id,
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
