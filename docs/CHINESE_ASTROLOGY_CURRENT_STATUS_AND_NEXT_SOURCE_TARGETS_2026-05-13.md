# Chinese Astrology Current Status And Next Source Targets

Date: 2026-05-13

## Current Status

The Chinese Astrology source-enrichment pass is implemented in source folders only. The private OCR corpus remains under `output/chinese_books_private_corpus/`, outside app build artifacts.

Implemented and verified in the current source state:

- Real regulating Useful God rows keyed by Day Stem + Month Branch for the verified Lu Zhiji slice, with season-only climate rows kept as evidence only.
- Month-command structure selection before ordinary strong/weak balancing.
- Final rulings for source-screened dominant, follow, and transformation structures, with false/failed cases withheld.
- Specific damaged-useful patterns instead of generic contact damage.
- Timing interpretation that distinguishes branch-weighted Da Yun, stem-weighted Liu Nian, rescue, damage, activation, movement, pressure, and arrival/contact.
- BaZi-first compatibility judgement before score display.
- Expanded auxiliary stars as secondary markers.
- The Life Areas tab includes `Health & Body Balance`. The requested medical/context wording has been removed from source UI strings; the card is reached through `Chinese Astrology -> Life Areas -> Health & Body Balance`.

Verification already run after implementation:

- `pytest backend/test_chinese_astrology_bazi.py -q` passed: 67 tests.
- `pytest frontend/backend/test_chinese_astrology_bazi.py -q` passed: 67 tests.
- `npm --prefix frontend run test:ui -- chineseAstrologyPage.test.jsx astroclockApi.test.mjs` passed: 46 tests.
- `npm --prefix frontend run build` passed with the existing large chunk warning.
- After the Life Areas wording removal, the focused backend mirror tests and React page test also passed.

Current dev runtime check:

- Frontend Vite responds at `http://localhost:5173/index.html`.
- Backend is listening on `127.0.0.1:52525`; the checked `/health` path returns 404, so that endpoint should not be used as the runtime health check.

## New Source Sweep

This follow-up sweep focused on not-yet-deep areas rather than rechecking what is already implemented. The most useful source clusters are:

- `lu_zhiji_bazi_advanced`, pp. 19-21 and 47-50: tiao hou climate/regulating logic, cold-warm/dry-wet scoring, and the ten-stem regulating table.
- `lu_zhiji_bazi_advanced`, pp. 79-111: stem/branch contact, activation, transformation, roots, tomb/storage, Da Yun and Liu Nian handling.
- `lu_zhiji_bazi_advanced`, pp. 148-176: spouse palace, spouse star, timing activation, marriage-event examples.
- `lu_zhiji_bazi_advanced`, pp. 299-308: body-balance correspondences by stem/branch, element condition, pillar position, and timing trigger.
- `lu_zhiji_fate_search`, pp. 219-226: bing yao disease-medicine, damaged useful god, rescue, and the warning not to over-apply "have disease, seek medicine".
- `lu_zhiji_fate_search`, pp. 280-282 and 315: source-flow and tong guan as a real useful-element path, not a footnote.
- `lu_zhiji_fate_search`, pp. 340 and 411-417: timing ying qi, host-position contact, fill-in of virtual branches, Fu Yin/Fan Yin, and day-vs-year conflict.
- `yuanhai_ziping_daquan`, pp. 37-38, 209, 227: fetal/month extras, damage summaries, and classical "use X, do not injure X" rules.
- `yuanhai_ziping_daquan`, pp. 21-29 and 181-183: auxiliary star formulas, Kong Wang, Tian Luo / Di Wang, Yang Ren, San Qi, and related marker logic.
- `sanming_tonghui_part3`, pp. 205-217 and 450-460: root/useful placement, transformation/follow cautions, body-balance examples, Yi Ma, Tao Hua, Hua Gai, San Qi, and family topics.

## Strong Next Improvements

1. Complete the full tiao hou table.

Build a full `Day Stem + Month Branch -> regulating stems` table with primary stems, secondary stems, conditions, taboos, and source references. The current engine proves the architecture, but coverage is partial. The table should make statements like `Bing Fire in Hai month requires warmth first` and then check whether that stem is present, rooted, absent, damaged, rescued, or supplied by timing.

2. Replace coarse strength with a root-grade strength model.

The books repeatedly reject raw counting. Add explicit evidence for de ling, de di, de zhu, root class, hidden-stem rank, tomb/storage roots, same-side support, opposing pressure, and "too strong / too weak / neutral". Also encode Lu's point that Resource does not fully replace a real root. This will improve Day Master strength, Useful Elements, Ten Gods weighting, and life-area confidence.

3. Upgrade ge ju to a real success/failure/rescue engine.

Current month-command structure selection is the right first step. The next version should score whether the structure is clean, mixed, damaged, rescued, or transformed. Add xiang shen, ji shen, mixed Officer/Killing, keep-Officer-combine-Killing, combine-Officer-keep-Killing, greedy-combination-forgetting-Officer, and structure-specific rescue rules. This should decide when ordinary strong/weak balancing is secondary.

4. Add tong guan as a separate useful-element path.

The sources treat tong guan as a real mechanism when two forces are opposed or when the useful path cannot flow. Add a mediator detector, e.g. Officer/Killing heavy with weak Day Master can need Resource to pass the pressure into support; strong Day Master with light Wealth can need Output to create flow. This should sit beside support/suppression, tiao hou, ge ju, and bing yao.

5. Expand sun yong / bing yao beyond the first four damage patterns.

The current source-pattern damage is much better than generic pressure, but still thin. Add severity and rescue: whether the useful god is clashed, combined away, buried, empty, root-cut, two-against-one, or rescued by a medicine. Also distinguish "control" from "transform": source examples warn that sometimes direct control is wrong and transformation is better.

6. Make timing an ying qi engine.

The app already labels activation; now it should infer event timing quality. Add rules for combination as arrival/contact, clash as movement, tomb/storage as collection, harm/piercing as injury; Da Yun setting the decade field; Liu Nian selecting the event trigger; Liu Yue/Liu Ri narrowing activation; Fu Yin/Fan Yin; fill-in of virtual branches; and timing that rescues or destroys the current useful path.

7. Improve compatibility through spouse-star and spouse-palace dynamics.

Move further away from generic compatibility scoring. For each chart, judge spouse star condition, spouse palace stability, useful-element exchange, Day Master exchange, cross-chart palace contacts, and current timing activating either spouse palace or spouse star. Then score only after the evidence judgement is formed.

8. Enrich Health & Body Balance without making clinical claims.

The Lu advanced source has enough material to improve this card: five-organ correspondences by stem/branch, pillar-position body zones, weak-element flags, excessive heat/cold/dry/damp flags, and timing triggers. The UI can keep the current `Health & Body Balance` framing and add concrete chart evidence such as "Metal is exposed and pressured by Fire in the Month pillar" instead of broad generic text.

9. Add auxiliary-star placement and timing interpretation.

The added Shen Sha formulas are useful but currently flat. Next step: interpret star placement by pillar/palace, whether the star is useful or harmful in chart context, whether it is voided by Kong Wang, and whether timing activates it. Tian Luo / Di Wang, Xian Chi/Tao Hua, Yi Ma variants, Tian Chu, Xue Tang, and more Kong Wang detail are viable candidates.

10. Add optional classical extras, but keep them out of primary scoring at first.

The corpus contains tai yuan, ming gong, na yin, and small-cycle methods. It also contains source conflict: later Zi Ping practice often avoids letting fetal pillar, small luck, or Na Yin drive the main judgement. Best product shape is an `Advanced Classical Extras` drawer that displays them as context, not as a primary Useful God or compatibility score driver.

## Recommended Implementation Order

1. Full tiao hou table with fixtures for every Day Stem + Month Branch row.
2. Strength/root-grade model and UI evidence rows.
3. Ge ju v2 with xiang shen, ji shen, success/failure/rescue, and mixed-structure handling.
4. Tong guan and bing yao v2 as separate useful-element paths.
5. Ying qi timing engine for Da Yun, Liu Nian, Liu Yue, Liu Ri.
6. Relationship/compatibility v2 using spouse palace, spouse star, and timing activation.
7. Health & Body Balance enrichment from element/stem/pillar evidence.
8. Auxiliary-star placement/timing interpretation and optional classical extras.

## Implementation Guardrails

- Any new table copied from OCR must be verified against page images before release.
- No generated/package artifact edits.
- Keep full OCR text private; docs should use page references and paraphrase.
- Add source fixtures before finalizing a rule family.
- Do not let I Ching Oracle logic change from this BaZi corpus; the books do not provide standalone oracle casting rules.
