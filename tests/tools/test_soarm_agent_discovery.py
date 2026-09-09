from __future__ import annotations

import socket

import pytest

import tools.soarm_agent_discovery as discovery
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


def test_run_uses_interruptible_wait_for_signal_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    class StopEvent:
        def __init__(self) -> None:
            self.waited: list[float] = []
            self.stopped = False

        def is_set(self) -> bool:
            return self.stopped

        def wait(self, timeout: float) -> bool:
            self.waited.append(timeout)
            self.stopped = True
            return True

    class ServiceSocket(FakeSocket):
        def setsockopt(self, *_args: object) -> None:
            pass

        def bind(self, _address: tuple[str, int]) -> None:
            pass

        def settimeout(self, _timeout: float) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(discovery.secrets, "randbits", lambda _bits: 0x1234ABCD)
    event = StopEvent()
    discovery.run(
        discovery.parse_args(
            ["--bind-ip", "10.0.0.10", "--broadcast-ip", "10.0.0.255", "--interval", "3600"]
        ),
        event,
        socket_factory=lambda *_args: ServiceSocket([]),
    )
    assert event.waited == [3600.0]


def test_signal_handler_sets_shutdown_event(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers: dict[int, object] = {}
    monkeypatch.setattr(discovery.signal, "signal", lambda signum, handler: handlers.__setitem__(signum, handler))

    def fake_run(_args: argparse.Namespace, stop_event: object) -> None:
        handlers[discovery.signal.SIGTERM](discovery.signal.SIGTERM, None)
        assert stop_event.is_set()

    import argparse

    monkeypatch.setattr(discovery, "run", fake_run)
    assert discovery.main(["--bind-ip", "10.0.0.10", "--broadcast-ip", "10.0.0.255"]) == 0
    assert discovery.signal.SIGINT in handlers
    assert discovery.signal.SIGTERM in handlers


def test_auto_wifi_selection_derives_broadcast_from_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_ip_json(*args: str) -> object:
        calls.append(args)
        if args == ("-j", "-4", "route", "show", "default"):
            return [{"dev": "wlp2s0"}]
        return [
            {
                "ifname": "wlp2s0",
                "addr_info": [{"family": "inet", "local": "192.168.20.17", "prefixlen": 23}],
            }
        ]

    monkeypatch.setattr(discovery, "_run_ip_json", fake_ip_json)
    assert discovery._resolve_addresses(None, None) == ("192.168.20.17", "192.168.21.255")
    assert calls == [
        ("-j", "-4", "route", "show", "default"),
        ("-j", "-4", "addr", "show", "dev", "wlp2s0"),
    ]


def test_explicit_addresses_bypass_auto_wifi_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called() -> str:
        raise AssertionError("automatic Wi-Fi discovery should not run")

    monkeypatch.setattr(discovery, "_active_wifi_device", fail_if_called)
    assert discovery._resolve_addresses("10.0.0.10", "10.0.0.255") == (
        "10.0.0.10",
        "10.0.0.255",
    )
