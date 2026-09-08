# Gate 08 evidence — timeout hold and near-current re-handshake

- Date: 2026-09-08
- Firmware commit: `68ad76b`
- Physical operator: linao
- Power arrangement: follower servo power connected; follower remained mechanically supported; operator ready to remove servo power

## Before stopping the bridge

```text
data: [1, 1, 827703013, 373, 373, 24, 63, 0, 4, 0, 0, 0, 0, -33]
```

The follower was `ACTIVE` with all six servos responding. The measured pose was:

```text
[0.1902136177, -1.8315730607, 1.5186409800,
 1.5508545766, 2.5939615123, -0.4832039482]
```

## After stopping the bridge

After the bridge was stopped and the follower was left without commands:

```text
data: [1, 2, 827703013, 596, 596, 18584, 63, 0, 5, 0, 0, 0, 0, -34]
```

The state changed to `HOLDING_TIMEOUT` with the same session ID and
`command_age_ms=18584`. The six-joint pose was exactly unchanged. The timeout
counter increased from `4` to `5`, as expected; response mask, rejection reason,
read errors, and write errors remained healthy.

## After restarting the bridge

```text
data: [1, 1, -524996089, 204, 204, 4, 63, 0, 5, 0, 0, 0, 0, -33]
```

The follower returned to `ACTIVE` with a new session ID, all six servos
responding, no rejection, and no bus errors. The operator confirmed that the
re-handshake produced no visible jump.

Result: PASS for Gate 08.
