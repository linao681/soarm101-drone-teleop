# Summer Wireless Speed Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the summer wireless teleoperation response by allowing every joint to advance up to `0.24 rad` per 20 ms firmware control tick, while retaining the current session, timeout, replay, handshake, and bus-fault protections.

**Architecture:** Keep the existing `control_logic::Controller` trajectory state machine and change only its six velocity constants from the conservative per-joint values to `12.0 rad/s`. At the fixed 50 Hz control rate, `12.0 rad/s × 0.020 s = 0.24 rad`, matching the host bridge's existing `--max-step-rad 0.24`. Verify the behavior in the native state-machine test before compiling or uploading firmware.

**Tech Stack:** C++17, PlatformIO Unity native tests, Arduino/ESP32-C3 firmware, Python wireless bridge, ROS 2 Humble, micro-ROS UDP.

## Global Constraints

- Read `docs/superpowers/specs/2026-09-08-summer-speed-profile-design.md` before editing.
- Preserve all existing user changes and unrelated untracked files.
- Do not modify `start_soarm_demo.sh`, WiFi settings, calibration values, ROS QoS, servo `Goal_Speed=0`, or acceleration `254`.
- Never print, stage, or commit `firmware/xiao_soarm/src/wifi_config.h`, WiFi passwords, or other credentials.
- Do not upload firmware until both `pio test -e native` and the ESP32-C3 build pass on the final source tree.
- Upload only after the operator confirms the follower is mechanically supported, its workspace is clear, and servo power is disconnected.
- Do not claim a hardware check passed without the operator's physical observation and saved evidence.
- If a stop condition is reached, stop immediately and report the full command, output, `git status --short`, and `git log -1 --oneline`.

---

### Task 1: Define and implement the summer response limit

**Files:**
- Modify: `firmware/xiao_soarm/test/test_control_logic/test_main.cpp:63-72`
- Modify: `firmware/xiao_soarm/src/control_logic.h:9-13`
- Modify: `firmware/xiao_soarm/README.md:50-53`
- Modify: `docs/soarm_wireless_test_matrix.md:57`

**Interfaces:**
- Consumes: `control_logic::Controller::on_command(...)` and `control_logic::Controller::tick(...)`.
- Produces: `control_logic::kMaxVelocityRadS == {12.0, 12.0, 12.0, 12.0, 12.0, 12.0}`.
- Preserves: the 20 ms firmware tick, host `--max-step-rad 0.24`, and all state/rejection semantics.

- [ ] **Step 1: Confirm the starting tree and protected files**

Run from `/home/linao/so101_lerobot`:

```bash
git status --short
git log -1 --oneline
git check-ignore -v firmware/xiao_soarm/src/wifi_config.h
```

Expected: note all pre-existing changes without modifying them; `wifi_config.h` is ignored. Do not run a command that displays its contents.

- [ ] **Step 2: Write the failing native test**

Add the following test after the existing `test_trajectory_obeys_velocity_limit` in `firmware/xiao_soarm/test/test_control_logic/test_main.cpp`; keep the existing generic velocity-limit test:

```cpp
void test_summer_profile_applies_host_step_in_one_tick() {
    Controller controller = active_controller_at_zero(7);
    controller.on_command(command(7, 2, filled(0.24)), zeros(), true, 0);

    const Output output = controller.tick(20, zeros(), true);

    for (size_t joint = 0; joint < kJointCount; ++joint) {
        TEST_ASSERT_DOUBLE_WITHIN(1e-6, 0.24, output.applied_target[joint]);
        TEST_ASSERT_TRUE(output.should_write);
    }
}
```

Add this entry immediately after the existing trajectory test in the main test list:

```cpp
RUN_TEST(test_summer_profile_applies_host_step_in_one_tick);
```

- [ ] **Step 3: Run the native test and confirm the intended failure**

Run:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: FAIL in `test_summer_profile_applies_host_step_in_one_tick`; the current first three joints advance only about `0.016 rad`, proving the test detects the conservative `0.8 rad/s` profile. If collection, compilation, or another test fails instead, stop and report rather than editing production code.

- [ ] **Step 4: Implement the minimal velocity change**

In `firmware/xiao_soarm/src/control_logic.h`, replace the existing velocity array with exactly:

```cpp
constexpr double kMaxVelocityRadS[kJointCount] = {
    12.0, 12.0, 12.0, 12.0, 12.0, 12.0
};
```

Do not alter `Controller::on_command`, `Controller::tick`, the timeout, handshake tolerance, sequence comparison, or rejection states.

- [ ] **Step 5: Update the static documentation**

In `firmware/xiao_soarm/README.md`, replace the control-limit sentence with:

```text
首次控制命令必须接近从臂当前回读姿态，之后固件会检查校准软限位。控制 tick 为 50 Hz，
六个关节的轨迹上限均为 12.0 rad/s，对应每个 20 ms tick 最多前进 0.24 rad；
通信超时 500 ms 后保持最后目标位置。
```

In `docs/soarm_wireless_test_matrix.md`, replace the paragraph describing the old six speeds with:

```text
固件控制 tick 为 50 Hz，关节状态和从臂状态发布为 20 Hz。超时阈值为 500 ms；首次握手要求每个关节与当前回读姿态的差值不超过 0.05 rad。六个关节的轨迹速度上限均为 12.0 rad/s，对应每个 20 ms 控制 tick 最多前进 0.24 rad，与电脑端命令步长上限一致。
```

- [ ] **Step 6: Run the complete native test suite**

Run:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
```

Expected: all seven native tests pass, including the existing generic trajectory test and `test_summer_profile_applies_host_step_in_one_tick`. If any test fails, stop; do not compile or upload.

- [ ] **Step 7: Compile the ESP32-C3 firmware without uploading**

Run:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
```

Expected: `SUCCESS` for `seeed_xiao_esp32c3`. This command must not include `upload` or `--target upload`. If compilation fails, stop and do not upload.

- [ ] **Step 8: Verify the implementation diff**

Run:

```bash
cd /home/linao/so101_lerobot
git diff --check
git diff -- firmware/xiao_soarm/src/control_logic.h firmware/xiao_soarm/test/test_control_logic/test_main.cpp firmware/xiao_soarm/README.md docs/soarm_wireless_test_matrix.md
git status --short
```

Expected: only the four planned files are modified by this task; unrelated pre-existing files remain untouched. Confirm no WiFi configuration or credential file is staged.

- [ ] **Step 9: Commit Task 1 separately**

Run:

```bash
cd /home/linao/so101_lerobot
git add firmware/xiao_soarm/src/control_logic.h firmware/xiao_soarm/test/test_control_logic/test_main.cpp firmware/xiao_soarm/README.md docs/soarm_wireless_test_matrix.md
git diff --cached --check
git diff --cached --name-only
git commit -m "feat: restore summer wireless response speed"
```

Expected staged names: exactly the four files listed above. Stop after this commit and report the native-test and compile outputs before requesting permission to upload.

---

### Task 2: Upload only after the firmware gates pass

**Files:**
- Create after observation: `logs/speed-profile/2026-09-08-upload-smoke.txt`

**Interfaces:**
- Consumes: the exact firmware commit produced by Task 1.
- Produces: a flashed XIAO ESP32-C3 running the `12.0 rad/s` profile and a serial smoke-test log.

- [ ] **Step 1: Reconfirm the final source gates**

Run:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio test -e native
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3
```

Expected: native tests and ESP32-C3 build both succeed on the committed tree. If either fails, stop and do not upload.

- [ ] **Step 2: Ask for the physical upload confirmation**

Before any upload command, obtain explicit operator confirmation of all four statements:

```text
从臂已机械支撑；运动空间已清空；舵机电源已断开；XIAO USB 已连接。
```

Do not infer these conditions from device listings.

- [ ] **Step 3: Identify the exact XIAO upload port**

Run:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio device list
```

Expected: one XIAO ESP32-C3 entry with USB VID:PID `303A:1001`, previously seen as `/dev/ttyACM0`. If no matching device exists or more than one candidate is ambiguous, stop and ask the operator; never guess a port.

- [ ] **Step 4: Upload the already-tested firmware**

If the matching XIAO is `/dev/ttyACM0`, run exactly:

```bash
cd /home/linao/so101_lerobot/firmware/xiao_soarm
/home/linao/.platformio/penv/bin/pio run -e seeed_xiao_esp32c3 --target upload --upload-port /dev/ttyACM0
```

Expected: upload completes with `SUCCESS`. If the resolved port differs, replace only `/dev/ttyACM0` with the observed XIAO path. On failure, leave servo power disconnected and report the output.

- [ ] **Step 5: Capture the USB-only serial smoke check**

Keep servo power disconnected. In one terminal, run the micro-ROS agent if it is not already running:

```bash
source /opt/ros/humble/setup.bash
snap run micro-ros-agent udp4 --port 8888 -v4
```

In another terminal, run:

```bash
mkdir -p /home/linao/so101_lerobot/logs/speed-profile
timeout 25s /home/linao/.platformio/penv/bin/pio device monitor -p /dev/ttyACM0 -b 115200 | tee /home/linao/so101_lerobot/logs/speed-profile/2026-09-08-upload-smoke.txt
```

Expected physical state and output: servos remain unpowered; firmware boots, connects to WiFi/micro-ROS, and reports `servo_mask:0x00` or `BUS_NOT_READY`; no motion command is sent. A timeout exit code from the 25-second monitor is expected. If the firmware repeatedly resets or does not create ROS entities, stop before powering servos.

- [ ] **Step 6: Commit only the observed smoke evidence**

Review the captured log for credentials before staging. It may contain SSID and IP addresses but must not contain a WiFi password. Then run:

```bash
cd /home/linao/so101_lerobot
git add -f logs/speed-profile/2026-09-08-upload-smoke.txt
git diff --cached --check
git commit -m "test: record summer speed firmware smoke check"
```

Do not claim powered-servo or motion testing passed at this point.

---

### Task 3: Validate powered response on the real arm

**Files:**
- Create after the run: `logs/speed-profile/2026-09-08-powered-response.md`
- Add after the run: the exact timestamped CSV path printed by the launcher and captured in `SPEED_PROFILE_CSV`
- Modify after the run: `docs/soarm_wireless_test_matrix.md`

**Interfaces:**
- Consumes: flashed Task 1 firmware, current `start_soarm_demo.sh`, matching leader/follower calibration, and the operator's physical observations.
- Produces: evidence that normal live teleoperation has summer-like response without jumps, wrong directions, sustained oscillation, or unexpected rejects.

- [ ] **Step 1: Obtain powered-test confirmation**

Before applying servo power, require the operator to confirm:

```text
从臂已机械支撑；运动空间已清空；可立即断开舵机电源；主从臂均处于安全姿态。
```

- [ ] **Step 2: Run the normal launcher**

Run:

```bash
cd /home/linao/so101_lerobot
./start_soarm_demo.sh
```

Record the exact CSV path printed after `本次指标日志：`. Do not substitute a different or older CSV.

- [ ] **Step 3: Perform staged physical motion**

With the operator continuously observing the arm:

1. Move only `shoulder_pan` slowly through a small range and verify direction.
2. Move `shoulder_pan` faster and verify it tracks without the previous `0.8 rad/s` lag.
3. Repeat small then normal-speed motion for `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, and `gripper`, one joint at a time.
4. Perform a short coordinated motion of all six joints.
5. Press `Ctrl+C` and verify the follower holds its last pose.

Stop immediately and remove servo power for any jump, wrong direction, sustained oscillation, collision risk, bus fault, abnormal sound, or abnormal temperature.

- [ ] **Step 4: Analyze the exact run CSV**

Paste the exact absolute CSV path printed by the launcher when prompted, then run:

```bash
cd /home/linao/so101_lerobot
read -r -p "粘贴本次指标日志的绝对路径: " SPEED_PROFILE_CSV
test -f "$SPEED_PROFILE_CSV"
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/analyze_wireless_log.py "$SPEED_PROFILE_CSV"
```

Pass criteria:

- `rejections_total` is `0`.
- `response_mask` remains `63` in the CSV rows.
- No unexpected timeout occurs during uninterrupted WiFi operation.
- The operator confirms all six directions are correct, normal motion feels comparable to the summer version, and there is no visible jump or sustained oscillation.

The CSV analyzer's aggregate tracking error may include deliberate rapid moves; do not use RMSE alone to claim success.

- [ ] **Step 5: Save the physical evidence**

Create `logs/speed-profile/2026-09-08-powered-response.md` using `apply_patch`. Record only observed facts: firmware commit hash, operator name, power arrangement, exact CSV path, analyzer values, six-joint direction observations, response comparison, stop/hold observation, and whether any jump, oscillation, bus fault, abnormal sound, or abnormal temperature occurred.

Update `docs/soarm_wireless_test_matrix.md` only if the recorded evidence satisfies the relevant Gate 7 criteria. If voltage or temperature was not actually observed, leave Gate 7 as partial and state exactly what remains unverified.

- [ ] **Step 6: Commit the hardware evidence separately**

Run:

```bash
cd /home/linao/so101_lerobot
git add docs/soarm_wireless_test_matrix.md
read -r -p "再次粘贴本次指标日志的绝对路径: " SPEED_PROFILE_CSV
test -f "$SPEED_PROFILE_CSV"
sed -i 's/\r$//' "$SPEED_PROFILE_CSV"
git add -f logs/speed-profile/2026-09-08-powered-response.md "$SPEED_PROFILE_CSV"
git diff --cached --check
git diff --cached --name-only
git commit -m "test: record summer wireless speed validation"
```

Stage only the exact evidence files from this run. Do not stage unrelated PDFs, documents, handoff notes, plans, calibration files, or credentials.

- [ ] **Step 7: Report final repository state**

Run:

```bash
cd /home/linao/so101_lerobot
git log -3 --oneline
git status --short
```

Report native-test results, compile result, upload result, physical observations, evidence paths, commits, and all remaining partial or unexecuted gates. Do not describe Gate 7 or the speed restoration as physically passed unless Step 3 and Step 5 contain real operator observations.
