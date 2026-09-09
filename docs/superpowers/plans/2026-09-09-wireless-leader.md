# SO-ARM101 Wireless Leader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the normal USB-connected SO-ARM101 leader input with a 50 Hz XIAO ESP32-C3 WiFi leader while retaining the computer as the calibration, safety, recovery, and logging bridge and preserving an explicit wired fallback.

**Architecture:** A dedicated leader firmware reads six raw STS3215 positions, verifies model/calibration identity, forces and confirms torque-off, and publishes versioned raw state plus health status through micro-ROS. The computer discovers both XIAOs without a fixed agent IP, normalizes leader samples with `cali/my_leader.json`, and feeds the existing follower command/session path. The work is gated through PC-only tests, native firmware tests, two ESP32-C3 builds, USB-only upload evidence, powered leader-only evidence, and finally staged two-arm evidence.

**Tech Stack:** Python 3.10, pytest, ROS 2 Humble/rclpy, `sensor_msgs`, `std_msgs`, Bash, C++17, PlatformIO Unity native tests, Arduino ESP32-C3, SCServo, micro-ROS UDP.

## Global Constraints

- Read `docs/superpowers/specs/2026-09-09-wireless-leader-design.md` before editing.
- Work in `/home/linao/so101_lerobot`; preserve every existing user change and unrelated untracked file.
- Never read, print, stage, or commit `firmware/xiao_soarm/src/wifi_config.h`, any future leader `wifi_config.h`, WiFi passwords, tokens, or other credentials.
- Do not modify `cali/my_leader.json`, `cali/my_follower.json`, the PC bridge's 30 Hz default command rate, follower `Goal_Speed=0`, acceleration `254`, 50 Hz follower control tick, 12.0 rad/s follower limits, ROS follower QoS, or the existing follower safety state machine.
- Keep `start_soarm_demo.sh` wired-by-default during Tasks 1–14. Change the no-argument default to wireless only in Task 15 after all hardware gates pass.
- Every software task follows red-green-refactor: add the named test, run it and confirm the intended failure, implement the minimum behavior, rerun the focused test and relevant regression suite, then commit only that task.
- Do not upload either firmware until Task 11 completes with all PC tests, both native suites, and both ESP32-C3 builds passing on the final source tree.
- Before any upload, obtain the exact physical confirmation written in Task 12. Never guess between multiple `303A:1001` XIAOs; identify the target by its observed USB serial/MAC and disconnect the other XIAO if ambiguous.
- During first upload and USB debug, servo 5 V stays disconnected. Do not connect USB 5 V and external 5 V simultaneously unless the board is confirmed to provide power isolation/OR-ing.
- Do not claim a hardware gate passed without operator observation and a saved evidence file. Any jump, wrong direction, torque-on state, sustained oscillation, bus fault, abnormal sound, abnormal temperature, invalid voltage, calibration mismatch, or unexpected write is an immediate stop condition.
- At every stop condition, stop further edits/actions and report the full command/output, `git status --short`, and `git log -1 --oneline`.

---

### Task 1: Define the wireless-leader Python protocol and calibration contract

**Files:**
- Create: `tools/soarm_wireless/leader_protocol.py`
- Create: `tests/tools/test_wireless_leader_protocol.py`

**Interfaces:**
- Consumes: `tools.soarm_wireless.control.JOINT_NAMES`, JSON calibration schema used by `cali/my_leader.json`.
- Produces: `LeaderStateCode`, `LeaderRawState.from_array(values)`, `LeaderStatus.from_array(values)`, `load_leader_calibration(path)`, `leader_calibration_crc32(calibration)`, and `normalize_leader_raw(raw_positions, calibration)`.
- Protocol constants: version `1`, raw-state length `11`, status length `13`, expected model `777`, CRC-32/ISO-HDLC over `struct.pack("<BHhHH", id, 777, homing_offset, range_min, range_max)` for IDs 1–6.

- [ ] **Step 1: Write the failing protocol tests**

Create `tests/tools/test_wireless_leader_protocol.py` with tests equivalent to this complete behavioral contract:

```python
from pathlib import Path

import pytest

from tools.soarm_wireless.leader_protocol import (
    LeaderRawState,
    LeaderStateCode,
    LeaderStatus,
    leader_calibration_crc32,
    load_leader_calibration,
    normalize_leader_raw,
)


CALIBRATION = {
    "shoulder_pan": {"id": 1, "drive_mode": 0, "homing_offset": 1084, "range_min": 694, "range_max": 3349},
    "shoulder_lift": {"id": 2, "drive_mode": 0, "homing_offset": -1065, "range_min": 804, "range_max": 3220},
    "elbow_flex": {"id": 3, "drive_mode": 0, "homing_offset": 16, "range_min": 795, "range_max": 3080},
    "wrist_flex": {"id": 4, "drive_mode": 0, "homing_offset": 133, "range_min": 679, "range_max": 3084},
    "wrist_roll": {"id": 5, "drive_mode": 0, "homing_offset": 1925, "range_min": 0, "range_max": 4095},
    "gripper": {"id": 6, "drive_mode": 0, "homing_offset": -1891, "range_min": 1447, "range_max": 2808},
}


def test_current_leader_calibration_has_stable_crc():
    assert leader_calibration_crc32(CALIBRATION) == 0x9D36C031


def test_raw_state_decodes_signed_positions_and_unsigned_ids():
    state = LeaderRawState.from_array([1, -1, -2, 1234, 63, -20, 100, 200, 300, 4095, 5000])
    assert state.boot_session_id == 0xFFFFFFFF
    assert state.sequence == 0xFFFFFFFE
    assert state.response_mask == 0x3F
    assert state.raw_positions == (-20, 100, 200, 300, 4095, 5000)


def test_status_requires_exact_shape_and_known_state():
    status = LeaderStatus.from_array([1, 2, 7, 9, 63, 63, 63, -1, 100, 0, 0, 2000, -42])
    assert status.state is LeaderStateCode.READY
    assert status.calibration_crc32 == 0xFFFFFFFF
    with pytest.raises(ValueError, match="13"):
        LeaderStatus.from_array([1] * 12)


def test_normalization_matches_lerobot_ranges():
    raw = [694, 2012, 3080, 679, 2047, 2808]
    action = normalize_leader_raw(raw, CALIBRATION)
    assert action["shoulder_pan.pos"] == pytest.approx(-100.0)
    assert action["shoulder_lift.pos"] == pytest.approx(0.0, abs=0.1)
    assert action["elbow_flex.pos"] == pytest.approx(100.0)
    assert action["wrist_flex.pos"] == pytest.approx(-100.0)
    assert action["wrist_roll.pos"] == pytest.approx(-0.02442, abs=0.01)
    assert action["gripper.pos"] == pytest.approx(100.0)


def test_loader_rejects_wrong_ids(tmp_path: Path):
    path = tmp_path / "leader.json"
    path.write_text('{"shoulder_pan":{"id":6}}')
    with pytest.raises(ValueError, match="joints|ID"):
        load_leader_calibration(path)
```

- [ ] **Step 2: Confirm the intended red failure**

Run:

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_leader_protocol.py -q
```

Expected: collection fails with `ModuleNotFoundError: tools.soarm_wireless.leader_protocol`. If another test or dependency fails first, stop.

- [ ] **Step 3: Implement the protocol module**

Implement these exact public definitions in `tools/soarm_wireless/leader_protocol.py`:

```python
LEADER_PROTOCOL_VERSION = 1
LEADER_RAW_FIELD_COUNT = 11
LEADER_STATUS_FIELD_COUNT = 13
EXPECTED_MODEL_NUMBER = 777

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

```

Implement `LeaderRawState.from_array(cls, values: Sequence[int]) -> LeaderRawState` and `LeaderStatus.from_array(cls, values: Sequence[int]) -> LeaderStatus` on those dataclasses. Use `value & 0xFFFFFFFF` for session, sequence, counters, uptime, and CRC fields. Validate exact message length, protocol version, known state, masks in `0..0x3f`, six calibration keys in `JOINT_NAMES` order, IDs 1–6, finite ranges, and `range_min < range_max`. Normalize the first five joints to `[-100, 100]`, gripper to `[0, 100]`, and apply `drive_mode` exactly as `SerialMotorsBus._normalize` does. Do not import or instantiate a serial bus.

- [ ] **Step 4: Run focused and existing protocol tests**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_leader_protocol.py \
  tests/tools/test_soarm_wireless_protocol.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add tools/soarm_wireless/leader_protocol.py tests/tools/test_wireless_leader_protocol.py
git diff --cached --check
git commit -m "feat: define wireless leader protocol"
```

---

### Task 2: Gate wireless leader samples and detect outages

**Files:**
- Create: `tools/soarm_wireless/leader_source.py`
- Create: `tests/tools/test_wireless_leader_source.py`

**Interfaces:**
- Consumes: Task 1 `LeaderRawState`, `LeaderStatus`, `normalize_leader_raw`, `leader_calibration_crc32`; existing `is_newer_sequence` from `tools.soarm_wireless.protocol`.
- Produces: `LeaderUnavailable`, `LeaderSample`, and `WirelessLeaderTracker` with `on_status(status, received_at)`, `on_raw_state(state, received_at)`, `get_action(now)`, `sample_age(now)`, and `reset()`.

- [ ] **Step 1: Write failing health-gate tests**

Cover these cases in `tests/tools/test_wireless_leader_source.py`:

```python
def test_tracker_accepts_only_ready_matching_status(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration, stale_timeout_s=0.150)
    tracker.on_status(ready_status, received_at=1.0)
    assert tracker.on_raw_state(raw_state, received_at=1.01)
    assert tracker.get_action(now=1.10)["shoulder_pan.pos"] == pytest.approx(-100.0)


def test_tracker_rejects_crc_mismatch(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(replace(ready_status, calibration_crc32=0), 1.0)
    assert not tracker.on_raw_state(raw_state, 1.01)
    with pytest.raises(LeaderUnavailable, match="calibration"):
        tracker.get_action(1.02)


def test_tracker_rejects_duplicate_and_old_sequence(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(ready_status, 1.0)
    assert tracker.on_raw_state(raw_state, 1.01)
    assert not tracker.on_raw_state(replace(raw_state, sequence=raw_state.sequence), 1.02)
    assert not tracker.on_raw_state(replace(raw_state, sequence=raw_state.sequence - 1), 1.03)


def test_tracker_becomes_unavailable_after_150_ms(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration, stale_timeout_s=0.150)
    tracker.on_status(ready_status, 1.0)
    tracker.on_raw_state(raw_state, 1.01)
    with pytest.raises(LeaderUnavailable, match="stale"):
        tracker.get_action(1.161)


def test_new_boot_session_resets_sequence_gate(calibration, ready_status, raw_state):
    tracker = WirelessLeaderTracker(calibration)
    tracker.on_status(ready_status, 1.0)
    tracker.on_raw_state(raw_state, 1.01)
    new_status = replace(ready_status, boot_session_id=99, last_sequence=0)
    tracker.on_status(new_status, 2.0)
    assert tracker.on_raw_state(replace(raw_state, boot_session_id=99, sequence=1), 2.01)
```

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_leader_source.py -q
```

Expected: import failure for `leader_source`.

- [ ] **Step 3: Implement the pure tracker**

Use these exact data boundaries:

```python
class LeaderUnavailable(RuntimeError):
    pass

@dataclass(frozen=True)
class LeaderSample:
    boot_session_id: int
    sequence: int
    received_at: float
    action: dict[str, float]

```

Implement `WirelessLeaderTracker.__init__(calibration, stale_timeout_s=0.150)`, `on_status(status, received_at)`, `on_raw_state(state, received_at)`, `get_action(now)`, `sample_age(now)`, and `reset()`. `on_raw_state` returns `True` only for a new sample whose status is `READY`, session matches, all three masks are `0x3f`, CRC matches, and sequence is newer. Rejected samples must not refresh `received_at`. Store a machine-readable `last_error` string for launcher/CSV diagnostics.

- [ ] **Step 4: Verify tracker and protocol suites**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_leader_source.py \
  tests/tools/test_wireless_leader_protocol.py -q
```

Expected: pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add tools/soarm_wireless/leader_source.py tests/tools/test_wireless_leader_source.py
git diff --cached --check
git commit -m "feat: validate wireless leader samples"
```

---

### Task 3: Implement the computer-side agent discovery service

**Files:**
- Create: `tools/soarm_agent_discovery.py`
- Create: `tests/tools/test_soarm_agent_discovery.py`

**Interfaces:**
- Produces: `DISCOVERY_PORT=8889`, `PROBE=b"SOARM_DISCOVER 1\n"`, `encode_announcement(nonce, agent_port)`, `decode_announcement(payload)`, and CLI options `--bind-ip`, `--broadcast-ip`, `--agent-port`, `--interval`.
- Packet: ASCII `SOARM_AGENT 1 <8 lowercase hex nonce> <decimal port>\n`.
- With no `--bind-ip` or `--broadcast-ip`, the service selects the active WiFi interface's IPv4 address and derives its broadcast address from the actual prefix; explicit options override auto-detection.

- [ ] **Step 1: Write failing packet/service tests**

```python
def test_announcement_round_trip():
    payload = encode_announcement(0x1234ABCD, 8888)
    assert payload == b"SOARM_AGENT 1 1234abcd 8888\n"
    assert decode_announcement(payload) == (0x1234ABCD, 8888)


@pytest.mark.parametrize("payload", [b"", b"SOARM_AGENT 2 1234abcd 8888\n", b"SOARM_AGENT 1 nope 8888\n", b"SOARM_AGENT 1 1234abcd 0\n"])
def test_invalid_announcement_is_rejected(payload):
    with pytest.raises(ValueError):
        decode_announcement(payload)


def test_probe_receives_unicast_announcement(monkeypatch):
    sock = FakeSocket(incoming=[(PROBE, ("10.0.0.51", 45000))])
    serve_once(sock, nonce=0x1234ABCD, agent_port=8888, broadcast_target=("10.0.0.255", 8889))
    assert (b"SOARM_AGENT 1 1234abcd 8888\n", ("10.0.0.51", 45000)) in sock.sent
```

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_agent_discovery.py -q
```

Expected: import failure for `tools.soarm_agent_discovery`.

- [ ] **Step 3: Implement the service**

The service must bind UDP `bind_ip:8889`, set `SO_BROADCAST`, broadcast an announcement every `interval` seconds, reply to exact `PROBE` packets with a unicast announcement, reject malformed packets silently, handle `SIGINT`/`SIGTERM`, and never log packet payloads or credentials. `nonce` is generated once with `secrets.randbits(32)` and printed only as hexadecimal diagnostics.

Expose a testable function:

```python
def serve_once(sock, nonce: int, agent_port: int, broadcast_target: tuple[str, int]) -> None:
    """Send one broadcast and reply to at most one waiting valid probe."""
```

- [ ] **Step 4: Verify tests and CLI help**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_agent_discovery.py -q
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/soarm_agent_discovery.py --help
```

Expected: tests pass; help lists all four options.

- [ ] **Step 5: Commit Task 3**

```bash
git add tools/soarm_agent_discovery.py tests/tools/test_soarm_agent_discovery.py
git diff --cached --check
git commit -m "feat: advertise the micro-ROS agent"
```

---

### Task 4: Add the shared C++ discovery parser

**Files:**
- Create: `firmware/soarm_common/agent_discovery_protocol.h`
- Create: `firmware/xiao_soarm/test/test_agent_discovery/test_main.cpp`
- Modify: `firmware/xiao_soarm/platformio.ini`

**Interfaces:**
- Produces header-only `agent_discovery::parse_announcement(const char*, size_t, Announcement&)` and `agent_discovery::kProbe`.
- Must parse exactly the Task 3 ASCII packet and reject extra fields, wrong versions, non-hex nonce, and ports outside `1..65535`.

- [ ] **Step 1: Add the failing native test**

```cpp
#include <unity.h>
#include "agent_discovery_protocol.h"

void test_valid_announcement() {
    agent_discovery::Announcement result{};
    const char payload[] = "SOARM_AGENT 1 1234abcd 8888\n";
    TEST_ASSERT_TRUE(agent_discovery::parse_announcement(payload, sizeof(payload) - 1, result));
    TEST_ASSERT_EQUAL_HEX32(0x1234abcd, result.nonce);
    TEST_ASSERT_EQUAL_UINT16(8888, result.agent_port);
}

void test_invalid_announcements() {
    agent_discovery::Announcement result{};
    const char wrong_version[] = "SOARM_AGENT 2 1234abcd 8888\n";
    const char bad_nonce[] = "SOARM_AGENT 1 zzzzabcd 8888\n";
    const char bad_port[] = "SOARM_AGENT 1 1234abcd 0\n";
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(wrong_version, sizeof(wrong_version) - 1, result));
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(bad_nonce, sizeof(bad_nonce) - 1, result));
    TEST_ASSERT_FALSE(agent_discovery::parse_announcement(bad_port, sizeof(bad_port) - 1, result));
}
```

Add `-I../soarm_common` to the native environment build flags.

- [ ] **Step 2: Confirm red**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: compilation fails because `agent_discovery_protocol.h` does not exist.

- [ ] **Step 3: Implement the header-only parser**

Define:

```cpp
namespace agent_discovery {
constexpr uint16_t kDiscoveryPort = 8889;
constexpr char kProbe[] = "SOARM_DISCOVER 1\n";
struct Announcement { uint32_t nonce; uint16_t agent_port; };
bool parse_announcement(const char* data, size_t size, Announcement& output);
}
```

Use bounded local buffers and manual numeric parsing; do not allocate `String`, call `sscanf`, or accept trailing bytes after the newline.

- [ ] **Step 4: Run all follower native tests**

```bash
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: existing seven controller tests plus discovery tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add firmware/soarm_common/agent_discovery_protocol.h \
  firmware/xiao_soarm/test/test_agent_discovery/test_main.cpp \
  firmware/xiao_soarm/platformio.ini
git diff --cached --check
git commit -m "feat: share agent discovery protocol"
```

---

### Task 5: Implement the leader firmware state machine and CRC

**Files:**
- Create: `firmware/xiao_soarm_leader/platformio.ini`
- Create: `firmware/xiao_soarm_leader/src/leader_logic.h`
- Create: `firmware/xiao_soarm_leader/src/leader_logic.cpp`
- Create: `firmware/xiao_soarm_leader/test/test_leader_logic/test_main.cpp`

**Interfaces:**
- Produces: `leader_logic::Controller`, `leader_logic::BusSnapshot`, `leader_logic::Output`, and `leader_logic::calibration_crc32(records, count)`.
- Constants: three consecutive bad reads fault; ten consecutive complete reads recover; valid mask `0x3f`.

- [ ] **Step 1: Create a native-only PlatformIO environment and failing tests**

Configure `[env:native]` with `platform=native`, `test_framework=unity`, `test_build_src=yes`, `build_src_filter=+<leader_logic.cpp>`, and `-std=gnu++17`.

Tests must demonstrate:

```cpp
using namespace leader_logic;

static Controller ready_controller(uint32_t initial_sequence = 0) {
    Controller c(initial_sequence);
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    c.report_agent_connected(true);
    for (int i = 0; i < 10; ++i) c.report_read(0x3f);
    return c;
}

void test_ready_requires_bus_agent_and_ten_good_reads() {
    Controller c;
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    TEST_ASSERT_EQUAL(WAITING_AGENT, c.state());
    c.report_agent_connected(true);
    for (int i = 0; i < 9; ++i) TEST_ASSERT_FALSE(c.report_read(0x3f).publish_sample);
    const Output ready = c.report_read(0x3f);
    TEST_ASSERT_EQUAL(READY, ready.state);
    TEST_ASSERT_TRUE(ready.publish_sample);
    TEST_ASSERT_EQUAL_UINT32(1, ready.sequence);
}

void test_three_bad_reads_fault_and_ten_good_reads_recover() {
    Controller c = ready_controller();
    TEST_ASSERT_EQUAL(READY, c.report_read(0x00).state);
    TEST_ASSERT_EQUAL(READY, c.report_read(0x00).state);
    TEST_ASSERT_EQUAL(BUS_FAULT, c.report_read(0x00).state);
    c.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x3f}, 0x9d36c031);
    for (int i = 0; i < 9; ++i) {
        TEST_ASSERT_EQUAL(BUS_FAULT, c.report_read(0x3f).state);
    }
    TEST_ASSERT_EQUAL(READY, c.report_read(0x3f).state);
}

void test_missing_model_or_torque_mask_never_readies() {
    Controller missing_model;
    missing_model.report_agent_connected(true);
    missing_model.report_bus_check(BusSnapshot{0x3f, 0x1f, 0x3f}, 1);
    TEST_ASSERT_EQUAL(BUS_FAULT, missing_model.state());

    Controller torque_on;
    torque_on.report_agent_connected(true);
    torque_on.report_bus_check(BusSnapshot{0x3f, 0x3f, 0x1f}, 1);
    TEST_ASSERT_EQUAL(BUS_FAULT, torque_on.state());
}

void test_sequence_wraps_from_uint32_max_to_zero() {
    Controller c = ready_controller(UINT32_MAX - 2);
    TEST_ASSERT_EQUAL_UINT32(UINT32_MAX, c.report_read(0x3f).sequence);
    TEST_ASSERT_EQUAL_UINT32(0, c.report_read(0x3f).sequence);
}

void test_crc_matches_python_vector() {
    const CalibrationRecord records[6] = {
        {1, 777, 1084, 694, 3349}, {2, 777, -1065, 804, 3220},
        {3, 777, 16, 795, 3080}, {4, 777, 133, 679, 3084},
        {5, 777, 1925, 0, 4095}, {6, 777, -1891, 1447, 2808},
    };
    TEST_ASSERT_EQUAL_HEX32(0x9d36c031, calibration_crc32(records, 6));
}
```

- [ ] **Step 2: Confirm red**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: compile failure because `leader_logic` APIs are absent.

- [ ] **Step 3: Implement the pure state machine**

Use these public declarations:

```cpp
enum State : int32_t { STARTING = 0, WAITING_AGENT = 1, READY = 2, BUS_FAULT = 3 };
struct BusSnapshot { uint8_t response_mask; uint8_t model_mask; uint8_t torque_off_mask; };
struct Output { State state; bool publish_sample; uint32_t sequence; };
struct CalibrationRecord {
    uint8_t id;
    uint16_t model;
    int16_t homing_offset;
    uint16_t range_min;
    uint16_t range_max;
};

class Controller {
public:
    explicit Controller(uint32_t initial_sequence = 0);
    void report_bus_check(const BusSnapshot& snapshot, uint32_t calibration_crc);
    void report_agent_connected(bool connected);
    Output report_read(uint8_t response_mask);
    State state() const;
    uint32_t calibration_crc() const;
};

uint32_t calibration_crc32(const CalibrationRecord* records, size_t count);
```

Keep this module free of Arduino, WiFi, ROS, and SCServo dependencies.

- [ ] **Step 4: Run leader native tests**

```bash
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: all leader logic and CRC tests pass.

- [ ] **Step 5: Commit Task 5**

```bash
git add firmware/xiao_soarm_leader/platformio.ini \
  firmware/xiao_soarm_leader/src/leader_logic.h \
  firmware/xiao_soarm_leader/src/leader_logic.cpp \
  firmware/xiao_soarm_leader/test/test_leader_logic/test_main.cpp
git diff --cached --check
git commit -m "feat: add wireless leader state machine"
```

---

### Task 6: Build the dedicated leader ESP32-C3 firmware

**Files:**
- Create: `firmware/xiao_soarm_leader/.gitignore`
- Create: `firmware/xiao_soarm_leader/src/wifi_config.example.h`
- Create: `firmware/xiao_soarm_leader/src/servo_bus.h`
- Create: `firmware/xiao_soarm_leader/src/servo_bus.cpp`
- Create: `firmware/xiao_soarm_leader/src/agent_discovery.h`
- Create: `firmware/xiao_soarm_leader/src/agent_discovery.cpp`
- Create: `firmware/xiao_soarm_leader/src/main.cpp`
- Create: `firmware/xiao_soarm_leader/src/uxr_time_override.cpp`
- Create: `firmware/xiao_soarm_leader/README.md`
- Modify: `firmware/xiao_soarm_leader/platformio.ini`
- Create: `tests/tools/test_wireless_leader_firmware_contract.py`

**Interfaces:**
- Publishes `/leader/raw_state` and `/leader/status` as fixed-length `Int32MultiArray` with best-effort/depth-1 QoS.
- Uses Task 4 discovery packet and Task 5 state machine.
- `servo_bus` API: `begin()`, `scan_and_disable_torque()`, `read_all(int32_t[6])`, `read_status()`, `calibration_crc32()`, and `stats()`.

- [ ] **Step 1: Write the failing source-contract test**

Create the following contract in `tests/tools/test_wireless_leader_firmware_contract.py`:

```python
from pathlib import Path


ROOT = Path(__file__).parents[2]
LEADER_SRC = ROOT / "firmware/xiao_soarm_leader/src"


def source_text() -> str:
    return "\n".join(path.read_text() for path in sorted(LEADER_SRC.glob("*.cpp")))


def test_leader_firmware_is_read_only_and_publishes_contract_topics():
    text = source_text()
    for required in (
        '"/leader/raw_state"',
        '"/leader/status"',
        "RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT",
        "LEADER_RAW_FIELD_COUNT = 11",
        "LEADER_STATUS_FIELD_COUNT = 13",
        "READ_PERIOD_MS = 20",
        "Torque_Enable",
        "read_torque_enable",
    ):
        assert required in text
    for forbidden in (
        "Goal_Position",
        "SMS_STS_GOAL_POSITION_L",
        "SyncWritePosEx",
        "write_positions",
        "rclc_subscription_init",
    ):
        assert forbidden not in text
```

- [ ] **Step 2: Confirm red**

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_leader_firmware_contract.py -q
```

Expected: failure because leader firmware files do not yet exist.

- [ ] **Step 3: Implement the leader servo bus**

Use IDs `{1,2,3,4,5,6}`, baud `1000000`, `Serial0.begin(1000000, SERIAL_8N1, D7, D6)`, and a 4 ms SCServo timeout. `scan_and_disable_torque()` must read model 777, write `Torque_Enable=0`, read it back through a helper named `read_torque_enable`, and return all three masks. `read_all` accepts signed positions, updates a response mask, and returns true only for `0x3f`. Define `LEADER_RAW_FIELD_COUNT = 11`, `LEADER_STATUS_FIELD_COUNT = 13`, and `READ_PERIOD_MS = 20` in `main.cpp`. No function may write a position, speed, acceleration, homing offset, or limit.

- [ ] **Step 4: Implement runtime discovery**

Bind UDP port 8889, accept broadcast announcements using Task 4, and after 3 seconds without discovery send `SOARM_DISCOVER 1\n` as rate-limited unicast probes across the DHCP `/24`. Use the UDP packet source as agent IP. For a non-`/24` network, continue broadcast listening and report `DISCOVERY_UNSUPPORTED_SUBNET` without scanning.

- [ ] **Step 5: Implement the micro-ROS main loop**

Create node `so101_leader`, publishers `/leader/raw_state` and `/leader/status`, and no subscribers. Generate a random 32-bit boot session ID. At 20 ms intervals read all positions and, only when Task 5 returns `publish_sample=true`, publish exactly 11 fields. At 100 ms intervals publish exactly 13 status fields. Use separate fixed arrays with static capacities; no heap allocation in the loop.

- [ ] **Step 6: Configure ESP32-C3 build without copying credentials**

Add the `seeed_xiao_esp32c3` environment using the same Arduino, SCServo, and local micro-ROS library versions as `firmware/xiao_soarm/platformio.ini`, with publisher capacity 2 and subscriber capacity 0. Point include/library paths at the existing local `firmware/xiao_soarm/lib/microros` build. Ignore `src/wifi_config.h`; provide only an example containing literal empty values `#define WIFI_SSID ""` and `#define WIFI_PASS ""`, with no real credentials.

Before the first ESP32 build, check only whether the ignored file exists:

```bash
test -f /home/linao/so101_lerobot/firmware/xiao_soarm_leader/src/wifi_config.h
```

If it does not exist, stop and ask the operator to create it locally from the example and enter the hotspot credentials themselves. Do not open, print, diff, hash, or stage that file.

- [ ] **Step 7: Run native, contract, and ESP32 build gates**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_leader_firmware_contract.py -q
```

Expected: all pass; do not upload.

- [ ] **Step 8: Commit Task 6**

Stage only the listed leader firmware/example/test files. Verify `git diff --cached --name-only` does not include either real `wifi_config.h`, then commit:

```bash
git add firmware/xiao_soarm_leader/.gitignore \
  firmware/xiao_soarm_leader/platformio.ini \
  firmware/xiao_soarm_leader/src/wifi_config.example.h \
  firmware/xiao_soarm_leader/src/servo_bus.h \
  firmware/xiao_soarm_leader/src/servo_bus.cpp \
  firmware/xiao_soarm_leader/src/agent_discovery.h \
  firmware/xiao_soarm_leader/src/agent_discovery.cpp \
  firmware/xiao_soarm_leader/src/main.cpp \
  firmware/xiao_soarm_leader/src/uxr_time_override.cpp \
  firmware/xiao_soarm_leader/README.md \
  tests/tools/test_wireless_leader_firmware_contract.py
git diff --cached --check
git diff --cached --name-only
git commit -m "feat: add wireless leader firmware"
```

---

### Task 7: Replace the follower's fixed agent IP with discovery

**Files:**
- Modify: `firmware/xiao_soarm/src/main.cpp`
- Create: `firmware/xiao_soarm/src/agent_discovery.h`
- Create: `firmware/xiao_soarm/src/agent_discovery.cpp`
- Modify: `firmware/xiao_soarm/src/wifi_config.example.h`
- Modify: `tests/tools/test_firmware_status_contract.py`

**Interfaces:**
- Consumes: Task 4 discovery parser.
- Preserves: follower topics, 14-field status, command protocol, QoS, 50 Hz control, 20 Hz feedback, 12.0 rad/s limit, 500 ms timeout, servo configuration, and calibration constants.

- [ ] **Step 1: Add the failing follower discovery contract**

Add assertions that `main.cpp` obtains an agent address from `agent_discovery::discover()`, passes that address to `set_microros_wifi_transports`, and does not reference `AGENT_IP`. Assert follower topic names and existing status field count remain unchanged.

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_firmware_status_contract.py -q
```

Expected: new discovery assertions fail while existing contracts pass.

- [ ] **Step 3: Implement follower discovery integration**

Reuse the Task 6 discovery behavior and Task 4 parser. Replace only fixed agent-address selection. Keep local WiFi credentials untouched and allow the old unused `AGENT_IP` define to remain in an ignored local header without reading it. On agent-loss restart, rediscover instead of reusing a fixed address.

- [ ] **Step 4: Run follower tests and compile without upload**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_firmware_status_contract.py -q
```

Expected: pass; do not upload.

- [ ] **Step 5: Commit Task 7**

```bash
git add firmware/xiao_soarm/src/main.cpp firmware/xiao_soarm/src/agent_discovery.h \
  firmware/xiao_soarm/src/agent_discovery.cpp firmware/xiao_soarm/src/wifi_config.example.h \
  tests/tools/test_firmware_status_contract.py
git diff --cached --check
git diff --cached --name-only
git commit -m "feat: discover follower micro-ROS agent"
```

---

### Task 8: Integrate wireless leader input into the teleoperation bridge

**Files:**
- Modify: `tools/soarm_wireless/leader_source.py`
- Modify: `tools/wireless_teleoperate.py`
- Modify: `tests/tools/test_wireless_leader_source.py`
- Modify: `tests/tools/test_wireless_teleoperate.py`

**Interfaces:**
- Produces `WiredLeaderSource` and `WirelessLeaderSource(node, calibration_path, stale_timeout_s)` with `connect()`, `get_action(now)`, `is_connected`, and `disconnect()`.
- Adds CLI: `--leader-mode {wired,wireless}`, `--leader-stale-timeout 0.15`, `--leader-recovery-blend-duration 1.0`; development default remains `wired` until Task 15.

- [ ] **Step 1: Write failing adapter and recovery tests**

Add tests proving wired mode still instantiates `SO101Leader`, wireless mode does not touch a serial port, wireless callbacks parse both topics, the default forwarding rate remains 30 Hz, stale leader input causes no call to `publish_command`, and a recovered boot session resets the follower control session and calls `startup_blend` with `duration=1.0` from current follower feedback toward the preserved relative target. Use explicit mocks and assert the complete call arguments rather than testing log text.

Use fake publishers/clocks and injected source objects; tests must not require hardware or a live ROS graph.

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_leader_source.py tests/tools/test_wireless_teleoperate.py -q
```

Expected: failures for missing adapter/CLI/recovery behavior.

- [ ] **Step 3: Implement the common source interface**

`WiredLeaderSource` delegates to current `SO101Leader` and retains EEPROM calibration matching. `WirelessLeaderSource` creates best-effort/depth-1 subscriptions for `/leader/raw_state` and `/leader/status`, feeds `WirelessLeaderTracker`, and raises `LeaderUnavailable` rather than returning stale actions.

- [ ] **Step 4: Refactor the run loop**

Keep follower mapping and command functions unchanged. Replace direct `leader.get_action()` calls with the source interface. On `LeaderUnavailable`, stop publishing immediately. On healthy return/new boot session, read current follower pose, reset the follower command session, perform a near-current handshake, compute the target from the original relative origins, and blend for `args.leader_recovery_blend_duration` while continuing to abort on another leader outage.

- [ ] **Step 5: Verify focused and existing control tests**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_leader_source.py \
  tests/tools/test_wireless_teleoperate.py \
  tests/tools/test_soarm_wireless_control.py \
  tests/tools/test_soarm_wireless_protocol.py -q
```

Expected: pass.

- [ ] **Step 6: Commit Task 8**

```bash
git add tools/soarm_wireless/leader_source.py tools/wireless_teleoperate.py \
  tests/tools/test_wireless_leader_source.py tests/tools/test_wireless_teleoperate.py
git diff --cached --check
git commit -m "feat: accept wireless leader input"
```

---

### Task 9: Extend CSV metrics and analysis for the wireless leader

**Files:**
- Modify: `tools/soarm_wireless/metrics.py`
- Modify: `tools/wireless_teleoperate.py`
- Modify: `tools/analyze_wireless_log.py`
- Modify: `tests/tools/test_soarm_wireless_metrics.py`

**Interfaces:**
- Adds `leader_boot_session_id`, `leader_sample_sequence`, `leader_sample_gap_ms`, `leader_sample_age_ms`, `leader_response_mask`, `leader_model_mask`, `leader_torque_off_mask`, `leader_calibration_crc32`, `leader_read_errors`, `leader_torque_errors`, `leader_rssi_dbm`, `leader_recovery_count`, and `control_chain_ack_latency_ms`.
- Analyzer produces `leader_sample_rate_hz`, `leader_max_sample_gap_ms`, `leader_recovery_count`, and control-chain p50/p95/p99.

- [ ] **Step 1: Write failing metrics tests**

Assert the CSV header contains all leader fields and that a three-row fixture computes:

```python
assert summary["leader_sample_rate_hz"] == pytest.approx(50.0)
assert summary["leader_max_sample_gap_ms"] == pytest.approx(20.0)
assert summary["leader_recovery_count"] == 1
assert summary["control_chain_ack_latency_p95_ms"] == 82.0
```

Also assert existing follower metrics remain present.

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_wireless_metrics.py -q
```

Expected: missing-key/header failures.

- [ ] **Step 3: Implement metrics**

Store the accepted leader sample receive time with each command sequence. When follower status acknowledges that command, compute `control_chain_ack_latency_ms` from leader sample acceptance to follower applied acknowledgement. Do not subtract XIAO uptime from PC monotonic time. Extend `summarize_rows` with nearest-rank percentiles and sample-gap/rate calculations.

- [ ] **Step 4: Verify metrics and bridge tests**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_soarm_wireless_metrics.py tests/tools/test_wireless_teleoperate.py -q
```

Expected: pass.

- [ ] **Step 5: Commit Task 9**

```bash
git add tools/soarm_wireless/metrics.py tools/wireless_teleoperate.py \
  tools/analyze_wireless_log.py tests/tools/test_soarm_wireless_metrics.py
git diff --cached --check
git commit -m "feat: measure wireless leader health"
```

---

### Task 10: Add launcher modes and a leader-only validator

**Files:**
- Modify: `start_soarm_demo.sh`
- Create: `tools/validate_wireless_leader.py`
- Modify: `tests/tools/test_wireless_launcher.py`
- Create: `tests/tools/test_validate_wireless_leader.py`

**Interfaces:**
- Launcher supports `--leader wired|wireless` and `--check`; Task 10 default remains wired.
- Validator supports required `--device-id` plus `--calibration`, `--duration`, and `--evidence-path`; it never publishes `/joint_command`.

- [ ] **Step 1: Write failing launcher tests**

Assert explicit parsing of both options, wired USB checks only in wired mode, wireless preflight waits for `/leader/raw_state` and `/leader/status`, fixed `EXPECTED_AGENT_IP` checks are absent, discovery service receives computed bind/broadcast IPs, and cleanup only kills processes started by this invocation.

- [ ] **Step 2: Write failing validator tests**

Use fake leader messages and assert the validator records protocol version, USB/MAC identity supplied by CLI, boot session, all masks, CRC, sample frequency, RSSI, read/torque error deltas, raw min/max per joint, and normalized min/max per joint. Assert source contains no publisher for `/joint_command`.

- [ ] **Step 3: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_launcher.py tests/tools/test_validate_wireless_leader.py -q
```

Expected: failures for unsupported launcher arguments and missing validator.

- [ ] **Step 4: Implement launcher modes**

Parse options without `eval`. Compute `CURRENT_IP` and broadcast address from the selected WiFi interface. Start the agent and `tools/soarm_agent_discovery.py`. In wireless mode wait for both leader topics and verify the status through a short Python preflight; in wired mode preserve the current stable by-id path and calibration behavior. Pass the selected leader mode and 1-second recovery duration to the bridge.

- [ ] **Step 5: Implement the read-only validator**

The validator subscribes only to leader topics, uses Tasks 1–2, collects for the requested duration, writes JSON atomically via a temporary sibling file, and exits nonzero unless state is READY, masks are `0x3f`, CRC matches, mean rate is 45–55 Hz, and error counters do not increase. It prompts for `OBSERVED` unless `--yes` is explicitly supplied.

- [ ] **Step 6: Verify launcher, validator, and check-mode tests**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_wireless_launcher.py tests/tools/test_validate_wireless_leader.py -q
bash -n start_soarm_demo.sh
```

Expected: pass.

- [ ] **Step 7: Commit Task 10**

```bash
git add start_soarm_demo.sh tools/validate_wireless_leader.py \
  tests/tools/test_wireless_launcher.py tests/tools/test_validate_wireless_leader.py
git diff --cached --check
git commit -m "feat: launch wired or wireless leader"
```

---

### Task 11: Run the complete software gate before any upload

**Files:**
- Modify only if a gate exposes a defect: files owned by Tasks 1–10, with a new failing regression test first.
- Create after success: `logs/wireless-leader/software-gate-2026-09-09.txt`

- [ ] **Step 1: Run all relevant PC tests**

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools -q
bash -n start_soarm_demo.sh
```

Expected: all relevant tests pass. If an unrelated repository baseline fails, save the exact failure and prove all wireless-leader/follower tests separately pass; do not silently ignore it.

- [ ] **Step 2: Run both native firmware suites**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
cd /home/linao/so101_lerobot/firmware/xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: both pass.

- [ ] **Step 3: Compile both ESP32-C3 firmwares without upload**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
cd /home/linao/so101_lerobot/firmware/xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
```

Expected: `SUCCESS` twice. Neither command may contain `upload`.

- [ ] **Step 4: Save and commit software-gate evidence**

Capture exact commands, counts, commit hashes, and outputs in `logs/wireless-leader/software-gate-2026-09-09.txt`. Check it for credentials, then force-add only that log and commit:

```bash
git add -f logs/wireless-leader/software-gate-2026-09-09.txt
git diff --cached --check
git commit -m "test: record wireless leader software gate"
```

Stop after this commit and request the Task 12 physical confirmation.

---

### Task 12: Upload the leader XIAO and capture USB-only evidence

**Files:**
- Create after observation: `logs/wireless-leader/leader-usb-smoke-2026-09-09.txt`

- [ ] **Step 1: Obtain exact physical confirmation**

Require the operator to state:

```text
主臂已机械支撑；运动空间已清空；主臂舵机 5V 已断开；仅连接主臂 XIAO USB；从臂 XIAO 已断开或已明确区分设备身份。
```

- [ ] **Step 2: Identify exactly one leader XIAO**

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio device list
ls -l /dev/serial/by-id/* /dev/ttyACM* 2>/dev/null
```

Expected: one unambiguous `303A:1001` target with recorded USB serial/MAC. Stop if ambiguous.

- [ ] **Step 3: Upload only the already-tested leader firmware**

Enter the port observed in Step 2 and reject anything that is not a character device before uploading:

```bash
read -r -p "主臂 XIAO 端口（例如 /dev/ttyACM1）: " LEADER_XIAO_PORT
test -c "$LEADER_XIAO_PORT"
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3 \
  --target upload --upload-port "$LEADER_XIAO_PORT"
```

Expected: `SUCCESS`. Keep servo 5 V disconnected.

- [ ] **Step 4: Run agent/discovery and capture serial smoke output**

In terminal A, start the agent:

```bash
source /opt/ros/humble/setup.bash
snap run micro-ros-agent udp4 --port 8888 -v4
```

In terminal B, start discovery with automatic active-WiFi address selection:

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/soarm_agent_discovery.py --agent-port 8888
```

In terminal C, capture exactly 25 seconds from the port stored in Step 3:

```bash
cd /home/linao/so101_lerobot
read -r -p "再次输入已确认的主臂 XIAO 端口: " LEADER_XIAO_PORT
test -c "$LEADER_XIAO_PORT"
timeout 25s /home/linao/.platformio/penv/bin/pio device monitor \
  -p "$LEADER_XIAO_PORT" -b 115200 | tee logs/wireless-leader/leader-usb-smoke-2026-09-09.txt
```

Expected: WiFi connects, agent is discovered, ROS entities are created, state remains `STARTING` or `BUS_FAULT` because servo mask is `0x00`, torque-off mask is `0x00`, and no position-write API appears. Stop both background terminals after capture.

- [ ] **Step 5: Commit only USB evidence**

Review the log for credentials, force-add it, and commit:

```bash
git add -f logs/wireless-leader/leader-usb-smoke-2026-09-09.txt
git diff --cached --check
git commit -m "test: record wireless leader USB smoke check"
```

Do not claim powered leader or motion validation. Stop and request Task 13 confirmation.

---

### Task 13: Validate the powered leader without moving the follower

**Files:**
- Create after observation: `logs/wireless-leader/leader-powered-2026-09-09.json`
- Create after observation: `logs/wireless-leader/leader-powered-2026-09-09.md`

- [ ] **Step 1: Obtain exact powered-test confirmation**

Require:

```text
主臂已机械支撑；运动空间已清空；可立即断开主臂舵机电源；主臂处于安全姿态；从臂舵机电源已断开；主臂 XIAO 未同时连接 USB 5V 和外部 5V，或供电隔离已确认。
```

- [ ] **Step 2: Power the leader and run the validator**

Start the micro-ROS agent and discovery service using the terminal A/B commands from Task 12 Step 4. Record the exact leader XIAO USB serial/MAC as a non-secret identifier, then run:

```bash
source /opt/ros/humble/setup.bash
cd /home/linao/so101_lerobot
read -r -p "主臂 XIAO USB serial/MAC: " LEADER_DEVICE_ID
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/validate_wireless_leader.py \
  --device-id "$LEADER_DEVICE_ID" \
  --calibration /home/linao/so101_lerobot/cali/my_leader.json \
  --duration 30 \
  --evidence-path /home/linao/so101_lerobot/logs/wireless-leader/leader-powered-2026-09-09.json
```

Expected machine evidence: `READY`, response/model/torque-off masks `63`, CRC `0x9d36c031`, 45–55 Hz, no increasing read or torque errors.

- [ ] **Step 3: Perform read-only physical motion**

With follower power still disconnected, manually move each leader joint one at a time through a small safe range. Confirm all six raw channels change, normalized directions match the existing wired leader, the leader remains freely movable, and no servo holds or drives a joint.

- [ ] **Step 4: Save and commit operator evidence**

Write only observed facts to the Markdown evidence: hardware identity, power arrangement, masks, CRC, rate, counters, six direction observations, torque-off/free-motion observation, voltage/temperature, and any abnormal sound/heat. Stage exactly the JSON and Markdown files and commit:

```bash
git add -f logs/wireless-leader/leader-powered-2026-09-09.json \
  logs/wireless-leader/leader-powered-2026-09-09.md
git diff --cached --check
git commit -m "test: validate powered wireless leader"
```

Stop and request Task 14 confirmation.

---

### Task 14: Validate two-arm motion, leader recovery, IP change, wired fallback, and endurance

**Files:**
- Create after observation: `logs/wireless-leader/two-arm-motion-2026-09-09.md`
- Create after observation: `logs/wireless-leader/leader-reset-recovery-2026-09-09.md`
- Create after observation: `logs/wireless-leader/agent-ip-change-2026-09-09.md`
- Create after observation: `logs/wireless-leader/wired-fallback-2026-09-09.md`
- Create after observation: `logs/wireless-leader/endurance-2026-09-09.md`
- Add after each run: the exact launcher CSV path printed for that run
- Modify after evidence: `docs/soarm_wireless_test_matrix.md`

- [ ] **Step 1: Obtain exact two-arm confirmation**

Require:

```text
主从臂均已机械支撑；运动空间已清空；可立即断开两臂舵机电源；两臂均处于安全姿态；主臂 XIAO 无 USB 数据线。
```

- [ ] **Step 2: Run wireless mode and staged joint motion**

```bash
cd /home/linao/so101_lerobot
./start_soarm_demo.sh --leader wireless
```

Record the exact CSV path. Move each joint slowly, then normally, one at a time; perform a short coordinated motion; press Ctrl+C and confirm hold. Stop immediately for any global stop condition.

- [ ] **Step 3: Analyze the exact CSV**

```bash
read -r -p "粘贴 Step 2 打印的指标 CSV 绝对路径: " TWO_ARM_CSV
test -f "$TWO_ARM_CSV"
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/analyze_wireless_log.py "$TWO_ARM_CSV"
```

Required: leader rate 45–55 Hz, all leader masks 63, follower response mask 63, no unexpected timeout/rejection/bus fault, control-chain p95 below 100 ms, correct directions, no visible jump or sustained oscillation.

- [ ] **Step 4: Test leader reset recovery**

During a separately logged safe run, retain its printed CSV path, then press only the leader XIAO reset button. Confirm follower stops and holds; move leader while it reconnects; confirm a new leader boot session and new follower control session; confirm approximately 1-second smooth catch-up with no old-target replay or visible jump. Save those observations in `logs/wireless-leader/leader-reset-recovery-2026-09-09.md`.

- [ ] **Step 5: Test changed hotspot IP without reflashing**

Stop motion and power servos off. Record `ip -4 -o addr show` before and after restarting/reconnecting the phone hotspot. This gate is valid only if the computer IP actually changes. Without reflashing either XIAO, run wireless `--check`, then a supported small-motion run and retain its printed CSV path. Save agent-discovery logs and observed addresses in `logs/wireless-leader/agent-ip-change-2026-09-09.md`, proving both XIAOs use the new source IP.

- [ ] **Step 6: Verify wired fallback**

Stop wireless motion, connect the known `usb-1a86_USB_Single_Serial_5A4B048657-if00` board, and run:

```bash
./start_soarm_demo.sh --leader wired --check
./start_soarm_demo.sh --leader wired
```

Perform one small supported joint motion, then Ctrl+C and confirm hold. Retain the printed CSV path and save operator observations in `logs/wireless-leader/wired-fallback-2026-09-09.md`.

- [ ] **Step 7: Run 10-minute wireless endurance test**

Run `--leader wireless` continuously for at least 600 seconds with normal safe motion and temperature/voltage observation. Retain the printed CSV path, analyze it, and save observations in `logs/wireless-leader/endurance-2026-09-09.md`. Require no bus faults, invalid commands, unexpected rejects/timeouts, wrong directions, visible jumps, abnormal sound, or abnormal temperature; masks remain 63 and control-chain p95 remains below 100 ms.

- [ ] **Step 8: Update matrix and commit hardware evidence**

Update only gates supported by saved observations. Force-add only the exact CSV/Markdown logs from Steps 2–7 plus the matrix. Verify filenames before committing:

```bash
read -r -p "两臂运动 CSV 绝对路径: " TWO_ARM_CSV
read -r -p "主臂复位恢复 CSV 绝对路径: " RESET_CSV
read -r -p "热点 IP 变化 CSV 绝对路径: " IP_CHANGE_CSV
read -r -p "有线回退 CSV 绝对路径: " WIRED_CSV
read -r -p "十分钟耐久 CSV 绝对路径: " ENDURANCE_CSV
test -f "$TWO_ARM_CSV"
test -f "$RESET_CSV"
test -f "$IP_CHANGE_CSV"
test -f "$WIRED_CSV"
test -f "$ENDURANCE_CSV"
git add -f "$TWO_ARM_CSV" "$RESET_CSV" "$IP_CHANGE_CSV" "$WIRED_CSV" "$ENDURANCE_CSV" \
  logs/wireless-leader/two-arm-motion-2026-09-09.md \
  logs/wireless-leader/leader-reset-recovery-2026-09-09.md \
  logs/wireless-leader/agent-ip-change-2026-09-09.md \
  logs/wireless-leader/wired-fallback-2026-09-09.md \
  logs/wireless-leader/endurance-2026-09-09.md \
  docs/soarm_wireless_test_matrix.md
git diff --cached --check
git diff --cached --name-only
git commit -m "test: validate wireless leader end to end"
```

If any criterion is unobserved, mark that gate partial and do not proceed to Task 15.

---

### Task 15: Make wireless leader the default after all hardware gates pass

**Files:**
- Modify: `tests/tools/test_wireless_launcher.py`
- Modify: `start_soarm_demo.sh`
- Modify: `firmware/xiao_soarm/README.md`
- Modify: `firmware/xiao_soarm_leader/README.md`
- Modify: `docs/soarm_wireless_test_matrix.md`

- [ ] **Step 1: Write the final failing default-mode test**

Add a launcher test asserting no-argument parsing selects `wireless`, while `--leader wired` explicitly selects wired and preserves the stable serial by-id path.

- [ ] **Step 2: Confirm red**

```bash
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_launcher.py -q
```

Expected: only the new default-mode assertion fails because development default is still wired.

- [ ] **Step 3: Switch the default and document final commands**

Change only the no-argument default to wireless. Keep both explicit modes and `--check`. Document power order, XIAO reset after flashing, wireless default, wired fallback, discovery behavior, evidence commands, and emergency power removal. Do not include credentials or fixed agent IPs.

- [ ] **Step 4: Run complete final verification**

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools -q
bash -n start_soarm_demo.sh
cd firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
cd ../xiao_soarm_leader
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
```

Expected: all tests and both builds pass. These commands do not upload.

- [ ] **Step 5: Commit the default switch**

```bash
cd /home/linao/so101_lerobot
git add tests/tools/test_wireless_launcher.py start_soarm_demo.sh \
  firmware/xiao_soarm/README.md firmware/xiao_soarm_leader/README.md \
  docs/soarm_wireless_test_matrix.md
git diff --cached --check
git diff --cached --name-only
git commit -m "feat: default to wireless leader teleoperation"
```

- [ ] **Step 6: Report final state**

```bash
git log -15 --oneline
git status --short
git check-ignore -v firmware/xiao_soarm/src/wifi_config.h
```

Report every commit, automated gate, firmware build/upload, hardware observation, evidence path, and any remaining partial gate. Never print the ignored credential file.
