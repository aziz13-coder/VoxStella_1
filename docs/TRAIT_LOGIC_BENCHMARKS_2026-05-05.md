# Trait Logic Benchmarks - Public Figure Calibration

Date: 2026-05-05

## Purpose

This benchmark is a logic check for Trait Profile. It is not a claim that a chart proves a biography. It checks whether the trait engine can surface broad, publicly documented life themes for charts with high-quality birth data, and whether rule changes are tied to actual computed signals instead of UI decoration.

The benchmark exercises the same backend endpoint used by the frontend:

`GET /api/astro-clock/traits/profile`

## Benchmark Cases

Birth data is encoded as UTC instants derived from the cited local birth records. This avoids historic timezone drift in the local timezone database.

| Case | Calibration Theme | Birth Data Source | Biography Sources |
| --- | --- | --- | --- |
| Albert Einstein | scientific originality | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Einstein%2C_Albert | Nobel facts/biography: https://www.nobelprize.org/prizes/physics/1921/einstein/facts/ and https://www.nobelprize.org/prizes/physics/1921/einstein/biographical/ |
| Marie Curie | scientific research, discipline, resilience | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Curie%2C_Marie | Nobel facts/biography: https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/facts/ and https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/biographical/ |
| Frida Kahlo | artistic imagination | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Kahlo%2C_Frida | Frida Kahlo Museum biography: https://www.museofridakahlo.org.mx/wp/wp-content/uploads/2022/08/Biografias-Frida-Kahlo-ingles.pdf |
| Muhammad Ali | combative public assertion | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Ali%2C_Muhammad | National Archives and Smithsonian NMAAHC: https://www.archives.gov/research/african-americans/individuals/muhammad-ali and https://nmaahc.si.edu/explore/stories/float-butterfly |
| Eleanor Roosevelt | humanitarian and justice advocacy | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Roosevelt%2C_Eleanor | National Park Service: https://www.nps.gov/elro/learn/historyculture/udhr.htm and https://home.nps.gov/wori/learn/historyculture/eleanor-roosevelt.htm |
| Amelia Earhart | pioneering exploration and risk | Astro-Databank indexed Rodden AA: https://www.astro.com/astro-databank/Earhart%2C_Amelia | National Park Service and Smithsonian SOVA: https://www.nps.gov/articles/amelia-earhart-birthplace.htm and https://sova.si.edu/record/nasm.1991.0003 |

## Findings From The First Run

The benchmark exposed several real gaps:

- Mars conflict patterns were under-counted when Mars was afflicted or not dignified. This hid combative/public assertion in a case like Muhammad Ali even when Mars had hard or angular contacts.
- `justice_advocacy` used Libra as both a positive signal and a dampener, which diluted the rule.
- Public Venus placement was under-used for artistic output; Frida Kahlo's profile showed imagination but the artistic grace rule was too narrow.
- 10th-house Saturn/Mars work signatures were under-used for industriousness; Marie Curie's discipline surfaced mainly through endurance/perseverance.
- Exploration was too fire/Jupiter-only; Amelia Earhart's air/mutable/Leo signatures did not give enough support to venturesomeness.

## Implemented Source Changes

The changes are limited to source trait catalog JSON files under `backend/traits/catalog/**`:

- Added Mars-MC, Mars-Pluto, and Sun-Mars hard-contact support to `pugnacity`, `warlike`, and `self_assertion`.
- Added Mercury/Aquarius and broader Uranus-ASC support to `frankness`.
- Removed the contradictory Libra dampener and added Air plus 9th/11th-house support to `justice_advocacy`.
- Added public Venus placement and Venus area determination support to `grace_artistic`.
- Added Saturn/Mars 6th/10th-house and Scorpio support to `industriousness`.
- Added Air, Leo/Sun, mutable mobility, and Uranus-MC support to `venturesomeness`.
- Added Air and Uranus-MC support to `travel_inclination`.

## Added Benchmark Harness

Source files:

- `backend/trait_logic_benchmark_profiles.py`
- `backend/trait_logic_benchmark_runner.py`
- `backend/test_trait_logic_benchmark_runner.py`

Run:

```powershell
python backend\trait_logic_benchmark_runner.py
python backend\trait_logic_benchmark_runner.py --json
python -m pytest backend\test_trait_logic_benchmark_runner.py
```

## Current Result

Latest run:

- Cases: 6
- Expected clusters: 7
- Passed clusters: 7
- Result: PASS

Representative hits:

- Einstein: `invention_discovery` score 39.6, summary rank 1
- Curie: `genius_inventive_scientific` score 43.5, summary rank 1; `endurance` score 100.0
- Kahlo: `imagination` score 70.6; `grace_artistic` score 50.0 after the Venus/public-house improvement
- Ali: `frankness` score 37.5; `pugnacity`, `self_assertion`, and `warlike` now clear the combative-public-assertion threshold
- Roosevelt: `humanitarianism` score 61.5; `justice_advocacy` now clears the benchmark threshold
- Earhart: `venturesomeness` score 47.8 after the air/mutable/Leo exploration improvement

## Maintenance Rule

When changing trait logic, rerun the benchmark. If a public-figure cluster fails, either fix the rule with a chart-readable signal or update this document with a clear reason why the biography theme should not be expected from the current doctrine.
