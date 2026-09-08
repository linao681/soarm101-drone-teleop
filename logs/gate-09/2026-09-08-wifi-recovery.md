# Gate 09 evidence — WiFi interruption and session recovery

- Date: 2026-09-08
- Firmware commit: `68ad76b`
- Launcher recovery-window commit: `262bd50`
- Physical operator: linao
- Power arrangement: follower servo power connected; follower mechanically supported; operator ready to remove servo power
- Metrics CSV: `logs/teleop_20260908_184248.csv`

## Recovery evidence

The PC WiFi was disconnected and restored on `wlp0s20f3`. The recorded
feedback gap was `3.229 s`. Before the interruption, the follower was in
`ACTIVE` with session `3904378998`; after the interruption it entered timeout
with the same session, then the bridge generated session `2734175475` and
completed a fresh handshake.

The bridge printed:

```text
Follower session recovered with a fresh near-current-pose handshake
```

Across the recorded run:

- `response_mask` remained `63` (`0x3f`)
- `reject_reason` remained `0`
- 232 samples were `ACTIVE`; the two `HOLDING_TIMEOUT` samples covered the
  interruption and the stale previous-session sample at startup
- Minimum RSSI was `-45 dBm`
- The measured six-joint pose before and after the interruption was unchanged
  in the saved CSV
- The operator confirmed no visible jump and no replay of the old target

The analyzer's `application_ratio` is not used as a Gate 9 criterion because
the CSV contains multiple sessions with independently reset sequence numbers.

Result: PASS for Gate 09.
