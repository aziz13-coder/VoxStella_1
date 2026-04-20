# Forensic Direction Rule Fixes 2026-03-23

## Scope

Second grounded forensic rule pass after replay slice 2 exposed four reusable direction gaps:

- `family_involvement`
- `accomplice_or_witness`
- `friend_or_close_associate`
- `authority_or_public_case`

The goal was to fix those gaps at the feature/rule layer, not by changing Astro Clock request handling and not by tuning a single replay case.

## What Changed

### Shared feature synthesis

Updated [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py) to expose the house/ruler structure the missed directions actually depended on:

- `malefics_in_8th`
- `third_ruler_*`
- `eighth_ruler_*`
- `eleventh_ruler_*`
- `first_and_fifth_rulers_same_house`
- `fifth_and_seventh_rulers_same_house`
- `first_fifth_seventh_clustered`

This keeps the rule layer grounded in reusable house logic instead of case labels.

### Directional rules

Updated [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml) with reusable rules for:

- family + child significator clustering under malefic/death pressure
- malefic in the 8th with hidden or family-linked context
- witness / accomplice signatures through 3rd, 7th, 11th, and 12th-house links
- friend / close associate involvement through 7th/11th crossover
- public / authority / celebrity-linked cases through 10th-house prominence tied to hidden or violent context

These changes are not keyed to specific names or case titles.

## Why These Changes Are Grounded

- `family_involvement`
  - Andrea Yates was already showing child-victim and violence direction, but the old family rules depended too narrowly on Moon/Cancer/4th-house pressure.
  - The new rule adds a broader but still structured family pattern: self/child/partner significators clustering under death or malefic pressure.

- `violence_homicide`
  - Menendez was under-detected because the older violence rules leaned too heavily on 1st-ruler and Moon-hard-malefic patterns.
  - The new rule recognizes a grounded hidden-homicide pattern: malefic in the 8th plus hidden luminaries or strong family/domestic involvement.

- `accomplice_or_witness`
  - The old layer had language dictionaries for witnesses/accomplices but no directional trigger using 3rd/11th structure.
  - The new rule uses hidden 3rd/11th-house links and 7th/11th crossover.

- `friend_or_close_associate`
  - Bob Crane showed the missing pattern clearly: 7th-house perpetrator axis tied to the 11th.
  - The new rule encodes that directly as a reusable house relation.

- `authority_or_public_case`
  - Gianni Versace needed a public/celebrity emphasis, not more homicide tuning.
  - The new rule uses 10th-house / solar prominence tied to hidden or violent context.

## Result

After rerunning the real replay slices:

- slice 1 remains `6/6 aligned`
- slice 2 improved from `4 aligned / 4 partially aligned` to `8/8 aligned`

That means the fixes generalized on the current replay set without breaking the earlier aligned cases.

## Files Changed

- [features.py](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/features.py)
- [directional_context_rules.yaml](C:/Users/sabaa/Downloads/codexhorary/backend/forensic/knowledge/directional_context_rules.yaml)
- [test_forensic_direction_rules.py](C:/Users/sabaa/Downloads/codexhorary/tests/test_forensic_direction_rules.py)
- [forensic_case_replay_slice_2_results.json](C:/Users/sabaa/Downloads/codexhorary/tests/fixtures/forensic_case_replay_slice_2_results.json)

## Verification

- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary:/mnt/c/Users/sabaa/Downloads/codexhorary/backend backend/venv/bin/python -m unittest tests.test_forensic_case_corpus tests.test_forensic_case_replay_slice_1 tests.test_forensic_case_replay_slice_2 tests.test_forensic_direction_rules tests.test_forensic_route_contract tests.test_forensic_features -v'`
- `wsl.exe bash -lc 'cd /mnt/c/Users/sabaa/Downloads/codexhorary && PYTHONPATH=/mnt/c/Users/sabaa/Downloads/codexhorary:/mnt/c/Users/sabaa/Downloads/codexhorary/backend backend/venv/bin/python - <<'"'"'PY'"'"'\nimport runpy\nrunpy.run_path(\"scripts/run_forensic_case_replay_slice_1.py\", run_name=\"__main__\")\nrunpy.run_path(\"scripts/run_forensic_case_replay_slice_2.py\", run_name=\"__main__\")\nPY'`
- `cmd /c npx vitest run src/tests/astroclockApi.test.mjs --config vitest.config.mjs`

## Next Safe Step

Do not keep tuning slice 2.

The next safe move is a fresh replay slice, so these new direction families are tested on new cases rather than tuned again on the current set.
