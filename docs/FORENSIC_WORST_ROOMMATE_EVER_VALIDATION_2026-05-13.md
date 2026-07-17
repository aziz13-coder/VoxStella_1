# Forensic Worst Roommate Ever Validation - 2026-05-13

## Scope

This pass builds a documented, runnable forensic benchmark for Netflix's `Worst Roommate Ever`.
The coverage point is 2026-05-13. The official Netflix/Tudum title page lists two released
seasons, and the benchmark inventory contains all nine released episodes:

- Season 1: 5 episodes
- Season 2: 4 episodes

Netflix is used only as the episode discovery index. Event facts, outcomes, and replay anchors
come from court records, law-enforcement/prosecutor records, and reputable reporting. Birth charts
are out of scope; the benchmark uses event charts only.

## Files Added

- `backend/benchmarks/forensic/worst_roommate_ever_cases.json`
- `backend/benchmarks/forensic/README.md`
- `backend/forensic_roommate_benchmark_runner.py`
- `backend/test_forensic_roommate_benchmark_runner.py`

## Case Inventory

| Ep | Title | Real case/persons | Key dates and locations | Context | Incident/outcome | Benchmark status |
| --- | --- | --- | --- | --- | --- | --- |
| S1E1 | Call Me Grandma | Dorothea Puente; convicted victims Dorothy Miller, Benjamin Fink, and Leona Carpenter; suspected/charged context includes more tenant deaths. | Bodies discovered at 2100 F Street, Sacramento, CA in November 1988; verdict 1993-08-26; sentence 1993-12-10. | Boarding-house operator and vulnerable tenants. | Convicted in three tenant murders; other counts were not resolved by conviction. | Holdout: no precise public event time in this source set. |
| S1E2 | Be Careful of the Quiet Ones | Kwang Chol "K.C." Joy; victim Maribel Ramos. | Last seen around 2013-05-02 20:30 in Orange, CA; remains identified May 2013; verdict/sentence in 2014. | Roommates with reported rent/move-out conflict. | Joy convicted of second-degree murder and sentenced to 15 years to life. | Runnable: last-seen/disappearance anchor, not exact homicide time. |
| S1E3 | Marathon Man | Youssef Khater; survivor Callie Quinn. | Attack reported in early morning of 2011-07-21 near Santa Isabel and Condell, Providencia, Santiago, Chile; arrest 2011-08-10. | Shared expatriate hostel/residence and fraud context. | Attempted homicide/assault survivor case; later conviction/sentence reported in Chile. | Holdout: public sources give early-morning window, not exact time. |
| S1E4 | Roommate Wanted - Part 1 | Jamison Bachman, also reported as "Jed Creek"; former roommates/survivors portrayed include Alex Miller, Sonia Acevedo, and Arleen Hairbaedian. | Multi-year pattern across several roommate contexts; later 2017 brother homicide charge appears in Part 2. | Roommate ads/personal ties, refusal to leave, legal/coercive tactics. | Serial squatting/harassment pattern documented mostly by longform journalism and documentary accounts. | Holdout: pattern case, no single replay timestamp. |
| S1E5 | Roommate Wanted - Part 2 | Jamison Bachman; charged victim Harry Bachman. | Welfare-check dispatch at 2017-11-04 12:16 in Elkins Park, PA; Jamison died before trial. | Family tie; Harry had reportedly bailed Jamison out but would not let him stay. | Jamison was charged with first- and third-degree murder; no conviction because he died before trial. | Runnable: official DA welfare-check/discovery anchor. |
| S2E1 | My BFF Tried to Kill Me | Janie Lynn Ridd; survivor Rachel, publicly identified mainly by first name; Rachel's son in the custody/care context. | VRSA purchase/communications described across October-December 2019; charges reported 2019-12-20. | Longtime friends turned roommates; caretaker and child-custody context. | Abuse/poisoning allegations and biological-agent conviction/plea reporting; survivor case. | Holdout: no precise poisoning, delivery, arrest, or purchase timestamp in this source set. |
| S2E2 | Housemate from Hell | Scott Edmund Pettigrew; victim Anita "Mimie" Cowen; Darrell Hatfield in documentary roommate context. | Police dispatched 2016-06-14 23:39 in Cathedral City, CA; Cowen pronounced dead 2016-06-15 00:17; appeal 2021-03-25. | Cowen rented rooms in her home; Pettigrew was a lodger/roommate. | Pettigrew convicted of first-degree murder, elder abuse, and protective-order violation; sentence 25 years to life. | Runnable: police welfare-check/disturbance dispatch anchor. |
| S2E3 | Burning Down the House | Tammy Fritz; survivor James "Bo" Bowden; co-defendants Sean Lagoe and Michelle Heaston. | Incidents reported in 2005 and 2009 in Colorado Springs; sentence 2015-05-26. | Bowden was a friend of Fritz's late husband and moved in to help the household; insurance motive reported. | Attempted murder for insurance money; Fritz sentenced to 48 years; co-defendants pleaded guilty to related charges. | Holdout: years and broad sequences only, no precise event time. |
| S2E4 | The Lethal Landlord | Michael Lee Dudley; victims Jessica Lewis and Austin Wenner. | Probable homicide sequence anchor 2020-06-09 19:00 in Burien, WA; remains found 2020-06-19 and 2020-06-22 near Seattle water sites; conviction/sentence 2022-2023; appeal 2025-08-25. | Lewis and Wenner were a couple staying/renting in Dudley's home. | Dudley convicted of two counts of second-degree murder while armed with a firearm; sentence reported as about 46 years; appeal otherwise affirmed except financial-obligation correction. | Runnable: probable evening sequence anchor, not exact death time. |

## Source Map

| Source ID | Role | URL |
| --- | --- | --- |
| `netflix_wre_tudum_series` | Official Netflix/Tudum series page and Season 1 episode inventory | https://www.netflix.com/tudum/worst-roommate-ever |
| `netflix_wre_s2_tudum` | Official Netflix/Tudum Season 2 overview | https://www.netflix.com/tudum/articles/worst-roommate-ever-season-2-release-date-news |
| `history_puente_discovery_1988` | Puente discovery summary | https://www.history.com/this-day-in-history/november-11/police-make-a-grisly-discovery-in-dorothea-puentes-lawn |
| `latimes_puente_verdict_1993` | Puente verdict reporting | https://www.latimes.com/archives/la-xpm-1993-08-27-mn-28512-story.html |
| `upi_puente_sentence_1993` | Puente sentencing reporting | https://www.upi.com/Archives/1993/12/10/Sacramento-landlady-gets-life-for-murders/1569755499600/ |
| `abc7_ramos_last_seen_2013` | Ramos public last-seen time | https://abc7.com/archive/9095889/ |
| `cbs_la_ramos_arrest_2013` | Ramos remains identification and Joy arrest | https://www.cbsnews.com/losangeles/news/police-trying-to-determine-if-body-found-in-remote-modjeska-canyon-is-missing-war-vet/ |
| `cbs_la_joy_verdict_2014` | Joy verdict reporting | https://www.cbsnews.com/losangeles/news/verdict-reached-in-murder-trial-of-roommate-accused-of-killing-army-vet/ |
| `cbs_la_joy_sentence_2014` | Joy sentencing reporting | https://www.cbsnews.com/losangeles/news/o-c-man-gets-15-to-life-for-killing-iraq-war-vet/ |
| `emol_khater_arrest_2011` | Chilean reporting on Khater arrest and attack facts | https://www.emol.com/noticias/nacional/2011/08/10/497167/pdi-detiene-a-atleta-danes-por-homicidio-frustrado-de-joven-estadounidense.html |
| `chilevision_khater_case_2022` | Chilean secondary case summary | https://www.chilevision.cl/noticias/reportajes/a-fondo/caso-inspiro-una-serie-estafador-que-se-hacia-pasar-por-deportista |
| `longreads_bachman_2018` | Longform Jamison Bachman pattern source | https://longreads.com/2018/02/21/worst-roommate-ever/ |
| `philly_inquirer_bachman_2022` | Local Bachman overview | https://www.inquirer.com/news/jamison-bachman-jed-creek-worst-roommate-ever-philadelphia-20220304.html |
| `montgomery_da_bachman_2017` | Official DA release for Harry Bachman welfare-check/discovery anchor | https://www.montgomerycountypa.gov/Archive.aspx?ADID=4031 |
| `cbs_philly_bachman_2017` | Local Bachman charge reporting | https://www.cbsnews.com/philadelphia/news/man-arrested-for-murder-of-brother-in-elkins-park/ |
| `utah_ag_ridd_2024` | Utah AG Ridd case summary | https://attorneygeneral.utah.gov/ridd-case-roommate-assaulted-by-a-virus/ |
| `deseret_ridd_charges_2019` | Ridd charging-document reporting | https://www.deseret.com/utah/2019/12/20/21032179/utah-woman-bacteria-staph-infections-biological-weapon-charges/ |
| `cathedral_city_pd_pettigrew_2016` | Police press release with Pettigrew dispatch/pronouncement times | https://www.cathedralcitypolice.com/wp-content/uploads/2018/04/Press-Release-187-June-15-20161.pdf |
| `justia_pettigrew_appeal_2021` | Pettigrew appellate opinion | https://law.justia.com/cases/california/court-of-appeal/2021/e074122.html |
| `gazette_fritz_sentence_2015` | Fritz sentencing report | https://gazette.com/2015/05/26/colorado-springs-woman-who-tried-to-kill-roommate-for-insurance-money-gets-48-years-0a504450-0dae-5386-8f8f-8d8c86455fd6/ |
| `wa_courts_dudley_2025` | Dudley appellate opinion | https://www.courts.wa.gov/opinions/pdf/851993.pdf |
| `seattle_times_dudley_charged_2020` | Dudley charging-document reporting | https://www.seattletimes.com/seattle-news/law-justice/burien-man-charged-with-murder-in-deaths-of-two-people-found-in-bags-on-west-seattle-beach/ |
| `fox13_dudley_sentence_2023` | Dudley sentencing reporting | https://www.fox13seattle.com/news/man-sentenced-to-46-years-for-killing-tenants-stuffing-bodies-in-suitcases-found-on-seattle-beach |

Every factual field in the JSON inventory carries source IDs and a confidence value. The runner validates
those source references.

## Research Status

Extraction status:

- Complete episode inventory for two released seasons and nine released episodes as of 2026-05-13.
- Four replayable anchors: Ramos last-seen, Harry Bachman welfare-check discovery, Cowen/Pettigrew welfare-check dispatch, Dudley probable evening sequence.
- Five holdouts because public sources did not provide a precise or tight event time: Puente, Khater, Bachman Part 1 pattern, Ridd, Fritz.
- No noon charts or invented times were introduced.
- Season 2 episode order has a known metadata wrinkle: the Tudum Season 2 article describes the Tammy Fritz and Scott Pettigrew stories in a different paragraph order than catalog-style episode listings. The dataset follows the title order used by common catalog listings and records the uncertainty.

## Benchmark Schema

Top-level fields:

- `schema_version`, `generated_at`, `benchmark_id`, `purpose`
- `coverage`: release-count and episode-coverage notes
- `benchmark_policy`: runnable/holdout rules and no-fabricated-times policy
- `comparison_axes`: shared forensic replay axis list
- `sources`: source ID, URL, kind, confidence/strength, notes
- `cases`: all released episodes

Each case contains:

- `episode`: season, episode, title, source IDs, confidence
- `case_inventory`: `real_people`, `key_dates`, `locations`, `relationship_context`, `incident_type`, `outcome`, `birth_times`
- `benchmark`: replay status, event anchor/query for runnable cases, expected axes, contradictory axes, expected survivability, and frozen current baseline fields for runnable cases

Runnable query fields are passed directly to `/api/astro-clock/forensic` after `datetime_local` is mapped to
the route's `datetime` parameter.

## Baseline Results

Command:

```powershell
python backend\forensic_roommate_benchmark_runner.py
```

Result:

- Inventory: 9 cases, 23 sources
- Runnable cases: 4
- Holdouts: 5
- Missing source references: 0
- Fact source gaps: 0
- Route errors: 0
- Directional comparison statuses: 3 aligned, 1 partially aligned
- Primary-axis recall: 11/12 = 0.9167
- False-positive contradictions: 0
- Survivability statuses: 3 aligned, 1 misaligned

Runnable case baselines:

| Case | Comparison | Survivability | Notes |
| --- | --- | --- | --- |
| Ramos last-seen | Aligned: homicide, missing-person, known-roommate axes matched. | Aligned: `Lower / fatal_pressure_dominant`. | Extra family, water, and witness categories are broad context, not exact fact claims. |
| Harry Bachman welfare check | Partially aligned: homicide and family matched; route/vehicle missed. | Aligned: `Lower / fatal_pressure_dominant`. | Vehicle theft is a sourced detail but not the core event axis; no calibration from one miss. |
| Cowen/Pettigrew welfare call | Aligned: homicide, known-associate, and water/pool axis matched. | Aligned: `Lower / fatal_pressure_dominant`. | Good fatal roommate/lodger benchmark anchor. |
| Dudley tenant double homicide | Aligned: homicide, known-associate, and concealment axes matched. | Misaligned: engine returned `Moderate / risk_loaded_survival`; expected fatal. | The anchor is a probable sequence proxy, not exact death time, so this is a documented gap rather than a calibration trigger by itself. |

## Comparison Findings

Useful behavior:

- The current engine recognizes homicide/violence pressure in all four runnable cases.
- It finds roommate, tenant, or known-associate context in Ramos, Pettigrew/Cowen, and Dudley.
- It captures concealment/deception in the Ramos and Dudley style outputs.
- Fatal survivability is correct for Ramos, Harry Bachman, and Pettigrew/Cowen.

Overreach and caution:

- Several outputs add broad contextual categories that are not core factual labels for the case, especially family, water, witness, or abduction/missing-person language.
- These extra labels are acceptable as exploratory testimony but should not be treated as evidence that the engine reproduced the full case narrative.
- The runner records contradictions separately so future overreach can be measured instead of hand-waved.

Misses:

- The Harry Bachman anchor misses the `route_vehicle_transport` axis tied to the reported Ford Escape theft.
- The Dudley anchor undercalls survivability for a fatal tenant double homicide, returning risk-loaded survival.

## Calibration Decision

No forensic engine scoring or rule changes were made in this pass.

Rationale:

- The benchmark has only four runnable anchors, and two are explicitly proxy-style anchors rather than exact event times.
- The Bachman transport miss is a sourced detail but not enough evidence to change general route/vehicle rules.
- The Dudley survivability miss is important, but one proxy-anchor double-homicide case is not a strong enough basis for changing general survivability weights.
- Changing rules now would risk overfitting to a small Netflix-indexed sample.

Calibration action taken:

- Added a reusable benchmark dataset and runner.
- Froze current comparison and survivability baselines in the dataset.
- Added tests for source coverage, schema validation, comparator behavior, report rendering, and live-route baseline drift.

Future calibration trigger:

- Revisit survivability only after adding more exact-time fatal known-person home/tenant cases, especially cases with firearm, dismemberment, concealment, or water-disposal signatures.
- Revisit route/vehicle rules only if multiple discovery anchors with sourced vehicle movement miss the route axis without creating accident/disaster false positives.

## Implementation Notes

The runner:

- validates source IDs and per-fact source/confidence coverage
- reports runnable versus holdout inventory
- calls `/api/astro-clock/forensic` through the Flask test client
- compares primary expected axes, missed axes, contradictory axes, survivability status, and top findings
- exits nonzero only for validation or route errors, not for legitimate benchmark misses

The live-route regression test intentionally preserves the current Dudley survivability miss as a frozen baseline.
That makes future calibration measurable instead of silent.

No frontend source changed. No frontend tests or builds were required.

## Limitations

- The benchmark is directional, not a claim that a chart can prove case facts.
- Public event timing is thin for several episodes. Holdouts should not be promoted without better timestamps.
- Discovery and last-seen anchors are not equivalent to exact death or assault times.
- Some source URLs are journalism rather than court records because official records were not available for every fact.
- The Netflix/Tudum Season 2 article has an apparent S2E2/S2E3 description-order inconsistency.

## Recommended Next Benchmark Sources

- Court opinions or probable-cause affidavits for Puente timing, if public.
- Trial or charging records for K.C. Joy with more precise last-contact or phone/computer timestamps.
- Chilean court records for Khater if accessible.
- Utah court records for Ridd plea/sentencing and controlled-delivery/arrest timing.
- El Paso County/Colorado court records for Fritz fire and attack timestamps.
- More non-Netflix roommate, lodger, landlord, and tenant cases as controls.
- Exact-time fatal tenant/roommate controls to test the Dudley survivability gap without overfitting.

## Verification

Commands run:

```powershell
python -m pytest -q backend\test_forensic_roommate_benchmark_runner.py
```

Result:

- `4 passed, 1 warning in 1.14s`

```powershell
python -m pytest -q tests\test_forensic_features.py tests\test_forensic_core_rules.py tests\test_forensic_deception_rules.py tests\test_forensic_direction_rules.py tests\test_forensic_route_contract.py tests\test_forensic_worst_ex_ever_benchmarks.py tests\test_forensic_netflix_true_crime_benchmarks.py
```

Result:

- `60 passed, 1 warning, 34 subtests passed in 3.78s`

```powershell
python backend\forensic_roommate_benchmark_runner.py
```

Result:

- exit code 0
- 4 runnable cases, 5 holdouts
- 3 aligned, 1 partially aligned
- 11/12 primary-axis recall
- 3 survivability aligned, 1 survivability misaligned
- no route errors
