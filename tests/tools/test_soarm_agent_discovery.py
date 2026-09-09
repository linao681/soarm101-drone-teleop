from __future__ import annotations

import socket

import pytest

from tools.soarm_agent_discovery import (
    PROBE,
    decode_announcement,
    encode_announcement,
    serve_once,
)


class FakeSocket:
    def __init__(self, incoming: list[tuple[bytes, tuple[str, int]]]) -> None:
        self.incoming = incoming
        self.sent: list[tuple[bytes, tuple[str, int]]] = []

    def sendto(self, payload: bytes, target: tuple[str, int]) -> None:
        self.sent.append((payload, target))

    def recvfrom(self, _size: int) -> tuple[bytes, tuple[str, int]]:
        if self.incoming:
            return self.incoming.pop(0)
        raise BlockingIOError


def test_announcement_round_trip() -> None:
    payload = encode_announcement(0x1234ABCD, 8888)
    assert payload == b"SOARM_AGENT 1 1234abcd 8888\n"
    assert decode_announcement(payload) == (0x1234ABCD, 8888)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"SOARM_AGENT 2 1234abcd 8888\n",
        b"SOARM_AGENT 1 nope 8888\n",
        b"SOARM_AGENT 1 1234abcd 0\n",
    ],
)
def test_invalid_announcement_is_rejected(payload: bytes) -> None:
    with pytest.raises(ValueError):
        decode_announcement(payload)


def test_probe_receives_unicast_announcement() -> None:
    sock = FakeSocket(incoming=[(PROBE, ("10.0.0.51", 45000))])
    serve_once(sock, nonce=0x1234ABCD, agent_port=8888, broadcast_target=("10.0.0.255", 8889))
    assert (b"SOARM_AGENT 1 1234abcd 8888\n", ("10.0.0.51", 45000)) in sock.sent


def test_serve_once_broadcasts_and_ignores_malformed_packets() -> None:
    sock = FakeSocket(
        incoming=[
            (b"not a probe", ("10.0.0.51", 45000)),
            (PROBE, ("10.0.0.52", 45001)),
        ]
    )
    serve_once(sock, nonce=0x1234ABCD, agent_port=8888, broadcast_target=("10.0.0.255", 8889))
    announcement = b"SOARM_AGENT 1 1234abcd 8888\n"
    assert sock.sent[0] == (announcement, ("10.0.0.255", 8889))
    assert sock.sent[1] == (announcement, ("10.0.0.52", 45001))


def test_serve_once_does_not_require_socket_timeout() -> None:
    class TimeoutSocket(FakeSocket):
        def recvfrom(self, _size: int) -> tuple[bytes, tuple[str, int]]:
            raise socket.timeout

    sock = TimeoutSocket([])
    serve_once(sock, nonce=1, agent_port=8888, broadcast_target=("10.0.0.255", 8889))
    assert len(sock.sent) == 1
