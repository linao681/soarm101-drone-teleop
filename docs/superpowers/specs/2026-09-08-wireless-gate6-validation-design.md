# Wireless Gate 6 Validation Design

## Purpose

Provide a repeatable Task 8 Gate 6 test that moves only the wireless follower
gripper by exactly `+0.10 rad` from its measured starting position. The test
must verify command acknowledgment and physical motion direction without using
the USB leader or allowing unrelated joints to move.

## Scope

Add one host-side validation command under `tools/`. Reuse the existing
`/joint_states`, `/joint_command`, `/follower_status`, command-ID protocol, and
follower state machine. Do not change firmware, calibration, leader mapping,
normal teleoperation behavior, or WiFi configuration.

## Safety Preconditions

Before publishing any command, the validator must receive fresh joint state and
follower status samples and require all of the following:

- exactly six expected joint names and finite measured positions;
- `response_mask == 0x3f`;
- follower state is `WAITING_HANDSHAKE` or `HOLDING_TIMEOUT`;
- rejection reason is `NONE`;
- no increase in bus read errors or write errors during the preflight window;
- requested gripper target remains inside the active follower calibration
  range.

The operator must mechanically support the follower, clear the workspace, and
remain ready to remove servo power. The script prints these requirements and
requires an explicit typed confirmation before motion unless `--yes` is passed
for an already supervised test.

## Command Sequence

The validator creates a fresh random session ID and starts at sequence 1.

1. Capture the latest measured six-joint pose as `start`.
2. Publish `start` unchanged until the follower reports `ACTIVE` for the same
   session and acknowledges the handshake sequence.
3. Create `target = start`, changing only the gripper element by `+0.10 rad`.
4. Publish the exact target at 20 Hz for at most 3 seconds.
5. Require same-session acknowledgment, `ACTIVE`, `response_mask == 0x3f`, no
   rejection, and no increase in read/write error counters.
6. Stop publishing after the measured gripper has moved in the positive
   direction and reached `0.10 rad` within a `0.03 rad` tolerance.
7. Exit without commanding a return movement. The firmware timeout behavior
   holds the final applied target; the operator may then remove servo power.

The other five target values remain equal to their captured starting values for
every command, and their measured displacement must remain within `0.03 rad`.
Any failed prerequisite or runtime invariant stops the test immediately and
prevents further commands.

## Evidence

Write one timestamped JSON evidence file under `logs/gate-06/`. It records:

- date, current Git commit, session ID, and tested joint;
- starting pose and requested target;
- first and final status arrays;
- handshake and movement sequence numbers;
- measured final pose and per-joint deltas;
- acknowledgment latency;
- starting and final read/write error counters;
- pass/fail result and a specific failure reason.

A technical pass requires all automated checks. The test matrix is marked
passed only after the physical operator separately confirms that the gripper
moved in the expected direction and no other joint visibly moved.

## Error Handling

ROS topic timeout, malformed status, stale feedback, wrong joint names,
out-of-range target, session mismatch, stale acknowledgment, nonzero rejection,
bus-mask loss, or increased bus errors causes a nonzero exit. The evidence file
is still written with the last available measurements and failure reason.
Unexpected exceptions also produce a failed evidence record before ROS cleanup
when possible.

## Testing

Unit tests use a transport-independent Gate 6 controller/helper layer with
synthetic joint states and status arrays. Tests cover:

- only the gripper target changes by `+0.10 rad`;
- an out-of-range target is rejected before publishing;
- the unchanged-pose handshake must be acknowledged first;
- wrong session, rejection, mask loss, and bus-error increases fail;
- positive measured motion within tolerance passes;
- motion in the wrong direction or movement of another joint fails;
- evidence is written on both pass and failure paths.

After unit tests pass, run the reliability-related pytest and Ruff checks. This
host-only addition requires no firmware build or upload.
