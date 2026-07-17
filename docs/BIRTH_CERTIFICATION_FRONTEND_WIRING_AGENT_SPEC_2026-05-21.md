# Birth Certification Frontend Wiring Agent Spec

Date: 2026-05-21

## Goal

Create and wire a frontend Birth Certification / Birth-Time Review workflow in AstroClock.

The backend/API foundation already exists. The frontend task is to add a user-facing modal/drawer that collects birth data and rectification events, calls the certification endpoint, and renders the candidate-time results clearly.

Do not expose internal source names in user-facing UI text. User-facing labels should use names like:

- `Birth Certification`
- `Birth-Time Review`
- `Rectification Review`
- `Certification Review`

Do not claim astrology proves legal guilt, innocence, traits, or factual life outcomes. The UI must frame this as a chart-time quality and model-review workflow.

## Files To Inspect First

Backend/API contract:

- `C:\Users\sabaa\Downloads\codexhorary\backend\birth_certification.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\astro_clock_api.py`
- `C:\Users\sabaa\Downloads\codexhorary\backend\test_birth_certification.py`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\backend\birth_certification.py`

Frontend integration points:

- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\TraitProfileModal.jsx`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\Directional3DModal.jsx`
- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\CompassTile.jsx`

Research/reference docs:

- `C:\Users\sabaa\Downloads\codexhorary\docs\BIRTH_TIME_CERTIFICATION_RECTIFICATION_MODEL_2026-05-21.md`
- `C:\Program Files (x86)\Galaxy\docs\research\zadorov_birth_certification_status.md`

## Existing Backend Contract

Endpoint:

```text
POST /api/astro-clock/certification/rectify
```

Frontend helper already added:

```js
AstroClockAPI.rectifyBirthTime(payload)
```

Location:

```text
C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\api.mjs
```

Request timeout is already set to 300000 ms because full-day scans can take time.

## Request Payload

Minimal payload:

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
  "include_series": true,
  "instruments": [
    {"id": "transit", "weight": 1},
    {"id": "secondary_progression", "weight": 1},
    {"id": "solar_arc", "weight": 0.9}
  ],
  "events": [
    {
      "label": "Arrest / detention marker",
      "timestamp": "2006-12-12T12:00:00+02:00",
      "latitude": 32.9907,
      "longitude": 35.6899,
      "timezone": "Asia/Jerusalem",
      "precision": 4,
      "theme": "legal confinement",
      "weight": 1,
      "source_note": "Day known, exact clock time unknown"
    }
  ]
}
```

Required birth fields:

- `date`
- `latitude`
- `longitude`
- `timezone`

Recommended birth fields:

- `location`
- `source_time_status`

Search fields:

- `search.start_time`: local birth-date search start, default `00:00`
- `search.end_time`: local birth-date search end, default `23:59`
- Backend enforces max 24 hours.

Event fields:

- `label`: user-visible event label.
- `timestamp`: ISO datetime. Include offset when known.
- `latitude` and `longitude`: event place coordinates.
- `timezone`: event timezone name if timestamp has no offset.
- `precision`: reference-compatible precision code.
- `theme`: optional grouping label; helps certification quality estimate.
- `weight`: optional numeric event weight.
- `source_note`: optional source/reliability note.

Precision codes:

- `0`: skip event
- `1`: exact
- `2`: minutes
- `3`: hours
- `4`: days
- `5`: weeks
- `6`: months

Instrument ids:

- `transit`
- `secondary_progression`
- `solar_arc`

## Response Shape

Successful response wrapper:

```json
{
  "success": true,
  "data": {
    "model": "birth_time_certification_rectification",
    "algorithm": "minute_scan_event_instrument_aspect_weights_v1",
    "meta": {},
    "events": [],
    "instruments": [],
    "top_candidates": [],
    "periods": [],
    "certification": {},
    "series": []
  }
}
```

Use `data.certification` for the status banner:

- `status`: `certified_source`, `rectified_candidate`, `unresolved_rectification`, or `insufficient_data`
- `confidence`: `high`, `medium`, `low`, or `none`
- `reason`: readable explanation
- `candidate`: best candidate row summary when available
- `data_quality`: event quality counts

Use `data.top_candidates` for the ranked candidate table:

- `rank`
- `timestamp`
- `favorable`
- `tense`
- `strength`
- `dominant_curve`
- `raw_plus`
- `raw_minus`
- `hit_count`
- `event_hits`

Use `data.periods` for thresholded windows:

- `rank`
- `start`
- `end`
- `peak_favorable`
- `peak_tense`
- `peak_strength`
- `dominant_curve`
- `duration_minutes`

Use `data.series` for the histogram:

- `timestamp`
- `favorable`
- `tense`
- `strength`
- `dominant_curve`

If the user disables full-series output, render the top table and periods only.

## UI Integration Plan

Create a new component:

```text
C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\BirthCertificationModal.jsx
```

Wire it from:

```text
C:\Users\sabaa\Downloads\codexhorary\frontend\src\features\astroclock\AstroClock.jsx
```

Follow the existing modal patterns:

- `TraitProfileModal.jsx` for snap/current chart source selection and API loading state.
- `Directional3DModal.jsx` for modal shell, close button, loading/error/empty state, controls, and tables.
- AstroClock feature action handlers around `handleOpenTraitProfile`, `handleOpenElection`, and related close handlers for premium gating and realtime pause/resume.

Recommended AstroClock changes:

- Add import:
  `import BirthCertificationModal from './BirthCertificationModal.jsx';`
- Add state near other modal flags:
  `const [showBirthCertification, setShowBirthCertification] = useState(false);`
- Add open handler using existing premium gate:
  - if `shouldRedirectToUpgrade()` then `redirectToPremiumUpgrade(...)`
  - otherwise pause realtime with `pauseRealtimeForFeature()`
  - then set `showBirthCertification` true
- Add close handler:
  - set false
  - call `resumeRealtimeAfterFeature()`
- Add a feature rail button beside other AstroClock feature buttons.
- Mount modal near the other modal mounts and pass current chart context, snaps, active snap id, loading snaps, loaded flag, and refresh callback.

Suggested props for `BirthCertificationModal`:

```js
{
  open,
  onClose,
  mode,
  manualIso,
  manualLocation,
  timezone,
  latitude,
  longitude,
  houseSystem,
  chartSnapshot,
  snaps,
  activeSnapId,
  loadingSnaps,
  snapsLoaded,
  onRefreshSnaps
}
```

## Modal UX Requirements

Top-level sections:

- Birth data
- Search interval
- Life events
- Instruments and scoring
- Results

Birth data fields:

- Date
- Location label
- Latitude
- Longitude
- Timezone
- Source time status

Source time status options:

- `unknown`
- `approximate`
- `rectified_candidate`
- `certificate`
- `family_exact`
- `certified`

Search fields:

- Start time, default `00:00`
- End time, default `23:59`
- House system, default from AstroClock `houseSystem`
- Orb, default `1`
- Level threshold, default `67`
- Include full series checkbox, default `true`

Event editor:

- Add/remove rows.
- Label
- ISO timestamp with offset
- Location label
- Latitude
- Longitude
- Timezone
- Precision selector
- Theme
- Weight
- Source note

Quality warnings:

- Warn if fewer than 3 events.
- Warn if all events share the same theme.
- Warn if events have only month-level precision.
- Warn if latitude/longitude is missing.
- Warn if birth time status is externally certified, because scan is optional and not needed for certification.

Results:

- Status banner from `certification.status`, `confidence`, and `reason`.
- Best candidate card from `certification.candidate`.
- Histogram of `series`: draw favorable and tense as two curves/bars. Favorable can be blue/green; tense can be amber/red. Avoid implying good/bad certainty.
- Top candidates table.
- Periods table.
- Event quality summary from `certification.data_quality`.
- Parity note from `meta.parity_note` in a small technical disclosure.

Do not block the first version on a perfect chart-like histogram. A simple responsive SVG or div-bar histogram is acceptable if it uses the `series` data faithfully.

## Context Helpers To Reuse

Use the snap/current-context logic from `TraitProfileModal.jsx`:

- `snapDashboard`
- `snapCoordinates`
- `getSnapMetaParts`
- `formatSnapLabel`
- `snapToTraitClockContext`
- `buildTraitClockContext`

Do not duplicate large helpers if practical. If extracting shared helpers is too risky because of the dirty worktree, copy the minimal local helper set into `BirthCertificationModal.jsx` for the first pass.

Use `AstroClockAPI.rectifyBirthTime(payload)` to run the scan.

## Suggested Payload Builder

Inside the modal, build:

```js
const payload = {
  birth: {
    date: birthDate,
    location: birthLocation || undefined,
    latitude: Number(birthLatitude),
    longitude: Number(birthLongitude),
    timezone: birthTimezone,
    source_time_status: sourceTimeStatus,
  },
  search: {
    start_time: searchStart,
    end_time: searchEnd,
  },
  house_system_code: houseSystem,
  orb_degrees: Number(orbDegrees || 1),
  level_percent: Number(levelPercent || 67),
  include_series: includeSeries,
  instruments: selectedInstruments.map((item) => ({
    id: item.id,
    weight: Number(item.weight || 1),
  })),
  events: eventRows.map((event) => ({
    label: event.label,
    timestamp: event.timestamp,
    latitude: Number(event.latitude),
    longitude: Number(event.longitude),
    timezone: event.timezone || undefined,
    precision: Number(event.precision || 1),
    theme: event.theme || undefined,
    weight: Number(event.weight || 1),
    source_note: event.sourceNote || undefined,
  })),
};
```

## Validation Rules

Frontend should validate before calling:

- Birth date is present.
- Birth latitude/longitude are finite numbers.
- Birth timezone is present.
- Search start and end are present.
- At least one event is present.
- Every enabled event has timestamp, latitude, longitude, and precision.
- End time is not before start time for same-day search.
- Full search range is no more than 24 hours.

Backend still validates, so display backend errors too.

## Testing Requirements

Add frontend tests if the existing test setup can support them without a large fixture:

- API helper sends `POST /api/astro-clock/certification/rectify`.
- Modal validates missing birth fields.
- Modal calls `AstroClockAPI.rectifyBirthTime` with a normalized payload.
- Modal renders status banner, candidate table, periods table, and histogram from a fake response.
- Close handler calls `onClose`.

Suggested files:

- `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\birthCertificationModal.test.jsx`
- Add API helper test to an existing API test file if that is the repo pattern.

Backend tests already exist:

```powershell
python -m pytest backend/test_birth_certification.py -q
```

Current focused backend result:

```text
6 passed
```

## Acceptance Criteria

- A user can open Birth Certification from AstroClock.
- The workflow can run against manually entered birth/event data.
- The workflow can optionally seed birth data from the active AstroClock context or selected snap.
- The backend request uses `AstroClockAPI.rectifyBirthTime`.
- Results render without requiring the user to inspect JSON.
- The UI clearly distinguishes externally certified source times from model-derived rectified candidates.
- No user-facing text names internal source software.
- No generated artifacts under `frontend/dist*`, `frontend/backend/build`, `win-unpacked`, `resources`, `node_modules`, or `venv` are edited.
