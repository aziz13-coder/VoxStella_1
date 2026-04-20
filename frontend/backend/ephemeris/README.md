Swiss Ephemeris asteroid data bundled for Astro Clock.

This directory is source-backed so `frontend/scripts/prepare-backend.js` copies it
into `frontend/backend`, and `backend/build_backend.py` embeds it into the
packaged backend executable.

Included:

- `sweph/seas_*.se1` for the major asteroid bands used by Ceres, Pallas, Juno, and Vesta
- `sweph/ast0/se00026s.se1` for Proserpina
- `sweph/seleapsec.txt`

Source on the current build machine:

- `C:\Program Files (x86)\Galaxy\SwisEph`
