# AstroClock Dispositor Logic

This note documents the resolved AstroClock dispositor contract.

## Source Paths

- Backend chain logic: `backend/astro_dispositors.py`
- Packaged backend source twin: `frontend/backend/astro_dispositors.py`
- Dashboard serialization: `backend/astro_clock_api.py` and `frontend/backend/astro_clock_api.py`
- Frontend display model: `frontend/src/features/astroclock/dispositorViewModel.mjs`

## Rules

- Dispositor chains use traditional domicile rulers:
  - Mars rules Aries and Scorpio.
  - Venus rules Taurus and Libra.
  - Mercury rules Gemini and Virgo.
  - Moon rules Cancer.
  - Sun rules Leo.
  - Jupiter rules Sagittarius and Pisces.
  - Saturn rules Capricorn and Aquarius.
- A final dispositor exists only when the chain terminates in a planet occupying its own domicile.
- Mutual reception is a terminal state, but it has no single final dispositor.
- Longer rulership loops are terminal cycles, but they also have no single final dispositor.
- `includeModern` may add Uranus, Neptune, and Pluto as chart bodies, but sign rulership for dispositor chains remains traditional.

## API Fields

Each dashboard `dispositors[planet]` entry includes:

- `dispositor`: immediate traditional sign ruler.
- `chain`: ordered planet path.
- `final_dispositor`: populated only for a genuine final dispositor.
- `has_final_dispositor`: true only when `final_dispositor` is genuine.
- `terminal_type`: one of `domicile`, `mutual_reception`, `cycle`, or `unknown`.
- `mutual_reception` and `reception_partner`: populated for strict two-planet mutual reception.
- `cycle`: populated for mutual receptions and longer cycles.

Research final-dispositor filters use the same backend helper as the dashboard. Mutual receptions and cycles do not match final-dispositor filters; use reception filters for mutual-reception analysis.
