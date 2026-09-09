# Powered wireless-leader validation — 2026-09-09

## Test arrangement

- Leader XIAO identity: `E4:B3:23:C4:7D:38`.
- The leader was mechanically supported and in a safe pose; its motion space was clear and its servo power could be disconnected immediately.
- Follower servo power remained disconnected.
- The operator confirmed that the leader XIAO USB 5 V and external 5 V were not simultaneously connected, or that their power isolation was confirmed.

## Read-only machine evidence

- Capture duration: 30 seconds; result: `PASS`.
- Protocol/state: version 1, boot session `527852859`, `READY`.
- Response/model/torque-off masks: `63` / `63` / `63`.
- Calibration CRC: `0x9d36c031`, matching the selected leader calibration.
- Samples: 1,497 at 49.87 Hz; read-error delta: 0; torque-error delta: 0; RSSI: -40 dBm.
- Every raw channel changed during the capture. Details are retained in the adjacent JSON evidence.
- One stale/duplicate raw sample was rejected by the read-only validator and recorded in JSON; it did not refresh control state or indicate a hardware health failure.

## Operator observations

- Each of the six leader joints was moved one at a time through a small safe range.
- All six normalized directions matched the existing wired leader.
- All joints remained freely movable: no servo held or drove a joint.
- No abnormal sound, heat, or other anomaly was observed.
- Voltage and temperature values were not independently recorded during this read-only capture.
