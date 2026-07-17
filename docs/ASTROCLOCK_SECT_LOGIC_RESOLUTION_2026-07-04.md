# Astroclock Sect Logic Resolution - 2026-07-04

## Scope

Reviewed and resolved Sect logic issues in Astroclock backend/frontend source paths:

- `backend/sect.py`
- `frontend/backend/sect.py`
- `backend/house_influence.py`
- `frontend/backend/house_influence.py`
- `frontend/src/features/astroclock/AstroClock.jsx`
- `frontend/src/features/astroclock/traitProfileViewModel.mjs`

No packaged build artifacts were edited.

## Issues Resolved

1. Sect was derived primarily from `Sun.house`, so changing house systems could flip day/night classification.
   - Resolution: `compute_sect_info` now prefers Sun altitude from serialized chart data or computes it from UTC time, coordinates, and Sun ecliptic position. House number remains only a fallback.

2. Unknown Sun data silently defaulted to a day chart.
   - Resolution: unknown chart sect now stays `None`; downstream per-planet `in_sect` stays unknown instead of becoming false day/night evidence.

3. Nocturnal hayz hemisphere handling was chart-label based.
   - Resolution: sign polarity and hemisphere matching now follow each planet's assigned sect. Planets of the chart sect prefer above the horizon; contrary-sect planets prefer below.

4. `malefic_of_sect` received out-of-sect harshness keywords.
   - Resolution: the moderated malefic of sect keeps `malefic_of_sect` and `in_sect`; harsh `malefic_out_of_sect` keywords now attach only to Mars/Saturn rows that are actually out of sect.
   - Related source correction: Basic Analysis malefic sect phrasing now reads the per-planet `in_sect` flag instead of chart day/night alone.

5. Frontend displays coerced unknown sect states into Day/Night or out-of-sect labels.
   - Resolution: Astroclock summary, Sect panel, saved snaps, and trait profile labels now normalize `diurnal/day` and `nocturnal/night` explicitly and leave unknown values unset.

## Verification

Targeted checks added:

- `backend/test_sect.py`
- `frontend/backend/test_sect.py`
- `frontend/src/tests/traitProfileViewModel.test.mjs`

Commands run:

```powershell
python -m pytest backend/test_sect.py
python -m pytest frontend/backend/test_sect.py
npm --prefix frontend run test:ui -- traitProfileViewModel.test.mjs
```

All targeted checks passed after the fixes.
