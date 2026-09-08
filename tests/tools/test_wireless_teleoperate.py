from pathlib import Path
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


def test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta():
    source = (Path(__file__).parents[2] / "tools" / "validate_wireless_gate6.py").read_text()

    assert 'parser.add_argument("--yes", action="store_true")' in source
    assert "sys.path.insert" in source
    assert "GRIPPER_DELTA_RAD" in source
    assert "arm_at_current_pose(node, start)" in source
    assert "node.publish_command(target)" in source
    assert "write_evidence" in source
