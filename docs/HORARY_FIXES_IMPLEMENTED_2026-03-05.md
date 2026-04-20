# Horary Engine Fixes Implemented (2026-03-05)

## Scope
This note documents the fixes implemented after the horary/astroclock audit and the follow-up runtime stability patch discovered during dummy-question execution on Windows.

## Implemented Fixes

### 1) AstroClock paused/manual chart contract
- File: `backend/astro_clock_engine.py`
- Anchors:
  - `class MoonState` at line 47
  - `_build_real_time_payload` at line 125
  - `_generate_chart_with_horary_engine` at line 169
  - `_calculate_moon_state` at line 258
- Fix summary:
  - `MoonState.last_aspect` and `MoonState.next_aspect` accept structured payloads (`Optional[Any]`).
  - Real-time payload path now passes full `chart_result` to moon-state calculation.
  - Non-realtime modes (`manual`, `paused`) now force explicit `date` + `time` and `use_current_time=False`.
  - Moon aspect fallback now checks both `chart_data` and top-level `chart_result`.

### 2) Translation event emission regression
- File: `backend/horary_engine/perfection_core.py`
- Anchors:
  - `_detect_translation_events` at line 376
  - translation confidence and append around lines 508 and 512
- Fix summary:
  - Translation event creation is no longer limited to hostile-path branching.
  - Favorable translation paths now emit `TRANSLATION` events correctly.

### 3) Malefic prohibition chronology semantics
- File: `backend/horary_engine/engine.py`
- Anchor:
  - `_check_malefic_prohibition` at line 7054
- Fix summary:
  - Logic now requires chronological comparison against `earliest_perfection_days`.
  - Returns only chronology-grounded outcomes: `true_prohibition` or `post_perfection`.
  - Stops classifying generic affliction inside prohibition logic.
  - Handles aspects where target planet appears in either side of aspect tuple.

### 4) Solar thresholds from configuration
- Files:
  - `backend/horary_engine/engine.py`
  - `backend/horary_constants.yaml`
- Anchors:
  - `_analyze_enhanced_solar_condition` at line 962
  - `legacy_fixed` gate at line 983
  - per-planet solar overrides at line 1000
  - `legacy_fixed_solar_orbs` config entry at `horary_constants.yaml:64`
- Fix summary:
  - Replaced hardcoded solar distances with config-driven values.
  - Added optional per-planet override path.
  - Added legacy compatibility switch: `legacy_fixed_solar_orbs`.

### 5) Lost-object Moon VoC denial path
- File: `backend/horary_engine/engine.py`
- Anchor:
  - `_check_theft_loss_specific_denials` at line 6989
- Fix summary:
  - Uses enhanced VoC API (`_is_moon_void_of_course_enhanced`) instead of nonexistent property access.

### 6) Considerations contract alignment
- File: `backend/horary_engine/engine.py`
- Anchors:
  - chart_data considerations injection at line 1685
  - `_calculate_considerations` at line 1922
- Fix summary:
  - Added override-aware context fields:
    - `radical_raw`
    - `radicality_ignored`
    - `moon_void_ignored`
  - Supports ignore flags cleanly while preserving computed ground truth context.
  - Injects `considerations` into serialized `chart_data` for downstream adapters.

### 7) Windows encoding runtime crash in debug print path
- File: `backend/horary_engine/engine.py`
- Anchors:
  - line 6844
  - line 7182
- Fix summary:
  - Replaced Unicode arrows in `print(...)` debug statements with ASCII-safe markers.
  - Prevents `UnicodeEncodeError` on cp1251 consoles during live judgment runs.

## Regression Tests Added
- `tests/test_astroclock_adapter_fixes.py`
  - `test_paused_mode_uses_effective_datetime`
  - `test_moon_state_uses_top_level_fallbacks`
- `tests/test_horary_judgment_fixes.py`
  - `test_translation_event_emits_for_favorable_paths`
  - `test_prohibition_requires_chronology_and_preemption`
  - `test_solar_condition_uses_configured_under_beams_limit`
  - `test_lost_object_voc_denial_uses_enhanced_voc_check`
  - `test_considerations_include_override_context`

## Validation Performed
- `python -m compileall backend/astro_clock_engine.py backend/horary_engine/engine.py backend/horary_engine/perfection_core.py tests/test_astroclock_adapter_fixes.py tests/test_horary_judgment_fixes.py`
- `python -m compileall backend/app.py backend/astro_clock_api.py backend/horary_engine/serialization.py`
- Runtime smoke harness covering all implemented fixes (passed).
- Live uncaptured dummy-question run after encoding patch (passed; no UnicodeEncodeError).

## Dummy-Question Reaction Snapshot
Execution settings:
- location: `Jerusalem, Israel`
- datetime: `2026-03-05 14:30`
- timezone: `Asia/Jerusalem`
- all ignore flags: `False`

Results:
- Career question: `NO` (70), `Category.CAREER`, houses `[1, 10]`
- Lost keys question: `NO` (50), `Category.MONEY`, houses `[1, 4]`
- Relationship/contact question: `NO` (90), `Category.MONEY`, houses `[1, 2]`
- Lawsuit question: `NO` (65), `Category.LAWSUIT`, houses `[1, 7, 9]`
- Business partner trust question: `NO` (70), `Category.CAREER`, houses `[1, 10, 7]`

## Notes
- `pytest` is not installed in this environment (`python -m pytest` unavailable), so validation used compile checks and runtime smoke harnesses.
- Category routing for some prompts (for example relationship and lost-object phrasings) may need a separate taxonomy review.
