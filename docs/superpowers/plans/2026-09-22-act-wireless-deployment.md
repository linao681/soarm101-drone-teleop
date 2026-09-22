# ACT Wireless Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy an ACT policy trained with wired SO-ARM101 LeRobot data to the existing wireless follower through a tested host-side adapter, while preserving the firmware safety controls and the current human teleoperation path.

**Architecture:** Add a pure ACT observation/action adapter, extract the existing wireless follower protocol into a reusable bridge, and add a standalone ACT rollout entry point. The host sends validated six-joint targets at 30 Hz without the old host-side per-step smoothing limit; the XIAO firmware remains responsible for velocity, calibrated-range, timeout, stale-sequence, and bus-fault safety.

**Tech Stack:** Python 3.10, NumPy, PyTorch/LeRobot policy APIs, OpenCV-backed `OpenCVCamera`, ROS 2 Humble `rclpy`, `sensor_msgs/msg/JointState`, `std_msgs/msg/Int32MultiArray`, pytest, existing SO-ARM wireless protocol helpers.

## Global Constraints

- Use the camera feature keys `observation.images.top` and `observation.images.wrist` exactly; `top` is the fixed scene camera and `wrist` is the wrist camera.
- Use ordinary USB cameras through the existing `OpenCVCameraConfig` and `OpenCVCamera` classes. Do not add a vendor camera dependency.
- Keep the six-joint order exactly `shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`.
- Default the rollout loop to 30 Hz and keep acknowledgement processing asynchronous; do not block every policy step on an acknowledgement.
- Remove the ACT host-side `max_step_rad` smoothing behavior. Keep the XIAO firmware velocity limiter, calibrated raw-range checks, command timeout hold, session/sequence validation, and bus-fault behavior unchanged.
- Do not modify firmware, Wi-Fi configuration, `wifi_config.h`, credentials, the wired data-collection workflow, or the existing main branch during implementation.
- Preserve the existing human teleoperation behavior while extracting shared code.
- All implementation tasks follow RED → run the focused test and record the failure → GREEN → run the focused test and record the pass → make one focused commit.
- Unit and dry-run evidence must never be described as successful real-hardware validation. Any hardware test remains operator-gated and requires a mechanically supported follower, clear motion space, and an immediately reachable power disconnect.
- Do not include datasets, policy checkpoints, Wi-Fi credentials, or `wifi_config.h` in commits.

## File Map

Create:

- `tools/soarm_wireless/act_adapter.py` — pure ACT observation/action contract.
- `tools/soarm_wireless/follower_bridge.py` — reusable ROS wireless follower session, command, status, and recovery bridge.
- `tools/act_wireless_rollout.py` — standalone ACT inference and wireless rollout entry point.
- `tests/tools/test_act_adapter.py` — adapter contract tests.
- `tests/tools/test_follower_bridge.py` — sequence and watchdog tests for the shared bridge helpers.
- `tests/tools/test_act_wireless_rollout.py` — camera/policy/publisher dry-run tests.
- `tests/tools/test_act_wireless_docs.py` — documentation and CLI contract checks.
- `docs/act_wireless_deployment.md` — user-facing wired-training and wireless-rollout guide.

Modify:

- `tools/wireless_teleoperate.py` — import the shared follower bridge, remove host-side step limiting from the human path, and retain its current wired/wireless leader behavior.
- `README.md` — add one link to the ACT wireless deployment guide without changing unrelated project description text.

Do not modify:

- `firmware/`, `wifi_config.h`, calibration secrets, dataset files, policy checkpoints, or the existing data-collection scripts.

---

## Task 1: Define the pure ACT observation/action contract

**Files:** `tools/soarm_wireless/act_adapter.py`, `tests/tools/test_act_adapter.py`

- [ ] Add `ACT_CAMERA_KEYS = ("observation.images.top", "observation.images.wrist")`, `ACT_STATE_KEY = "observation.state"`, and an action dimension derived from the existing `JOINT_NAMES`.
- [ ] Implement `coerce_policy_action(action) -> numpy.ndarray` with these exact rules: accept a NumPy array, a Python sequence, or an object exposing `detach().cpu().numpy()`; accept shape `(6,)` and squeeze shape `(1, 6)`; reject every other shape; convert to `float32`; reject non-finite values with a `ValueError`.
- [ ] Implement `build_observation(top, wrist, state) -> dict[str, numpy.ndarray]`; require each image to be an `H x W x 3` array with nonzero dimensions, require a six-element finite state vector, convert state to `float32`, and return only the two required image keys plus `observation.state`.
- [ ] Add a small `validate_joint_names(names)` helper that compares the exact six-joint tuple and raises a descriptive error for a reordered or incomplete state message.

### RED verification

- [ ] Add tests for exact observation keys, image/state shapes, batched policy output squeezing, wrong action dimension, non-finite action, invalid image rank/channel count, invalid state length, non-finite state, and reordered joint names.
- [ ] Run:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_act_adapter.py
  ```

- [ ] Confirm the new test module fails because `tools/soarm_wireless/act_adapter.py` does not yet exist.

### GREEN implementation and verification

- [ ] Implement the adapter functions with no ROS, camera, policy, or hardware imports so the module remains pure and fast to test.
- [ ] Re-run the same focused pytest command and confirm all adapter tests pass.
- [ ] Commit exactly the adapter and its tests with:

  ```bash
  git add tools/soarm_wireless/act_adapter.py tests/tools/test_act_adapter.py
  git commit -m "feat: define ACT wireless observation contract"
  ```

## Task 2: Extract and test the reusable wireless follower bridge

**Files:** `tools/soarm_wireless/follower_bridge.py`, `tests/tools/test_follower_bridge.py`, `tools/wireless_teleoperate.py`

- [ ] Move the existing follower ROS behavior from `tools/wireless_teleoperate.py` into `tools/soarm_wireless/follower_bridge.py` without changing protocol semantics: `/joint_states` and `/follower_status` subscriptions, `/joint_command` publication, session creation/reset, command sequence encoding, status ownership, current-pose arming, status watchdog, callback draining, and feedback recovery.
- [ ] Add a pure `CommandPublisherState` dataclass with `session_id`, `next_sequence`, and `next_command_id()` that emits `encode_command_id(session_id, sequence)` and wraps the sequence at `0xFFFFFFFF`.
- [ ] Keep status parsing through `FollowerStatus.from_array()` and session filtering through `status_matches_session()`; stale-session statuses must not arm or acknowledge a new session.
- [ ] Preserve the existing metrics hooks (`set_metrics_writer`, command context, leader sample context, status logging) so human teleoperation logs do not lose fields.
- [ ] Update `tools/wireless_teleoperate.py` to import the shared bridge/helpers instead of maintaining a second bridge implementation. Remove the `--max-step-rad` argument and all `limit_step()` calls from the human path so desired targets are published directly; keep feedback/recovery timeouts and firmware safety unchanged.
- [ ] Keep the existing startup/recovery blend arguments and semantics in the human tool unless a test proves they depend on the removed host step limiter; do not alter unrelated command-line behavior.

### RED verification

- [ ] Add tests using an in-process fake publisher and fake clock for: monotonic command IDs within a session, new session reset, sequence wrap, rejection of wrong joint names/non-finite positions before publication, ignoring a status from another session, and raising after a configured feedback outage.
- [ ] Run:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_follower_bridge.py
  ```

- [ ] Confirm the tests fail before the bridge module and extracted API exist.

### GREEN implementation and verification

- [ ] Implement the shared bridge by preserving the current callback and status field behavior, then make the human teleoperation module call the shared functions.
- [ ] Re-run the focused bridge tests and the existing wireless launcher/firmware contract tests:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_follower_bridge.py tests/tools/test_wireless_launcher.py tests/tools/test_firmware_status_contract.py
  ```

- [ ] Run `py_compile` for `tools/soarm_wireless/follower_bridge.py` and `tools/wireless_teleoperate.py`.
- [ ] Commit exactly this extraction and its tests with:

  ```bash
  git add tools/soarm_wireless/follower_bridge.py tests/tools/test_follower_bridge.py tools/wireless_teleoperate.py
  git commit -m "refactor: share wireless follower bridge"
  ```

## Task 3: Implement the standalone ACT wireless rollout runtime

**Files:** `tools/act_wireless_rollout.py`, `tests/tools/test_act_wireless_rollout.py`

- [ ] Implement CLI parsing for `--policy-path`, `--dataset-repo-id`, `--dataset-root`, `--top-camera`, `--wrist-camera`, `--image-width`, `--image-height`, `--rate` (default `30.0`), `--follower-calibration`, `--feedback-timeout`, `--recovery-timeout`, and `--dry-run`; require either a dataset repo ID or dataset root and reject nonpositive rate/dimensions.
- [ ] Load policy metadata with `LeRobotDatasetMetadata(repo_id, root=...)`, load the policy with `PreTrainedConfig.from_pretrained()` and `make_policy()`, and build LeRobot pre/post processors with `make_pre_post_processors(..., dataset_stats=metadata.stats)`.
- [ ] Construct two `OpenCVCameraConfig`/`OpenCVCamera` instances using the configured USB paths or indices, RGB output, and identical requested dimensions; connect them before entering the control loop and disconnect them in `finally`.
- [ ] Use `/joint_states` from the shared follower bridge as `observation.state` in the exact joint order. Read the latest frame from both cameras each cycle, call `build_observation()`, and use the existing `lerobot.utils.control_utils.predict_action()` path so ACT normalization and temporal aggregation follow LeRobot behavior.
- [ ] Define a small runtime object with `load()`, `step()`, and `close()` methods. `step()` must: read both frames, read current state, build the observation, infer one action, validate/coerce it, and publish one six-joint target unless `--dry-run` is active.
- [ ] Start with the follower measured pose and perform the existing current-pose session handshake before normal publication. Do not publish policy output until the follower status is active with all six response bits present.
- [ ] Publish at the configured rate without waiting for one ACK per action. Drain ROS callbacks each cycle and stop publishing on stale state, stale status, camera error, policy error, non-finite action, wrong action dimension, or follower `HOLDING_TIMEOUT`/`BUS_FAULT`.
- [ ] On recovery, require fresh follower feedback and a new current-pose handshake before resuming; never replay a previously queued action. Do not add a host-side `limit_step` or other smoothing layer.
- [ ] In `--dry-run`, still validate both camera frames, state shape, policy output shape, preprocessing, and rate timing, but never create or publish a ROS command. Print the validated feature keys and action dimension once at startup.
- [ ] Keep hardware access isolated behind injected camera, policy, clock, and publisher objects so tests do not require ROS hardware or cameras.

### RED verification

- [ ] Add tests with fake top/wrist cameras returning fixed `H x W x 3` frames, a fake policy returning a `(1, 6)` action, a fake state source, and a fake publisher. Cover: correct feature keys, policy action squeezing, one-cycle command publication, dry-run zero publications, camera failure stopping publication, non-finite action stopping publication, and stale follower state stopping publication.
- [ ] Add a CLI test that rejects missing dataset selection and accepts the documented dry-run arguments.
- [ ] Run:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_act_wireless_rollout.py
  ```

- [ ] Confirm the tests fail because `tools/act_wireless_rollout.py` does not yet exist.

### GREEN implementation and verification

- [ ] Implement the runtime using the existing LeRobot policy factory, processor factory, OpenCV camera APIs, control-loop timing, and shared wireless bridge.
- [ ] Re-run the focused rollout tests and confirm dry-run has zero calls to the fake publisher.
- [ ] Run `py_compile` on `tools/act_wireless_rollout.py` and the imported adapter/bridge modules.
- [ ] Commit exactly this runtime and its tests with:

  ```bash
  git add tools/act_wireless_rollout.py tests/tools/test_act_wireless_rollout.py
  git commit -m "feat: add ACT wireless rollout runtime"
  ```

## Task 4: Document wired ACT training and wireless deployment

**Files:** `docs/act_wireless_deployment.md`, `tests/tools/test_act_wireless_docs.py`, `README.md`

- [ ] Write the guide for this repository’s actual workflow: record demonstrations with wired LeRobot leader/follower and two USB cameras; train ACT from that dataset; run the policy on the host; send only validated joint targets over the existing wireless follower protocol.
- [ ] Document camera mapping (`top` and `wrist`), identical camera order/resolution between recording and deployment, joint order, task text, policy/dataset metadata, and the `--dry-run` smoke check.
- [ ] Document the difference between wired training and wireless execution: ACT inference is on the host, XIAO remains the low-level safety/servo controller, and the firmware limiter is intentionally retained.
- [ ] Include concrete command templates with placeholders only for repository paths, dataset repo ID, policy path, and camera device paths. Do not include Wi-Fi SSIDs, passwords, IP credentials, or `wifi_config.h` contents.
- [ ] Include an operator safety checklist for the first short real test and explicitly label it as hardware validation requiring live observation.
- [ ] Add one README link to the guide.
- [ ] Add documentation tests that assert the guide contains both required camera keys, `/joint_states`, `/joint_command`, `--dry-run`, the retained firmware safety statement, and no credential filenames/content.

### RED verification

- [ ] Add the documentation test before creating the guide and README link.
- [ ] Run:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q tests/tools/test_act_wireless_docs.py
  ```

- [ ] Confirm the test fails because the guide and link are absent.

### GREEN implementation and verification

- [ ] Create the guide and README link using the exact CLI and feature names implemented in Task 3.
- [ ] Re-run the documentation test and scan the diff for `wifi_config.h`, password-like values, and dataset/checkpoint files.
- [ ] Commit exactly the guide, documentation test, and README link with:

  ```bash
  git add docs/act_wireless_deployment.md tests/tools/test_act_wireless_docs.py README.md
  git commit -m "docs: explain wired ACT training and wireless rollout"
  ```

## Task 5: Run complete software verification and prepare the hardware gate

**Files:** no new source files; only test output and Git state are inspected.

- [ ] Run the complete focused suite:

  ```bash
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/linao/miniforge3/envs/lerobot_so101/bin/python -m pytest -q \
    tests/tools/test_act_adapter.py \
    tests/tools/test_follower_bridge.py \
    tests/tools/test_act_wireless_rollout.py \
    tests/tools/test_act_wireless_docs.py \
    tests/processor/test_policy_robot_bridge.py \
    tests/tools/test_wireless_launcher.py \
    tests/tools/test_firmware_status_contract.py
  ```

- [ ] Run syntax checks:

  ```bash
  /home/linao/miniforge3/envs/lerobot_so101/bin/python -m py_compile \
    tools/soarm_wireless/act_adapter.py \
    tools/soarm_wireless/follower_bridge.py \
    tools/act_wireless_rollout.py \
    tools/wireless_teleoperate.py
  ```

- [ ] Run `git diff --check main...HEAD` and `git status --short --branch`.
- [ ] Verify the branch diff contains no firmware changes, no Wi-Fi configuration, no credentials, no datasets, and no policy checkpoint binaries.
- [ ] Run a software-only dry-run using fake cameras/policy from the test suite and record that it publishes zero ROS commands.
- [ ] Stop here for operator confirmation before any real actuator test. The hardware gate requires both arms in safe supported poses, clear workspace, immediate power disconnect, the correct fixed wireless follower, and an observed short low-risk motion. Only after the operator supplies live observations may hardware evidence be recorded.
- [ ] Commit no empty or verification-only commit; the final state is represented by the five focused commits above.

## Final handoff criteria

- [ ] The branch contains the pure adapter, shared follower bridge, standalone ACT rollout, tests, and guide.
- [ ] The existing wired human teleoperation path still passes its focused tests and no longer applies host-side per-step smoothing.
- [ ] The XIAO firmware limiter and safety checks remain unchanged.
- [ ] The dry-run path validates both camera observations and six-joint actions without publishing commands.
- [ ] The user receives the branch name, commit list, test command, dry-run command, and a clear statement that no real-hardware success is claimed until observed evidence is supplied.
