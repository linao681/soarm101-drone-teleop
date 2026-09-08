# Faster WiFi Recovery Catch-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the follower catch up to the leader's current pose in 3 seconds after WiFi recovery while keeping the normal startup synchronization at 8 seconds.

**Architecture:** Add a dedicated `--recovery-blend-duration` argument to the wireless bridge and pass it from the launcher through `SOARM_RECOVERY_BLEND_DURATION`. Use this duration only in the recovery `startup_blend` call; keep the existing startup call unchanged. The existing per-command `--max-step-rad=0.24` limiter remains the motion safety bound.

**Tech Stack:** Python 3.10, argparse, pytest, Ruff, Bash launcher.

## Global Constraints

- Recovery blend duration defaults to `3.0` seconds.
- Normal startup duration remains `8.0` seconds.
- Existing `0.24 rad` per-command step limit remains unchanged.
- Do not change the firmware protocol, timeout policy, credentials, or unrelated working-tree files.
- Gate 9 must be rerun on the real hardware after implementation; automatic tests cannot prove the physical motion result.

---

### Task 1: Add and forward the recovery blend duration

**Files:**
- Modify: `tools/wireless_teleoperate.py:56-80, 424-449`
- Modify: `start_soarm_demo.sh:28-36, 160-176`
- Test: `tests/tools/test_wireless_teleoperate.py`
- Test: `tests/tools/test_wireless_launcher.py`

**Interfaces:**
- Produces CLI option `--recovery-blend-duration FLOAT`, default `3.0`.
- Produces launcher environment override `SOARM_RECOVERY_BLEND_DURATION`, default `3`.
- The recovery `startup_blend(..., duration, ...)` receives `args.recovery_blend_duration`; initial synchronization continues receiving `args.startup_duration`.

- [ ] **Step 1: Write the failing tests**

Add these assertions to `tests/tools/test_wireless_teleoperate.py`:

```python
def test_recovery_blend_duration_has_three_second_default():
    source = (Path(__file__).parents[2] / "tools" / "wireless_teleoperate.py").read_text()

    assert '"--recovery-blend-duration"' in source
    assert "default=3.0" in source
```

Add these assertions to `tests/tools/test_wireless_launcher.py`:

```python
def test_wireless_launcher_forwards_recovery_blend_duration():
    launcher = (Path(__file__).parents[2] / "start_soarm_demo.sh").read_text()

    assert 'RECOVERY_BLEND_DURATION="${SOARM_RECOVERY_BLEND_DURATION:-3}"' in launcher
    assert '    --recovery-blend-duration "$RECOVERY_BLEND_DURATION" \\' in launcher
```

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_wireless_teleoperate.py -k recovery_blend_duration
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_wireless_launcher.py -k recovery_blend_duration
```

Expected: both tests fail because the new bridge option and launcher forwarding do not exist yet.

- [ ] **Step 3: Implement the minimal bridge change**

In `tools/wireless_teleoperate.py`, add the argument immediately after `--startup-duration`:

```python
parser.add_argument(
    "--recovery-blend-duration",
    type=float,
    default=3.0,
    help="Seconds used to smoothly catch up after follower session recovery",
)
```

Validate it with the existing positive-duration checks:

```python
if args.feedback_timeout <= 0.0 or args.recovery_timeout <= 0.0:
    raise ValueError("--feedback-timeout and --recovery-timeout must be positive")
if args.startup_duration <= 0.0 or args.recovery_blend_duration <= 0.0:
    raise ValueError("--startup-duration and --recovery-blend-duration must be positive")
```

In the recovery branch, change only the duration argument of the second `startup_blend` call from `args.startup_duration` to `args.recovery_blend_duration`. Leave the initial synchronization call using `args.startup_duration`.

- [ ] **Step 4: Implement launcher forwarding**

In `start_soarm_demo.sh`, add:

```bash
RECOVERY_BLEND_DURATION="${SOARM_RECOVERY_BLEND_DURATION:-3}"
```

Then append this option beside the existing recovery options in the bridge command:

```bash
    --recovery-blend-duration "$RECOVERY_BLEND_DURATION" \
```

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_wireless_teleoperate.py -k recovery_blend_duration
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_wireless_launcher.py -k recovery_blend_duration
```

Expected: all selected tests pass.

- [ ] **Step 6: Run the full relevant verification suite**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_wireless_teleoperate.py tests/tools/test_wireless_launcher.py tests/tools/test_soarm_wireless_control.py tests/tools/test_soarm_wireless_gate6.py tests/tools/test_soarm_wireless_metrics.py tests/tools/test_soarm_wireless_protocol.py
/home/linao/miniforge3/envs/lerobot_so101/bin/python -m ruff check tools/wireless_teleoperate.py tests/tools/test_wireless_teleoperate.py tests/tools/test_wireless_launcher.py
bash -n start_soarm_demo.sh
```

Expected: pytest passes, Ruff reports `All checks passed!`, and `bash -n` exits successfully.

- [ ] **Step 7: Commit the implementation**

```bash
git add tools/wireless_teleoperate.py start_soarm_demo.sh tests/tools/test_wireless_teleoperate.py tests/tools/test_wireless_launcher.py
git diff --cached --check
git commit -m "feat: speed up wireless recovery catch-up"
```

- [ ] **Step 8: Perform the required hardware follow-up**

Run the normal launcher with both arms safely supported. During active teleoperation, disconnect and reconnect the PC WiFi, move the leader while disconnected, and observe that the follower catches up smoothly in about 3 seconds without a jump or stale-target replay. Save the resulting CSV and update Gate 9 evidence only after the physical observation is complete.
