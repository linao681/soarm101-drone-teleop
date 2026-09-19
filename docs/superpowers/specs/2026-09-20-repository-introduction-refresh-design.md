# Repository Introduction Refresh Design

## Goal

Update the repository homepage so it accurately presents the current project: a
SO-ARM101 teleoperation system that supports both a wireless leader and a
wireless follower, while retaining the wired-leader fallback path. The README
should help a new visitor understand the project and start the correct mode
without reading the upstream LeRobot documentation first.

## README Structure

The README will be rewritten as a project-first document with these sections:

1. Project title and a short Chinese summary.
2. Current capabilities, including wireless leader and follower operation,
   hotspot agent discovery, wired fallback, reconnect handling, metrics, and
   initial drone-mounted grasping experiments.
3. A concise control-path overview from leader arm through the Ubuntu bridge to
   the follower arm.
4. Repository layout for the bridge, launcher, follower firmware, leader
   firmware, calibration data, tests, and evidence logs.
5. Setup notes covering ROS 2, LeRobot, PlatformIO, 2.4 GHz Wi-Fi, calibration,
   and ignored local Wi-Fi configuration files.
6. Quick-start commands for wireless leader, wired leader, and check-only mode.
7. Firmware build and upload commands for the two XIAO ESP32-C3 projects.
8. Reliability and safety behavior, verified evidence, and explicit limitations.
9. Upstream LeRobot attribution and license information.

The generic upstream LeRobot tutorial content currently occupying most of the
README will be removed from the homepage. Attribution and links to the upstream
project will remain.

## Accuracy and Safety Constraints

- Do not include `wifi_config.h`, Wi-Fi passwords, tokens, or other credentials.
- Do not claim that the deferred ten-minute endurance test passed.
- Distinguish tested short-run behavior from planned or deferred validation.
- State that stopping the application leaves the follower holding its last
  commanded pose and that physical emergency stop means removing servo power.
- Explain that calibration files are hardware-specific and must be synchronized
  with the firmware after recalibration or controller/arm changes.
- Preserve the wired leader path as a supported fallback.

## GitHub Repository Description

Use this concise description:

> SO-ARM101 双无线主从臂遥操作与无人机搭载实验，基于 LeRobot、ROS 2、micro-ROS 和 XIAO ESP32-C3，支持热点 IP 自动发现、有线回退与断线安全恢复。

## Verification

- Check every documented command against the current launcher and firmware
  directory names.
- Run README link and secret-pattern checks.
- Confirm the GitHub description after updating it.
- Review the final Git diff to ensure unrelated local submission materials and
  credentials are not included.
