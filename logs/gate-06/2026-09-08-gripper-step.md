# Gate 06 evidence — single-joint gripper step

- Date: 2026-09-08
- Firmware commit: `68ad76b`
- Gate 6 validator commit: `6ad27c2`
- Physical operator: linao
- Power arrangement: follower servo power connected; follower mechanically supported; workspace clear; operator ready to remove servo power
- Validator evidence: `logs/gate-06/gate6-20260908-175300.json`

## Automated result

The validator completed successfully and recorded a fresh session:

```text
Gate 6 PASS; evidence: logs/gate-06/gate6-20260908-175300.json
```

- Session ID: `1708662757`
- Handshake sequences: `1` through `2`
- Movement sequence: `3`
- Commanded joint: `gripper`
- Commanded delta: `+0.10 rad`
- Measured gripper delta: `+0.076699 rad`
- Maximum non-gripper measured delta: `0.009204 rad`
- Final response mask: `63` (`0x3f`)
- Final state: `ACTIVE`
- Final rejection reason: `NONE` (`0`)
- Read/write errors: `0` / `0`
- Acknowledgment latency: `60.96 ms`

The measured gripper displacement is within the validator's `±0.03 rad`
completion tolerance. The five non-gripper joints stayed within the same
tolerance.

## Physical observation

The operator confirmed that only the gripper moved in the positive direction;
the other five joints did not move. No stop condition was observed.

Result: PASS for Gate 06.
