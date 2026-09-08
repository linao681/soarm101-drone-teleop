# Wireless Gate 6 Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a host-side, evidence-producing validator that performs one supported `+0.10 rad` gripper movement only after a measured-pose handshake and verifies acknowledgement, direction, and bus health.

**Architecture:** Put all transport-independent preflight, target construction, and result evaluation in `tools/soarm_wireless/gate6.py`. Put ROS subscriptions, protocol session commands, typed operator confirmation, evidence serialization, and process exit behavior in `tools/validate_wireless_gate6.py`. Reuse `WirelessFollowerBridge`, `arm_at_current_pose`, `wait_for_follower`, `load_follower_calibration`, and the existing command/status protocol instead of duplicating ROS transport code.

**Tech Stack:** Python 3.10, `rclpy`, ROS 2 `sensor_msgs/JointState`, `std_msgs/Int32MultiArray`, existing `tools.soarm_wireless` helpers, `pytest`, Ruff.

## Global Constraints

- Test the `gripper` only; its index is `JOINT_NAMES.index("gripper")`.
- Command exactly `+0.10 rad` from the freshly measured pose, with a `0.03 rad` completion tolerance.
- The five non-gripper target values must equal their captured starting values; their measured displacement must not exceed `0.03 rad`.
- Require `response_mask == 0x3f`, status rejection `NONE`, and unchanged read/write error counters from preflight to completion.
- Use a fresh random command session and unchanged-pose handshake before the movement command.
- Publish at 20 Hz for no more than 3 seconds after handshake; never command a return movement.
- Write an evidence JSON file for every pass and every failure under `logs/gate-06/`; the physical operator decides whether visual direction/no-other-joint motion passes.
- Do not modify firmware, calibration, normal leader teleoperation, or WiFi configuration.

---

### Task 1: Add Pure Gate 6 Safety and Evaluation Logic

**Files:**
- Create: `tools/soarm_wireless/gate6.py`
- Create: `tests/tools/test_soarm_wireless_gate6.py`

**Interfaces:**
- Consumes: `JOINT_NAMES` and `raw_to_radians` from `tools.soarm_wireless.control`; `FollowerStatus`, `FollowerState`, and `RejectReason` from `tools.soarm_wireless.protocol`.
- Produces: `GRIPPER_INDEX`, `GRIPPER_DELTA_RAD`, `POSITION_TOLERANCE_RAD`, `Gate6Failure`, `build_target`, `validate_preflight`, and `evaluate_completion` for the ROS runner.

- [ ] **Step 1: Write the failing pure-logic tests**

```python
import pytest

from tools.soarm_wireless.gate6 import (
    GRIPPER_DELTA_RAD,
    Gate6Failure,
    build_target,
    evaluate_completion,
)


def test_build_target_changes_only_gripper():
    start = [0.0, 0.1, 0.2, 0.3, 0.4, -0.5]
    target = build_target(start, {"gripper": {"range_min": 0, "range_max": 4095}})
    assert target[:-1] == start[:-1]
    assert target[-1] == pytest.approx(start[-1] + GRIPPER_DELTA_RAD)


def test_build_target_rejects_gripper_outside_calibration_range():
    start = [0.0] * 6
    with pytest.raises(Gate6Failure, match="outside follower calibration"):
        build_target(start, {"gripper": {"range_min": 0, "range_max": 2048}})


def test_completion_rejects_wrong_direction_and_other_joint_motion(status_active):
    start = [0.0] * 6
    target = build_target(start, {"gripper": {"range_min": 0, "range_max": 4095}})
    wrong_direction = [0.0] * 6
    wrong_direction[-1] = -0.05
    with pytest.raises(Gate6Failure, match="gripper direction"):
        evaluate_completion(start, target, wrong_direction, status_active, 0, 0)

    moved_body_joint = list(target)
    moved_body_joint[0] = 0.04
    with pytest.raises(Gate6Failure, match="unexpected motion"):
        evaluate_completion(start, target, moved_body_joint, status_active, 0, 0)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_wireless_gate6.py -q
```

Expected: FAIL because `tools.soarm_wireless.gate6` does not exist.

- [ ] **Step 3: Implement the pure safety layer**

```python
# tools/soarm_wireless/gate6.py
from __future__ import annotations

from tools.soarm_wireless.control import JOINT_NAMES, raw_to_radians
from tools.soarm_wireless.protocol import FollowerState, RejectReason

GRIPPER_INDEX = JOINT_NAMES.index("gripper")
GRIPPER_DELTA_RAD = 0.10
POSITION_TOLERANCE_RAD = 0.03


class Gate6Failure(RuntimeError):
    pass


def build_target(start: list[float], calibration: dict[str, dict[str, int]]) -> list[float]:
    if len(start) != len(JOINT_NAMES):
        raise Gate6Failure("expected six starting joint positions")
    target = list(start)
    target[GRIPPER_INDEX] += GRIPPER_DELTA_RAD
    low = raw_to_radians(calibration["gripper"]["range_min"])
    high = raw_to_radians(calibration["gripper"]["range_max"])
    if not low <= target[GRIPPER_INDEX] <= high:
        raise Gate6Failure("gripper target is outside follower calibration")
    return target


def validate_preflight(status, read_errors: int, write_errors: int) -> None:
    if status.response_mask != 0x3F:
        raise Gate6Failure(f"servo response mask is 0x{status.response_mask:02x}")
    if status.state not in (FollowerState.WAITING_HANDSHAKE, FollowerState.HOLDING_TIMEOUT):
        raise Gate6Failure(f"follower state is {status.state.name}")
    if status.reject_reason is not RejectReason.NONE:
        raise Gate6Failure(f"follower rejection is {status.reject_reason.name}")
    if status.read_errors != read_errors or status.write_errors != write_errors:
        raise Gate6Failure("bus error counters changed during preflight")


def evaluate_completion(start, target, measured, status, read_errors: int, write_errors: int) -> None:
    if status.response_mask != 0x3F or status.state is not FollowerState.ACTIVE:
        raise Gate6Failure("follower is not active with all servos online")
    if status.reject_reason is not RejectReason.NONE:
        raise Gate6Failure(f"follower rejection is {status.reject_reason.name}")
    if status.read_errors != read_errors or status.write_errors != write_errors:
        raise Gate6Failure("bus error counters increased")
    if measured[GRIPPER_INDEX] - start[GRIPPER_INDEX] <= 0.0:
        raise Gate6Failure("gripper direction was not positive")
    if abs(measured[GRIPPER_INDEX] - target[GRIPPER_INDEX]) > POSITION_TOLERANCE_RAD:
        raise Gate6Failure("gripper did not reach the requested target")
    for index, value in enumerate(measured):
        if index != GRIPPER_INDEX and abs(value - start[index]) > POSITION_TOLERANCE_RAD:
            raise Gate6Failure(f"unexpected motion on {JOINT_NAMES[index]}")
```

- [ ] **Step 4: Add status fixtures and completion/preflight coverage**

```python
from tools.soarm_wireless.protocol import FollowerState, FollowerStatus, RejectReason


@pytest.fixture
def status_active():
    return FollowerStatus(
        version=1, state=FollowerState.ACTIVE, session_id=7,
        last_received_sequence=2, last_applied_sequence=2, command_age_ms=10,
        response_mask=0x3F, reject_reason=RejectReason.NONE,
        command_timeout_count=0, invalid_command_count=0,
        control_reject_count=0, read_errors=0, write_errors=0, rssi_dbm=-40,
    )


def test_completion_accepts_positive_gripper_motion(status_active):
    start = [0.0] * 6
    target = build_target(start, {"gripper": {"range_min": 0, "range_max": 4095}})
    measured = list(target)
    evaluate_completion(start, target, measured, status_active, 0, 0)
```

- [ ] **Step 5: Run the pure test suite to verify it passes**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_wireless_gate6.py -q
```

Expected: all Gate 6 pure-logic tests PASS.

- [ ] **Step 6: Commit the pure logic**

```bash
git add tools/soarm_wireless/gate6.py tests/tools/test_soarm_wireless_gate6.py
git commit -m "feat: add gate 6 safety checks"
```

### Task 2: Add JSON Evidence Serialization

**Files:**
- Modify: `tools/soarm_wireless/gate6.py`
- Modify: `tests/tools/test_soarm_wireless_gate6.py`

**Interfaces:**
- Consumes: `Gate6Failure` and result data from Task 1.
- Produces: `write_evidence(path: Path, evidence: dict[str, object]) -> None` for the ROS runner.

- [ ] **Step 1: Write the failing evidence test**

```python
import json

from tools.soarm_wireless.gate6 import write_evidence


def test_write_evidence_creates_parseable_json(tmp_path):
    path = tmp_path / "gate6.json"
    write_evidence(path, {"result": "PASS", "joint": "gripper", "delta_rad": 0.10})
    assert json.loads(path.read_text()) == {
        "result": "PASS", "joint": "gripper", "delta_rad": 0.10
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_wireless_gate6.py::test_write_evidence_creates_parseable_json -q
```

Expected: FAIL because `write_evidence` is undefined.

- [ ] **Step 3: Implement atomic JSON evidence writing**

```python
import json
from pathlib import Path


def write_evidence(path: Path, evidence: dict[str, object]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_soarm_wireless_gate6.py -q
```

Expected: all Gate 6 tests PASS.

- [ ] **Step 5: Commit evidence serialization**

```bash
git add tools/soarm_wireless/gate6.py tests/tools/test_soarm_wireless_gate6.py
git commit -m "feat: save gate 6 validation evidence"
```

### Task 3: Add the ROS Gate 6 Runner

**Files:**
- Create: `tools/validate_wireless_gate6.py`
- Modify: `tests/tools/test_wireless_teleoperate.py`

**Interfaces:**
- Consumes: `WirelessFollowerBridge`, `wait_for_follower`, `arm_at_current_pose`, `load_follower_calibration`; `build_target`, `validate_preflight`, `evaluate_completion`, `write_evidence`.
- Produces: executable CLI `python tools/validate_wireless_gate6.py --yes --follower-calibration cali/my_follower.json` and one JSON evidence record.

- [ ] **Step 1: Write the failing runner contract test**

```python
from pathlib import Path


def test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta():
    source = (Path(__file__).parents[2] / "tools" / "validate_wireless_gate6.py").read_text()
    assert 'parser.add_argument("--yes", action="store_true")' in source
    assert "GRIPPER_DELTA_RAD" in source
    assert "arm_at_current_pose(node, start)" in source
    assert "node.publish_command(target)" in source
    assert "write_evidence" in source
```

- [ ] **Step 2: Run the runner-contract test to verify it fails**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_teleoperate.py::test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta -q
```

Expected: FAIL because `tools/validate_wireless_gate6.py` does not exist.

- [ ] **Step 3: Implement the runner loop and evidence record**

```python
# Essential control sequence inside run(args)
rclpy.init()
node = WirelessFollowerBridge()
evidence = {"joint": "gripper", "delta_rad": GRIPPER_DELTA_RAD, "result": "FAIL"}
try:
    start = wait_for_follower(node)
    status = node.latest_status
    if status is None:
        raise Gate6Failure("no follower status received")
    baseline_read_errors = status.read_errors
    baseline_write_errors = status.write_errors
    validate_preflight(status, baseline_read_errors, baseline_write_errors)
    target = build_target(start, load_follower_calibration(args.follower_calibration))
    require_confirmation(args.yes)
    arm_at_current_pose(node, start)
    movement_sequence = publish_until_acknowledged(
        node, target, baseline_read_errors, baseline_write_errors, timeout_s=3.0
    )
    final = wait_for_follower(node, timeout=1.0, after_monotonic=0.0)
    evaluate_completion(
        start, target, final, node.latest_status,
        baseline_read_errors, baseline_write_errors,
    )
    evidence.update({"result": "PASS", "start": start, "target": target,
                     "measured_final": final, "movement_sequence": movement_sequence})
except Exception as error:
    evidence["failure_reason"] = str(error)
    raise
finally:
    evidence["status_final"] = status_to_list(node.latest_status)
    write_evidence(args.evidence_path, evidence)
    node.destroy_node()
    rclpy.shutdown()
```

`publish_until_acknowledged` must publish at 20 Hz, call `rclpy.spin_once`,
fail on stale feedback, wrong session, non-`ACTIVE` state, nonzero rejection,
non-`0x3f` mask, or increased error counters, and return the acknowledged
movement sequence. `require_confirmation` prints the power/support warning and
accepts only an exact `MOVE` input when `--yes` is absent.

- [ ] **Step 4: Run the runner-contract test to verify it passes**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest tests/tools/test_wireless_teleoperate.py::test_gate6_runner_requires_confirmation_and_uses_exact_gripper_delta -q
```

Expected: PASS.

- [ ] **Step 5: Run the complete host-only verification**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest \
  tests/tools/test_soarm_wireless_gate6.py \
  tests/tools/test_wireless_teleoperate.py \
  tests/tools/test_soarm_wireless_control.py \
  tests/tools/test_soarm_wireless_protocol.py \
  tests/tools/test_soarm_wireless_metrics.py -q
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m ruff check \
  tools/soarm_wireless tools/validate_wireless_gate6.py tests/tools
git diff --check
```

Expected: all tests pass, Ruff reports `All checks passed!`, and `git diff --check` is silent.

- [ ] **Step 6: Commit the runner**

```bash
git add tools/validate_wireless_gate6.py tests/tools/test_wireless_teleoperate.py
git commit -m "feat: add supported gripper gate 6 validator"
```

### Task 4: Document and Perform the Physical Gate 6 Test

**Files:**
- Modify: `docs/soarm_wireless_test_matrix.md`
- Create: `logs/gate-06/YYYY-mm-dd-gripper-step.md`

**Interfaces:**
- Consumes: JSON evidence created by `tools/validate_wireless_gate6.py`.
- Produces: a recorded Gate 6 result only after physical operator confirmation.

- [ ] **Step 1: Run the non-motion preflight with the follower supported**

Run:

```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /follower_status --once
```

Expected: status version `1`, response mask `63`, rejection reason `0`, and no read/write error increase after the XIAO reset.

- [ ] **Step 2: Run the supervised 0.10-rad gripper validator**

Run:

```bash
cd /home/linao/so101_lerobot
/home/linao/miniforge3/envs/lerobot_so101/bin/python \
  tools/validate_wireless_gate6.py \
  --follower-calibration cali/my_follower.json
```

Expected: the operator types `MOVE`; only the gripper opens by approximately `0.10 rad`; the process exits 0 and prints its JSON evidence path.

- [ ] **Step 3: Apply the physical stop condition**

If any body joint visibly moves, the gripper moves in the wrong direction, a status rejection occurs, response mask differs from `63`, or any bus error counter increases: immediately remove servo power, retain the generated JSON and terminal output, and do not update Gate 6 as passed.

- [ ] **Step 4: Record the result only after operator confirmation**

For a pass, create the evidence summary with the exact JSON path, physical observation, start/target/final positions, session and sequence IDs, response mask, acknowledgment latency, and error counters. Update row 6 with the date, firmware commit, operator, power arrangement, `通过`, and evidence paths.

- [ ] **Step 5: Commit Gate 6 evidence**

```bash
git add docs/soarm_wireless_test_matrix.md
git add -f logs/gate-06/YYYY-mm-dd-gripper-step.md logs/gate-06/*.json
git commit -m "test: record wireless hardware gate 6"
```

## Self-Review

- Spec coverage: Task 1 enforces target, calibration, direction, other-joint, status, and error-counter constraints. Task 2 guarantees pass and failure evidence. Task 3 defines handshake, fresh session, 20 Hz/3-second motion, confirmation, and cleanup. Task 4 defines physical safety, stop conditions, and test-matrix recording.
- Placeholder scan: the only `YYYY-mm-dd` occurrence is the runtime-generated evidence filename pattern, not an unfinished implementation choice.
- Type consistency: Task 1 exports all helpers named in Tasks 2–3; Task 3 uses existing bridge APIs without changing their signatures; Task 4 calls the exact Task 3 CLI.
