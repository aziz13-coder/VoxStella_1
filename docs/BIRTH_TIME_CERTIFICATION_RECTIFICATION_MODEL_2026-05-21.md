# Birth-Time Certification / Rectification Model

Date: 2026-05-21

## Purpose

This note documents the certification/rectification workflow implemented in the app after reverse-engineering the reference Rectificator behavior.

The app feature is a birth-time review tool. It does not certify a chart by itself unless the user supplies an external reliable birth-time source. Without such a source, the model can only produce a `rectified_candidate` or `unresolved_rectification`.

## Reference Workflow

Source evidence:

- Decompiled main loop: `C:\Program Files (x86)\Galaxy\temp\ilspy_rectificator\GalaxyRectificator\Obj4Rectificator.cs`
- GUI full-day Zadorov export: `C:\Program Files (x86)\Galaxy\BoxOut\rectdetail_19780425_19780425_19780425000000_20260520205614.rtf`
- Extracted text export: `C:\Program Files (x86)\Galaxy\temp\zadorov_rectdetail_20260520205614.txt`
- Result screenshot: `C:\Program Files (x86)\Galaxy\temp\rectificator_zadorov_calc_wait120.png`

Observed workflow:

1. The first row in the chart list is the natal chart being rectified.
2. Later rows are dated life events.
3. The work panel loads five weighted blocks: events, instruments, thematic object groups, aspects, and objects.
4. The calculation scans a search period minute by minute. The reference UI rejects periods longer than 24 hours.
5. For every candidate minute, the natal chart is recomputed.
6. For every selected event and selected instrument, the dynamic/event chart is computed.
7. Event precision gates usable dynamic points. Exact events use all points; lower precision events shift the event time and only keep points that move no more than 1 degree. For day/month-level precision, fast points are effectively removed.
8. Dynamic-to-natal aspects are collected only when the aspect, dynamic object, and thematic eligibility pass.
9. Positive coefficients accumulate into a favorable curve. Negative coefficients accumulate into an intensity/tense curve.
10. Raw curves are normalized to 0-100 using the reference max/min-floor formula.
11. Period extraction uses the UI `Level (%)` threshold. A period is emitted when either favorable or intensity is at or above the threshold.

Important source lines:

- `Obj4Rectificator.cs:730-749`: max 24-hour period and minute row count.
- `Obj4Rectificator.cs:774-787`: scan every candidate minute, update natal chart, loop selected events.
- `Obj4Rectificator.cs:794-798`: instrument weights split planet-vs-angle contribution.
- `Obj4Rectificator.cs:802-878`: event precision handling and dynamic-point usability gate.
- `Obj4Rectificator.cs:880-905`: cross-aspect filtering and plus/minus accumulation.
- `Obj4Rectificator.cs:928-941`: normalization formula.
- `Obj4Rectificator.cs:1327-1361`: full-table export.
- `Obj4Rectificator.cs:1364-1433`: thresholded period export.

## Implemented In App

Backend source:

- `C:\Users\sabaa\Downloads\codexhorary\backend\birth_certification.py`
- Mirrored for packaged backend source: `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\birth_certification.py`
- API route: `POST /api/astro-clock/certification/rectify` in `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py`
- Frontend API helper: `api.rectifyBirthTime(...)` in `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`
- Build hidden import: `birth_certification` in both backend build scripts.

The implementation includes:

- Minute-by-minute scan over a maximum 24-hour birth-time interval.
- Input parsing for birth date/location/timezone and event timestamp/location/timezone.
- Event precision codes compatible with the reference behavior:
  - `0`: skip
  - `1`: exact
  - `2`: minutes, shift by 15 minutes
  - `3`: hours, shift by 3 hours
  - `4`: days, shift by 3 days
  - `5`: weeks, shift by 21 days
  - `6`: months, shift by about 90 days
- Swiss Ephemeris calculation of planets and angles.
- Instrument layer support:
  - transits
  - secondary progressions
  - solar arc directions
- Dynamic-point precision filtering by 1 degree.
- Fast-point removal for coarse day/month events.
- Aspect families: conjunction, sextile, square, trine, opposition.
- Favorable and tense raw accumulators.
- Reference-style normalization to 0-100.
- Threshold period extraction using `level_percent`.
- Certification status classification:
  - `certified_source`: only when birth time is externally marked as certified/source-backed.
  - `rectified_candidate`: strong isolated peak plus enough relatively precise independent events.
  - `unresolved_rectification`: no stable enough result.
  - `insufficient_data`: no scan rows.

## API Payload

Minimal request:

```json
{
  "birth": {
    "date": "1978-04-25",
    "location": "Simferopol",
    "latitude": 44.9521,
    "longitude": 34.1024,
    "timezone": "Europe/Simferopol",
    "source_time_status": "unknown"
  },
  "search": {
    "start_time": "00:00",
    "end_time": "23:59"
  },
  "house_system_code": "T",
  "orb_degrees": 1,
  "level_percent": 67,
  "events": [
    {
      "label": "Arrest / detention marker",
      "timestamp": "2006-12-12T12:00:00+02:00",
      "latitude": 32.9907,
      "longitude": 35.6899,
      "timezone": "Asia/Jerusalem",
      "precision": 4,
      "theme": "legal confinement",
      "weight": 1
    }
  ],
  "instruments": [
    {"id": "transit", "weight": 1},
    {"id": "secondary_progression", "weight": 1},
    {"id": "solar_arc", "weight": 0.9}
  ],
  "include_series": true
}
```

Response shape:

- `meta`: scan settings, row count, normalization amplitude, parity note.
- `events`: normalized event input list.
- `instruments`: normalized instrument list.
- `top_candidates`: best rows ranked by strongest favorable/tense curve. Each row includes `rank`, `timestamp`, `favorable`, `tense`, `strength`, `dominant_curve`, `raw_plus`, `raw_minus`, `hit_count`, and `event_hits`.
- `periods`: thresholded contiguous windows. Each period includes `rank`, `start`, `end`, `peak_favorable`, `peak_tense`, `peak_strength`, `dominant_curve`, and `duration_minutes`.
- `certification`: final status and reason.
- `series`: all minute rows when `include_series=true`.

## Zadorov GUI Evidence

The real reference GUI full-day run used:

- Birth scan date: `25.04.1978 00:00:00 - 25.04.1978 23:59:00`
- Birth location: Simferopol, `44 57 07 N`, `034 06 09 E`
- House system: topocentric
- Events loaded:
  - provisional marriage midpoint
  - arrest/detention marker
  - original district conviction
  - release to house arrest / arrival Katzrin
  - retrial acquittal announcement

Top favorable rows from the exported full table:

| Local birth time | Favorable | Intensity |
| --- | ---: | ---: |
| 05:59 | 100 | 50 |
| 06:01 | 100 | 47 |
| 06:00 | 99 | 49 |
| 05:56 | 99 | 46 |
| 10:31 | 99 | 42 |

This supersedes the earlier runtime-only probe. The GUI run proves the reference workflow can produce a strong local cluster around 05:56-06:01 for this specific event set, but it still does not certify the birth time because the marriage date is provisional and several legal events are day-level or externally clustered.

## Parity Limits

Implemented parity:

- 24-hour max scan.
- Candidate minute loop.
- Event precision offset/gating.
- Dynamic-to-natal aspect accumulation.
- Favorable vs tense curve separation.
- Reference normalization and threshold period extraction.

Known gaps:

- The exact proprietary reference tables for all 48 objects are not fully embedded.
- The exact thematic object-group table is not fully embedded.
- The exact aspect coefficient table is approximated and configurable.
- The exact instrument table is partially implemented. The app includes transits, secondary progressions, and solar arc directions, but not every reference progression/profection/primary-direction variant.
- The reference engine has more chart objects than the app default: house cusps, lots, nodes, and possibly custom points. The app currently uses planets plus Asc/MC/Dsc/IC.
- Primary directions and tertiary/minor progression variants remain future work.
- The reference GUI can export time-points after the user populates that list; the app endpoint currently exports ranked candidates and periods only.

## Implementation Guidance For Next UI Pass

Add a dedicated AstroClock modal or drawer named `Birth-Time Review` or `Certification Review`.

Required inputs:

- Birth date.
- Birth location, latitude, longitude, timezone.
- Search start/end time.
- Events table with label, timestamp, location, timezone, precision code, theme, weight, source note.
- Instrument toggles.
- Level threshold.
- Include/exclude full series.

Required result views:

- Top candidates table.
- Histogram of favorable and tense curves.
- Thresholded periods.
- Event contribution summary.
- Certification status and reason.
- Explicit warning when status is `unresolved_rectification`.

User-facing wording should avoid claiming that rectification equals proof. Use `certified` only for externally sourced times. Use `rectified candidate` for model-derived times.

## Verification

Focused backend tests:

```powershell
python -m pytest backend/test_birth_certification.py -q
```

Current result:

```text
6 passed
```

Smoke scan:

- A 6-minute real Swiss Ephemeris scan over Zadorov sample data completed successfully.
- Result returned a ranked top candidate and `unresolved_rectification`, as expected for one coarse event.
