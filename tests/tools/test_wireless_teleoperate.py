from types import SimpleNamespace

from builtin_interfaces.msg import Time

from tools.wireless_teleoperate import WirelessFollowerBridge


class _Publisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


class _Clock:
    def now(self):
        return SimpleNamespace(to_msg=Time)


def test_publish_command_records_sequence_for_metrics(monkeypatch):
    bridge = object.__new__(WirelessFollowerBridge)
    bridge.session_id = 0x12345678
    bridge.next_sequence = 7
    bridge.last_command_sequence = 0
    bridge.command_send_times = {}
    bridge.publisher = _Publisher()
    bridge.get_clock = lambda: _Clock()
    monkeypatch.setattr("tools.wireless_teleoperate.time.monotonic", lambda: 12.5)

    sequence = bridge.publish_command([0.0] * 6)

    assert sequence == 7
    assert bridge.last_command_sequence == 7
