# ACT Wireless Deployment Design

Date: 2026-09-22  
Branch: `codex/act-wireless-deployment`

## Goal

Deploy an ACT policy trained with the existing wired SO-ARM101 LeRobot workflow to a fixed wireless SO-ARM101 follower.

The ACT policy runs on the host computer or Jetson. The follower XIAO remains the low-level ROS 2/micro-ROS actuator controller and receives commands on `/joint_command`.

## Scope

### Included

- A standalone `tools/act_wireless_rollout.py` entry point.
- Two ordinary USB/OpenCV cameras with stable feature names:
  - `observation.images.top`
  - `observation.images.wrist`
- Six-joint SO-ARM101 state input from `/joint_states`.
- ACT policy loading and preprocessing using the training dataset/policy metadata.
- Conversion of policy actions to the wireless follower command format.
- Reuse of the existing wireless session handshake, sequence numbers, feedback watchdog, and follower status checks.
- A dry-run mode that performs policy input and output validation without publishing servo commands.
- Unit and integration-style tests that do not require an attached arm.

### Not included

- Changes to XIAO firmware.
- Changes to Wi-Fi credentials or `wifi_config.h`.
- A new data-collection workflow. Wired `lerobot-record` remains the recommended way to create the ACT dataset.
- Autonomous drone flight control.
- Removal of the follower's firmware safety limits.

## Architecture

```text
top USB camera ─┐
                ├─> ACT observation ─> ACT policy ─> 6-joint action
wrist USB camera┘                                      │
wireless /joint_states ────────────────────────────────┘
                                                       │
                                                       ▼
                         wireless follower bridge
                         - action validation
                         - session handshake
                         - monotonically increasing sequence
                         - /joint_command publisher
                         - /follower_status watchdog
                                                       │
                                                       ▼
                                           follower XIAO + SO-ARM101
```

The existing wireless publisher and recovery behavior will be moved into a reusable module under `tools/soarm_wireless/`. The current human teleoperation entry point and the new ACT entry point will share that module so their protocol behavior cannot diverge.

## Runtime behavior

### Startup

1. Validate policy metadata, camera configuration, and the six expected joint names.
2. Wait for a valid `/joint_states` sample from the follower.
3. Create a fresh wireless session and perform the current-pose handshake.
4. Wait for the follower to report `ACTIVE` with all six servos available.
5. Begin ACT inference and command publishing.

The first policy target is checked for finite values and valid calibrated joint range. The host does not add a per-command `max_step_rad` smoothing limit in this branch. The XIAO firmware's existing velocity limiter, calibrated range checks, timeout hold, and bus-fault handling remain active.

### Control loop

- Default command rate: 30 Hz.
- Policy inference and command publishing are decoupled so publishing does not wait for an acknowledgement for every command.
- `/follower_status` is monitored asynchronously.
- The command contains the existing protocol session ID and monotonically increasing sequence number.
- Invalid, non-finite, or wrong-sized policy outputs are rejected locally and no command is published for that cycle.

### Failure behavior

- Camera failure: stop publishing and report the camera name.
- Policy inference failure: stop publishing and preserve the follower's last commanded pose.
- Invalid policy action: stop that command cycle and report the validation error.
- Stale `/joint_states` or follower status: stop publishing; the firmware then enters its existing hold-last-command state.
- Follower `HOLDING_TIMEOUT` or `BUS_FAULT`: do not replay an old action. Require fresh feedback and a new current-pose handshake before resuming.
- Ctrl+C: stop the host loop; the follower keeps its last commanded pose until its normal safety handling or power is removed.

## Inputs and action contract

The deployment configuration must match the wired training dataset:

- camera names: `top`, `wrist`;
- identical camera order and image dimensions;
- identical joint order:
  `shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`;
- identical action/state units and normalization metadata;
- identical task description semantics.

The adapter will use LeRobot's policy preprocessing and dataset statistics rather than introducing a second hand-written normalization scheme.

## CLI shape

The first implementation will expose the minimum controls needed for a safe deployment:

```text
--policy-path
--dataset-repo-id or --dataset-root
--top-camera
--wrist-camera
--image-width
--image-height
--rate (default 30)
--follower-calibration
--dry-run
```

The exact argument spelling will follow the existing project's argparse style and the installed LeRobot policy-loading APIs.

## Verification

Before any hardware test:

1. Unit tests cover action shape, finite-value, joint-order, range, sequence, and watchdog behavior.
2. A dry-run test loads a fake policy and two fake camera frames, verifies the two image keys and six-joint action shape, and confirms that no ROS command is published.
3. Existing wireless teleoperation tests continue to pass.
4. Python syntax and lint checks pass for all changed Python files.

Hardware validation is separate and must be observed by the operator. The first real test uses a mechanically supported follower, clear motion space, an immediately accessible power disconnect, and a short low-risk task. No hardware success will be claimed from dry-run or unit-test output alone.

