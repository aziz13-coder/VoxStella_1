# Election Model Reference and Source-Alignment Report

Date: 2026-07-31
Implementation version: `2026.07.31.1`

## Scope

This document records the reviewed Election workflow, the logic of every
selectable model variant, its source status, and the reconciliations completed
in the July 2026 audit.

Election scores are ordinal rankings within one model run. A score from one
model must not be compared numerically with a score from another model.
Natal overlay remains optional in the shared workflow. Models whose definition
is participant-relative still require their intrinsic saved-chart inputs:
Marriage Beta requires two participants, Business Beta at least one, Estate one,
and Lunar Fertility a natal phase anchor.

## Runtime Workflow

1. `ElectionModal.jsx` gathers the model, range, location, optional natal
   context, model options, and participant inputs.
2. `api.mjs` serializes those values to the validate and streamed-scan routes.
3. `/election/validate` canonicalizes the matter key, validates the range,
   step, limit, options, and required participant inputs.
4. `/election/suggest/stream` resolves optional natal context and any required
   participant charts, then calculates every timestamp in the requested range.
5. Reference-parity mode forces one-minute resolution for Marriage Beta,
   Business Beta, and Estate. It supports a complete 30-day range
   (43,201 inclusive points).
6. The selected scorer returns `Score(value, tags, pros, cautions, lines)`.
   Standard models normally use the total score and tags. Recovered-reference
   models also expose event and participant lines.
7. Day/hour filters are applied, candidates are ranked, and line-aware models
   segment periods using their total/detail and all/current/selected controls.
8. The SSE response reports progress followed by a final payload containing
   results, statistics, aggregated failure diagnostics, and model metadata.

Unknown matter keys are rejected. They no longer fall back to Marriage.
Per-timestamp calculation failures are counted by exception type and include
bounded diagnostic samples instead of disappearing silently.

## Model Matrix

| Model variant | Main workflow logic | Source profile | Audit result |
|---|---|---|---|
| Marriage Alpha | Fortifies Moon, Venus, Jupiter, the 7th house/ruler, and preferred fixed Ascendant/Moon conditions; optional natal promise and transit context | Historical primary: Morin Book 26 with Bonatti election rules | Added Bonatti's Taurus/Leo preference and Scorpio/Aquarius caution. Natal remains optional. |
| Marriage Beta | Separate event line plus two participant-fit lines; Moon-day intervals, almutens, recovered outer-body rules, and participant cross-links; line-aware period extraction | Recovered Galaxy reference | Completed favorable/tense line payloads and extraction. Planet-only participant rules remain active, while house/cusp/almuten rules require safe recorded birth-time precision. Jupiter retrograde support corrected to `+3`. |
| Surgery | Avoids the Moon in the sign governing the operated member; evaluates Moon light, benefic/malefic contacts, rulers, houses, speed, and procedure-specific conditions | Historical primary: Bonatti Treatise 7 with Morin context | Increasing light is the primary preference. Decreasing light, Mercury retrograde, VOC, Via Combusta, and Saturn prominence are cautions, not invented absolute prohibitions. Target-body sign remains a hard rule. |
| Business Alpha | Evaluates Ascendant/MC rulers, Moon, Mercury, Jupiter, angularity, dignity, timing, and optional natal context | Traditional synthesis | Growth, commerce, and conservative options now change score only when their relevant chart conditions exist; constant bonuses/caps were removed. Waxing uses directed elongation. |
| Business Beta | Recovered event and participant lines with planetary timing, participant fit, thresholding, and period extraction | Recovered Galaxy reference | Existing recovered implementation retained; false “all saved charts are certified” wording and runtime assumption removed. Precision comes from saved birth-time quality. |
| Estate | Buy/sell event line plus one participant line, traditional planetary timing, participant fit, and estate-specific period extraction | Recovered Galaxy reference | Existing recovered implementation retained. Participant precision is read from saved-chart quality rather than being declared certified. |
| Contract | Mercury condition and exact direct-station age, Moon condition/aspects, 7th house/ruler, fixed axes, and optional natal overlays | Traditional synthesis | The minimum-direct-days option now uses an actual Mercury direct-station instant, not speed as a proxy. Waxing uses directed elongation. |
| Journey | Cardinal/movable Ascendant, sound Ascendant ruler, Moon, 3rd/9th significations, benefic support, and malefic impediments | Historical primary: Morin Book 26 and Bonatti | Waxing classification corrected to directed elongation; existing short/long journey options retained. |
| Haircut | Moon in common/double-bodied signs except Gemini; malefic and phase context; optional natal overlays | Historical primary: Bonatti Treatise 7, second-house Chapter 4 | Virgo, Sagittarius, and Pisces are preferred; Gemini is avoided. Aries is allowed for trimming and prohibited only for complete shaving. The prohibition is final and cannot be offset by later bonuses. The unsupported Ascendant sign table was removed. |
| Beautification | Venus/Moon, selected body-part signs, procedure type, aspects, timing, and optional natal context | Modern heuristic | Kept explicitly labeled as a modern analogy, not a Bonatti/Morin rule set. |
| Conception | 5th house/ruler, Moon, Venus, Jupiter, Ascendant, malefics, and optional natal overlay; optional traditional polarity focus | Traditional synthesis | Retained with explicit wording that it is traditional timing, not medical fertility or fetal-sex prediction. |
| Lunar Fertility Windows | Natal Sun–Moon phase and antiphase recurrences, Moon-sign polarity, hourly windows, period grouping, and display normalization | Recovered Galaxy SkyLiner/Jonas reference | Overlap strengths now add; phase wins the display flag on overlap; visible scores normalize within the selected range while raw strength is preserved. Level is a visual guide and no longer deletes nonzero exported periods. |
| Viral Publish | Communication/audience houses, Mercury, Moon, Jupiter, aspects, timing, and optional natal context | Modern heuristic | Retained and labeled as a modern house-signification analogy. |
| Battle | Compares the Ascendant side with the 7th-house opponent, rulers, Moon, Mars/Saturn, fortune, and action type | Historical primary: Morin Book 26 | Removed the unsupported blanket “any planet in the 8th” prohibition. The hard exclusion now applies to the source-relevant case where the Ascendant ruler applies to a stronger 7th ruler; being in the 8th only qualifies that relationship. |
| Legal Action | Compares L1 and L7; the 10th ruler represents judge/victory; the 4th ruler and Moon dispositor represent the ending; also evaluates Moon, Mercury, Jupiter, Mars/Saturn | Historical primary: Bonatti Treatise 7 | L10 support is now comparative between the parties. Both L4 and the Moon's dispositor are evaluated for the ending instead of using generic 10th/4th strength alone. |

## Primary-Source Comparison

The local primary texts used in the audit are:

- `horary_knowledge/desktop_books_text/Bonatti_on_Elections_Treatise_7_of_Guido_Bonattis_Book_of_Astronomy_Benjamin_Dykes_z-library.sk_1lib.sk_z-lib.sk.txt`
- `horary_knowledge/desktop_books_text/631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt`

Directly traceable Bonatti passages include:

- Haircut/shaving, second-house Chapter 4 (text lines around 2486): common
  signs except Gemini; Aries accepted for trimming but rejected for shaving.
- Medical/surgery chapters (text lines around 3650-3735): increasing-light
  Moon, benefic support, and avoidance of the Moon in the sign of the member
  treated with iron or fire.
- Lawsuit/contention, Chapter 14 (text lines around 4793): L10 shows victory
  and must be compared for favor toward L1 versus L7; L4 and the Moon's
  dispositor describe the end.

Morin Book 26 supplies the natal-promise limitation and the principal election
framework used by Marriage Alpha, Journey, and Battle. The audit preserved
optional natal overlays rather than turning that philosophical limitation into
a product-wide required input.

Marriage Beta, Business Beta, Estate, and Lunar Fertility are explicitly marked
as recovered-reference models because their detailed point schedules derive
from repository research of Galaxy behavior rather than from the Bonatti/Morin
primary texts. Beautification and Viral Publish are explicitly marked modern
heuristics. This prevents a source category from being inferred from the mere
presence of “traditional” planets or houses.

## Score and Precision Contracts

- `model_metadata.score_semantics` is `ordinal_within_model_run`.
- `model_metadata.cross_model_comparable` is `false`.
- `model_metadata.natal_mode` is `optional`.
- `model_metadata.natal_context_applied` states what happened in the run.
- Marriage Beta, Business Beta, and Estate must use saved birth-time quality.
  Unknown or unsafe time precision suppresses house/cusp-dependent participant
  rules but does not suppress planet-to-planet rules.
- Lunar Fertility exposes both `raw_strength` and normalized visible `score`.
  Its `level_percent` is an inspection aid, not an export filter.

## Safety and Interpretation

Surgery, Conception, and Lunar Fertility are traditional or recovered
astrological timing tools. They are not medical advice, fertility diagnosis,
ovulation estimation, or fetal-sex prediction. Election results should be
inspected as ranked symbolic candidates, not deterministic outcomes.

## Verification

Source-alignment regressions live in:

- `tests/test_election_source_alignment.py`
- `tests/test_election_model_invariants.py`
- `tests/test_election_morin_rules.py`
- `backend/test_marriage_beta_contract.py`
- `backend/test_business_beta_contract.py`
- `backend/test_estate_election_contract.py`
- `tests/test_lunar_fertility_model.py`
- `tests/test_election_route_contracts.py`

These suites cover directed lunar phase, exact Mercury station age, Bonatti's
haircut and surgery rules, the narrowed Battle prohibition, comparative Legal
support, participant precision gating, recovered line extraction, Lunar
Fertility parity behavior, API validation, and partial-failure diagnostics.
