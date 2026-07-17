# Estate Election Benchmark Plan

This plan separates mechanical coverage from predictive validation. The synthetic fixtures prove that the coded estate rules emit the expected tags and move scores in the expected direction. The backtest and prospective logs are for evidence about whether the model is useful in real estate timing.

## Synthetic Rule Fixtures

Each rule gets one tiny chart fixture. The tests assert exact tag text and only compare score direction, not full chart totals, because unrelated estate rules can also fire in a compact chart.

| Rule | Fixture intent | Expected tag | Expected direction |
| --- | --- | --- | --- |
| Waxing vs waning Moon | Same Sun/Moon phase geometry with buy/sell direction changed by fixture | `Event buy Moon phase support: waning (+2.0)` and `Event buy Moon phase mismatch: waxing (-1.0)` | Buy waning fixture scores above buy waxing fixture |
| Rapid/slow signs by latitude | North-latitude Asc and Moon placed in rapid Aquarius or slow Cancer | `Event Moon rapid-sign estate support: Aquarius (+3.0)`, `Event Asc rapid-sign estate support: Aquarius (+3.0)`, `Event Moon slow-sign estate support: Cancer (+2.0)`, `Event Asc slow-sign estate support: Cancer (+2.0)` | Matching latitude/sign fixture scores above the same sign under the opposite direction branch |
| Mercury-Mars friction | Mercury and Mars conjunct versus separated | `Event Mercury-Mars friction: conjunction/square (-1.5)` | Friction fixture scores below separated fixture |
| 2nd ruler vs 7th ruler aspects | Custom cusps make Mercury rule 2nd and Jupiter rule 7th, then sextile them | `Event counterparty tie caution: 2nd ruler sextile 7th ruler (-0.9)` | Aspect fixture scores below the same fixture with no major aspect |
| Fortuna in Sagittarius/Pisces | Fortuna placed in Sagittarius, estate house 4 | `Event Fortuna estate sign support: Sagittarius (+1.0)` | Sagittarius/Pisces Fortuna fixture scores above neutral-sign Fortuna fixture |
| Benefic/malefic in 4th, 2nd, 8th | House-explicit planet rows isolate property, money, and transfer houses | `Event Mercury in 4th property support (+1.0)`, `Event angular property pressure: Mars in 4th (-1.1)`, `Event buy money set support: Venus in 2nd (+0.8)`, `Event buy money set malefic caution: Saturn in 2nd (-0.8)`, `Event sell transfer set support: Jupiter in 8th (+0.8)`, `Event sell transfer set malefic caution: Saturn in 8th (-0.8)` | Benefic-only fixture scores above matching malefic-pressure fixture |
| Participant Fortuna-to-Asc, Asc-ruler-to-event-Moon | Certified participant Asc and Asc ruler are aligned to event Fortuna and event Moon | `Buyer A: Asc ruler conjunction event Moon (+1.25)` and `Buyer A: event Fortuna conjunction participant Asc (+1.20)` | Participant resonance fixture scores above the same fixture with precision disabled |

Executable coverage: `backend/test_estate_synthetic_rule_fixtures.py`.

## Extraction Benchmarks

Controlled line rows are fed directly to `_extract_estate_periods`. This avoids chart calculation noise and verifies the estate-specific extraction contract.

| Scenario | Inputs | Expected assertions |
| --- | --- | --- |
| Total/all | `display_mode=total`, `scope=all`, `level_percent=50` | `estate_pass` only when event and participant lines both meet thresholds, `estate_selected_threshold` equals sum of selected line thresholds, and `estate_periods` uses `estate-period:*` ids |
| Detail/selected | `display_mode=detail`, `scope=selected`, selected participant line | Only selected participant line contributes to score, period ranking, and `estate_line_states` |
| Total/current | `display_mode=total`, `scope=current`, current event line | Only the current event line contributes, adjacent passing rows merge into one period |

Executable coverage: `backend/test_estate_extraction_benchmarks.py`.

## Scan Stability

Run the same seven-day scan across several latitudes and house systems, then track:

- No crashes.
- Deterministic top windows between repeated runs.
- Reasonable score spread, reported as min, max, and spread.
- Runtime per 1,000 timestamps.
- No empty line payloads for valid estate scans.

The local harness is deterministic and synthetic so it can run in CI without ephemeris services:

```powershell
python tools\estate_benchmark.py scan-stability --days 7 --step-minutes 60
python tools\estate_benchmark.py benchmark-suite --days 7 --step-minutes 60
```

## Backtest Dataset

Collect real transaction cases in `tests/fixtures/estate_backtest_dataset_template.csv` format. Required event columns cover:

- Offer submitted.
- Offer accepted.
- Contract signed.
- Closing date.
- Listing date for sellers.
- Scan start, scan end, step minutes, latitude, longitude, house system, direction, and participant chart source.

Outcome columns cover:

- Deal completed vs failed.
- Final price over/under ask.
- Time to close.
- Inspection, appraisal, and legal issues.

The first benchmark comparison should rank the chosen event time against random windows and simpler baselines such as Moon phase only, latitude sign only, and event-line-only score.

Backtest workflow:

1. Copy the template to a working CSV.
2. Enter one row per real transaction. Do not invent outcomes; leave unknown outcomes blank.
3. Add `scan_start`, `scan_end`, and `step_minutes`. If scan bounds are blank, the ranker uses a seven-day window around `chosen_event_datetime`.
4. Add either `participant_snap_id` for app-engine runs or `participant_chart_json` / `participant_chart_path` for portable runs.
5. Run the ranker, then validate the ranked file.

Sample files:

- `tests/fixtures/estate_backtest_sample.csv` is a synthetic ranked example for command checks only.
- `tests/fixtures/estate_prospective_freeze_sample.csv` is a synthetic freeze-log example for command checks only.
- These files are not predictive evidence and must not be mixed into real validation summaries.

Synthetic ranker smoke test:

```powershell
python tools\estate_benchmark.py backtest-rank --dataset tests\fixtures\estate_backtest_dataset_template.csv --output tests\fixtures\estate_backtest_ranked.csv --engine synthetic
```

Real app-engine ranker, using the same chart path as Astro Clock:

```powershell
python tools\estate_benchmark.py backtest-rank --dataset path\to\estate_cases.csv --output path\to\estate_cases_ranked.csv --engine app
```

Template or ranked-file validation:

```powershell
python tools\estate_benchmark.py backtest --dataset path\to\estate_cases_ranked.csv
python tools\estate_benchmark.py backtest --dataset tests\fixtures\estate_backtest_sample.csv
```

Computed rank fields:

- `chosen_rank` and `chosen_score`: full estate model.
- `random_window_rank`: deterministic random-window baseline.
- `moon_phase_baseline_rank`: Moon phase rule only.
- `latitude_sign_baseline_rank`: latitude sign rule only.
- `event_line_baseline_rank`: event chart line only, excluding participant fit.
- `top_windows_json`: top full-model windows for audit.

## Prospective Freeze Test

Freeze the model version before outcomes are known. For each candidate case, log:

- Frozen model version.
- Scan window, location, house system, direction, and participant snap id.
- Top windows scored before outcome.
- Actual selected time.
- Later outcome review without changing weights.

Create or replace a frozen prospective case:

```powershell
python tools\estate_benchmark.py freeze-case `
  --log tests\fixtures\estate_prospective_freeze.csv `
  --case-id live-001 `
  --direction buy `
  --location "Jerusalem" `
  --timezone "Asia/Jerusalem" `
  --house-system placidus `
  --latitude 31.778 `
  --longitude 35.235 `
  --scan-start 2026-04-18T00:00:00+00:00 `
  --scan-end 2026-04-25T00:00:00+00:00 `
  --selected-event 2026-04-20T10:00:00+00:00 `
  --engine app `
  --replace
```

Validate the prospective log after outcomes are reviewed:

```powershell
python tools\estate_benchmark.py prospective-freeze --log tests\fixtures\estate_prospective_freeze.csv
python tools\estate_benchmark.py prospective-freeze --log tests\fixtures\estate_prospective_freeze_sample.csv
```

The freeze row records the model version, freeze timestamp, top windows, selected rank, baseline ranks, and later outcome fields. Do not change the model weights for a frozen case; add a new model version if the scoring logic changes.
