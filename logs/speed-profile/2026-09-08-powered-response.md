# Summer wireless speed profile powered-response evidence

- Test date: 2026-09-08
- Operator: linao
- Firmware commit: `1067dff` (`feat: restore summer wireless response speed`)
- Evidence commit before this run: `297a4b7` (`test: record summer speed firmware smoke check`)
- Power and safety arrangement: follower mechanically supported; workspace clear; servo power connected for the run; operator could disconnect power immediately; both arms in a safe posture.
- Exact run CSV: `/home/linao/so101_lerobot/logs/teleop_20260908_193759.csv`

## Operator observations

- Startup reported matching leader calibration and a measured-pose, no-jump follower handshake.
- The operator reported the six-joint directions were correct and the response was acceptable.
- After `Ctrl+C`, the launcher reported that the follower held its last commanded pose; the operator confirmed the stop/hold behavior.
- No operator report of a jump, wrong direction, sustained oscillation, bus fault, abnormal sound, or abnormal temperature was provided in the run report.
- Voltage and temperature were not separately captured as evidence in this run; those conditions remain unverified.

## CSV analysis

Command:

```text
/home/linao/miniforge3/envs/lerobot_so101/bin/python tools/analyze_wireless_log.py /home/linao/so101_lerobot/logs/teleop_20260908_193759.csv
```

Observed values:

- Run duration: `143.7635453519979 s`
- Commands sent/applied: `1438 / 1437`
- Application ratio: `0.9993045897079277`
- Feedback samples/rate: `1438 / 10.002535736574446 Hz`
- `rejections_total`: `0`
- `timeout_count`: `0`
- `response_mask`: `63` for every CSV row
- Minimum RSSI: `-53 dBm`
- ACK latency: p50 `65.26047399893287 ms`, p95 `66.62888600112638 ms`, p99 `98.4069680016546 ms`
- Maximum joint error: `0.7592840904592735 rad`
- Aggregate joint RMSE: `0.059107182902839055 rad`

This is real-arm evidence for the run above. It does not claim the voltage/temperature portion of Gate 7 passed because those measurements were not saved.
