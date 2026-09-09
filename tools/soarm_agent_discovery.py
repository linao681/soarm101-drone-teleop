#!/usr/bin/env python3
"""Advertise the computer-side micro-ROS agent on the active Wi-Fi network."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import secrets
import signal
import socket
import subprocess
import time
from collections.abc import Callable


DISCOVERY_PORT = 8889
PROBE = b"SOARM_DISCOVER 1\n"
_ANNOUNCEMENT_RE = re.compile(r"SOARM_AGENT 1 ([0-9a-f]{8}) ([0-9]+)\n\Z")


def encode_announcement(nonce: int, agent_port: int) -> bytes:
    """Encode the discovery announcement packet."""
    if not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("nonce must fit in an unsigned 32-bit integer")
    if not 1 <= agent_port <= 65535:
        raise ValueError("agent_port must be between 1 and 65535")
    return f"SOARM_AGENT 1 {nonce:08x} {agent_port}\n".encode("ascii")


def decode_announcement(payload: bytes) -> tuple[int, int]:
    """Decode and validate an announcement packet."""
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("announcement is not ASCII") from exc
    match = _ANNOUNCEMENT_RE.fullmatch(text)
    if match is None:
        raise ValueError("invalid announcement fields")
    nonce_text, port_text = match.groups()
    try:
        nonce = int(nonce_text, 16)
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("invalid announcement fields") from exc
    if not 1 <= port <= 65535:
        raise ValueError("invalid agent port")
    return nonce, port


def serve_once(
    sock: socket.socket,
    nonce: int,
    agent_port: int,
    broadcast_target: tuple[str, int],
) -> None:
    """Send one broadcast and reply to at most one waiting valid probe."""
    announcement = encode_announcement(nonce, agent_port)
    sock.sendto(announcement, broadcast_target)
    while True:
        try:
            payload, sender = sock.recvfrom(4096)
        except (BlockingIOError, socket.timeout):
            return
        if payload != PROBE:
            continue
        sock.sendto(announcement, sender)
        return


def _run_ip_json(*args: str) -> object:
    output = subprocess.check_output(("ip", *args), text=True, stderr=subprocess.DEVNULL)
    return json.loads(output)


def _active_wifi_device() -> str:
    routes = _run_ip_json("-j", "-4", "route", "show", "default")
    for route in routes:
        device = route.get("dev")
        if isinstance(device, str) and _is_wifi_device(device):
            return device
    interfaces = _run_ip_json("-j", "-4", "addr", "show")
    for interface in interfaces:
        device = interface.get("ifname")
        if isinstance(device, str) and _is_wifi_device(device) and interface.get("operstate") == "UP":
            return device
    raise RuntimeError("could not find an active Wi-Fi interface")


def _is_wifi_device(device: str) -> bool:
    return device.startswith(("wl", "wlan"))


def _wifi_addresses(device: str) -> tuple[str, str]:
    interfaces = _run_ip_json("-j", "-4", "addr", "show", "dev", device)
    for interface in interfaces:
        for address in interface.get("addr_info", []):
            if address.get("family") != "inet":
                continue
            local = address.get("local")
            prefixlen = address.get("prefixlen")
            if isinstance(local, str) and isinstance(prefixlen, int):
                network = ipaddress.ip_network(f"{local}/{prefixlen}", strict=False)
                return local, str(network.broadcast_address)
    raise RuntimeError("active Wi-Fi interface has no IPv4 address")


def _resolve_addresses(bind_ip: str | None, broadcast_ip: str | None) -> tuple[str, str]:
    if bind_ip is None or broadcast_ip is None:
        device = _active_wifi_device()
        auto_bind, auto_broadcast = _wifi_addresses(device)
        bind_ip = bind_ip or auto_bind
        broadcast_ip = broadcast_ip or auto_broadcast
    return bind_ip, broadcast_ip


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind-ip", help="Local IPv4 address; defaults to the active Wi-Fi address")
    parser.add_argument(
        "--broadcast-ip",
        help="IPv4 broadcast address; defaults to the active Wi-Fi subnet broadcast",
    )
    parser.add_argument("--agent-port", type=int, default=8888, help="micro-ROS agent UDP port")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between announcements")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        # Keep signal handling simple while allowing the service loop to remain testable.
        run(args, lambda: stop)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"discovery service failed: {exc}")
        return 1
    return 0


def run(
    args: argparse.Namespace,
    should_stop: Callable[[], bool],
    *,
    socket_factory: Callable[..., socket.socket] = socket.socket,
) -> None:
    if args.interval <= 0:
        raise ValueError("interval must be positive")
    bind_ip, broadcast_ip = _resolve_addresses(args.bind_ip, args.broadcast_ip)
    nonce = secrets.randbits(32)
    print(f"discovery nonce {nonce:08x}", flush=True)
    sock = socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((bind_ip, DISCOVERY_PORT))
        sock.settimeout(0.0)
        while not should_stop():
            serve_once(sock, nonce, args.agent_port, (broadcast_ip, DISCOVERY_PORT))
            time.sleep(args.interval)
    finally:
        sock.close()


if __name__ == "__main__":
    raise SystemExit(main())
