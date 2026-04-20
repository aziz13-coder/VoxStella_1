# Mundane Long-Range Async Scan Mode

Date: 2026-04-12

## Reason

The normal `spatiotemporal_scan` mode is intentionally bounded for interactive use:

- `24` time slices
- `160` evaluated cells

That keeps short-window scans responsive, but it blocks legitimate longer-window research.

## Design

Do not raise the global scan caps.

Instead, add a separate mode:

- `long_range_async_scan`

This keeps the fast interactive mode intact and creates a second lane for longer windows.

## Runtime Policy

`spatiotemporal_scan`

- use for short investigative windows
- remains:
  - `24` time slices
  - `160` evaluated cells

`long_range_async_scan`

- use for broader research windows
- async-only by policy
- defaults:
  - `12h` time step when omitted
  - `6` candidates when omitted
- caps:
  - `180` time slices
  - `1200` evaluated cells
  - `12` maximum candidates

## UI Policy

The scan workspace should:

- expose `Long-Range Async Scan` as a distinct mode
- show per-mode limits, not one global slice limit
- keep the same progress polling flow already used by async scan start/result
- estimate workload inline:
  - time slices
  - evaluated cells

## API Policy

The blocking endpoint should not pretend to support the long-range mode.

- `/api/astro-clock/mundane/scan/run`
  - reject `long_range_async_scan`
- `/api/astro-clock/mundane/scan/start`
  - allow `long_range_async_scan`

## Scope

This is a scan-orchestration change only.

It does not:

- change mundane doctrine
- change domain scoring
- change short-window scan limits

## Practical Result

The user now has two clear scan lanes:

- short-window interactive scan
- long-range async research scan
