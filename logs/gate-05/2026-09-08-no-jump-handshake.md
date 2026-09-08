# Gate 05 evidence — supported first handshake

- Date: 2026-09-08
- Firmware commit: `68ad76b`
- Launcher commit: `e3d346e`
- Physical operator: linao
- Power arrangement: follower servo power connected; follower mechanically supported; operator available to remove servo power
- Metrics CSV: `logs/teleop_20260908_171548.csv`

## Startup evidence

```text
Leader calibration matched: /home/linao/so101_lerobot/cali/my_leader.json
Wireless follower feedback: [0.095, -1.85, 1.597, 1.509, 2.757, -0.549]
Follower armed at its measured pose without a jump
Initial synchronization complete (relative mapping)
Live teleoperation active; press Ctrl+C to stop
leader: [1.1, -99.6, 98.0, 51.3, 5.6, 3.7]  follower: [0.1, -1.85, 1.6, 1.51, 2.76, -0.55]
```

The physical operator reported that wireless teleoperation worked with no
visible problem. The initial feedback and first displayed follower position
were effectively unchanged at the shown precision, supporting the no-jump
observation.

## CSV summary

The saved run contains 1,774 feedback samples over 177.93 seconds at 9.97 Hz.
It recorded zero rejection samples and zero timeout samples. Minimum RSSI was
-60 dBm. This run included movement after the handshake, but it was not the
prescribed single-joint 0.10 rad Gate 06 procedure, so it is not credited as
Gate 06 or Gate 07 evidence.

The original CSV wrote `command_sequence=0` while `applied_sequence` advanced,
making its `commands_sent` and application-ratio summary invalid. The logging
defect was reproduced with a failing test and fixed separately in commit
`1acc38e`; it does not change the control command or firmware behavior.

Result: PASS for Gate 05 only. No visible jump was observed at the first
measured-pose handshake.
