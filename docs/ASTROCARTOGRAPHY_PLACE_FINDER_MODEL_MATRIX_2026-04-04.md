# Astrocartography Place Finder Model Matrix

Date: 2026-04-04

## Purpose

This memo reverse-engineers the legacy Almagest place-finder profiles into an English model matrix and defines how Vox Stella should reinterpret them.

Reference source folder:

- `C:\Users\sabaa\Desktop\Almagest8ORIGNAL`

Key legacy files inspected:

- `Educ.pls`
- `Love.pls`
- `WorkL.pls`
- `GMU 01c.PLS`
- `CAREER.HYP`
- `LOVE.HYP`
- `WORK.HYP`
- `MONEY.HYP`
- `BELIEFS.HYP`
- `PERSONAL.HYP`
- `PARTNERS.HYP`
- `HOME.HYP`
- `FRIEND.HYP`
- `SEX.HYP`
- `CHATTER.HYP`
- `ENEMIES.HYP`

## High-Level Finding

The legacy place-finder does not appear to use one single black-box model.

It appears to use at least two profile grammars:

- `.pls`: user-facing place-finder presets
- `.HYP`: domain-specific rule packs or interpretation-weight templates

The first Vox Stella implementation should not copy the legacy field grammar directly. It should preserve the idea of weighted goal profiles while replacing opaque field names with explicit JSON.

## Confirmed Visibility Split

The `Optimal Place Finder` dropdown shown in the UI appears to be driven by exactly four user-facing `.PLS` presets:

- `Educ.pls`
- `GMU 01c.PLS`
- `Love.pls`
- `WorkL.pls`

Evidence:

- these are the only `.PLS` files in the folder
- all four expose clear `[OPTIONS]` headers
- the decoded headers match the four visible dropdown labels:
  - `Obrazovanie` -> `Education`
  - `Dengi, Testovaya Model Ver.0.1c` -> `Money, Test Model Ver.0.1c`
  - `Lyubov` -> `Love`
  - `Rabota` -> `Work`

So the screenshot is not hiding additional same-level user presets under different filenames. At the visible preset layer, there are four.

What does exist beyond those four is a second hidden model family:

- `.HYP` domain rule packs

This is supported by:

- `MODELMAK.MNU`, whose header decodes to `BlackBox Model Editor`
- `MODELMAK.MNU` launching `Hyped.exe`
- the string `Events File|*.HYP` inside `Almaatla.exe`

Conclusion:

- there are exactly four visible place-finder presets in this workflow
- there are additional underlying hidden models in `.HYP` format
- the old app therefore has a two-layer model system, not just four total models

## Legacy Grammar Summary

### `.pls` profiles

Observed characteristics:

- human-facing topic headers in Russian
- `STYLE` switch in `[OPTIONS]`
- large collections of `EventN` blocks
- simple weight fields
- fields like `P0`, `P1`, `P2`, `P4`, `P5`, `P6`
- one test model uses additional `RS*` fields and a smaller event set

Interpretation:

- these look like place-ranking presets
- `STYLE=1` looks like the older stable topic-profile format
- `STYLE=0` plus `RS*` fields looks like an experimental or alternate scoring grammar

### `.HYP` profiles

Observed characteristics:

- mostly `80` event blocks each
- repeated field pattern:
  - `WEIGHT`
  - `A1`
  - `A11`
  - `A2`
  - `A4`
  - `A44`
  - `A5`
  - `A6`
  - `A8`
  - `A9`
- most domain files share nearly the same structure
- one category-specific numeric token varies by file

Interpretation:

- these look like reusable domain scoring packs built on one common rule template
- the numeric token likely identifies the domain family while the surrounding event structure remains shared
- `CAREER.HYP` is structurally related but clearly tuned more softly than the others
- they are likely authorable through the separate `Hyped.exe` / `BlackBox Model Editor` tooling rather than directly through the place-finder dropdown

## English Translation Matrix

### Place-finder `.pls` presets

| Legacy file | Russian header | English label | Style | Event count | Findings |
| --- | --- | --- | --- | --- | --- |
| `Educ.pls` | `Obrazovanie` | `Education` | `1` | `192` | Stable preset grammar. Strongest visible weights in the early sequence sit on `P2=3` and `P2=9`, with a smaller positive on `P2=1`. |
| `Love.pls` | `Lyubov` | `Love` | `1` | `192` | Stable preset grammar. Strong visible weights on `P2=5` and `P2=7`, moderate support on `P2=1`, `3`, `11`, and smaller support on `4`, `10`. |
| `WorkL.pls` | `Rabota` | `Work` | `1` | `210` | Stable preset grammar. Strong visible weights on `P2=7` and `P2=10`, then `8`, then `3` and `6`, with minor support on `1`, `2`, `11`. |
| `GMU 01c.PLS` | `Dengi, Testovaya Model Ver.0.1c` | `Money (Test Model v0.1c)` | `0` | `35` | Experimental or alternate grammar. Uses `P*` and `RS*` fields together. Looks like a prototype scoring profile rather than the canonical production format. |

### Domain `.HYP` rule packs

| Legacy file | English label | Event count | Distinctive token | Findings |
| --- | --- | --- | --- | --- |
| `CAREER.HYP` | `Career` | `80` | none clearly isolated | Uses the same family of fields but lighter and more varied weights. Looks custom-tuned rather than cloned from the generic domain template. |
| `LOVE.HYP` | `Love` | `80` | `29` | Generic domain template with a love-specific token embedded into `A11` and `A44`. |
| `WORK.HYP` | `Work` | `80` | `30` | Same generic domain template with work token. |
| `MONEY.HYP` | `Money` | `80` | `26` | Same generic domain template with money token. |
| `BELIEFS.HYP` | `Beliefs` | `80` | `33` | Same generic domain template with beliefs token. |
| `PERSONAL.HYP` | `Personal` | `80` | `25` | Same generic domain template with personal-development token. |
| `PARTNERS.HYP` | `Partners` | `80` | `31` | Same generic domain template with partnership token. |
| `HOME.HYP` | `Home` | `80` | `28` | Same generic domain template with home/family token. |
| `FRIEND.HYP` | `Friends` | `80` | `35` | Same generic domain template with friendship token. |
| `SEX.HYP` | `Sex / Intimacy` | `80` | `32` | Same generic domain template with intimacy token. |
| `CHATTER.HYP` | `Communication / Chatter` | `80` | `27` | Same generic domain template with communication token. |
| `ENEMIES.HYP` | `Enemies / Conflict` | `80` | `36` | Same generic domain template with conflict token. |

## Structural Findings

### 1. The legacy system separates topic selection from rule execution

The old app likely works in two layers:

- a topic preset layer (`.pls`)
- a deeper rule-pack layer (`.HYP`)

That is a good product architecture to preserve.

### 2. Most legacy domains are parameterized copies of a shared template

The `.HYP` files for love, work, money, beliefs, personal, partners, home, friends, sex, chatter, and enemies are nearly identical except for the embedded category token.

That suggests the old app was doing:

- one generic scoring grammar
- per-domain token substitution
- domain-specific weight interpretation at runtime

This is useful because Vox Stella should likewise avoid hard-coding every topic as a separate custom engine.

### 3. Career is special

`CAREER.HYP` does not simply mirror the generic `-2/-4/+5/+4` pattern used by the other domains.

It uses softer and more granular weights such as:

- `-0.5`
- `0.75`
- `0.6`
- `0.5`
- `0.25`
- `-0.75`

This suggests the legacy app treated career scoring as a more nuanced or more conservative domain.

### 4. Money appears under two systems

There is both:

- `MONEY.HYP`
- `GMU 01c.PLS` with header `Money, Test Model Ver.0.1c`

This suggests the money model was actively experimented on and should not be treated as fully stable in the legacy system.

## Inferred Preset-To-Rule-Pack Pairings

No direct plain-text filename binding between the four visible `.PLS` presets and the hidden `.HYP` rule packs was recovered from:

- the `.PLS` files themselves
- the `.HYP` files themselves
- readable strings inside `Almaatla.exe`

So the matrix below is an inference layer, not a proven runtime linkage table.

| Visible preset | Primary hidden pairing | Confidence | Secondary candidates | Basis |
| --- | --- | --- | --- | --- |
| `Educ.pls` | none directly matched | low | `BELIEFS.HYP`, `CHATTER.HYP` | There is no `EDUCATION.HYP`. Education semantics are closest to worldview/learning/communication-style domains, but this remains speculative. |
| `Love.pls` | `LOVE.HYP` | high | `PARTNERS.HYP` (medium), `SEX.HYP` (low) | Direct label match on the primary domain. The adjacent relationship-oriented packs look like likely secondary overlays rather than the main dropdown target. |
| `WorkL.pls` | `WORK.HYP` | high | `CAREER.HYP` (medium) | Direct label match on the main domain. `CAREER.HYP` looks like a distinct softer-tuned vocational pack and is likely related but not identical to the visible work preset. |
| `GMU 01c.PLS` | `MONEY.HYP` | high | none clearly indicated | Direct label match on money. The file also identifies itself as a test model, which fits the idea of a visible money preset sitting beside a deeper hidden money rule pack. |

Working interpretation:

- the visible dropdown chooses a user-facing topic preset
- the hidden `.HYP` family provides a deeper domain-rule layer
- some visible presets probably map to one main hidden domain pack plus optional adjacent domain packs
- `Education` is the only visible preset without a direct same-name hidden counterpart

## Recommended Vox Stella Goal Set

### First release

- `education`
- `love`
- `work`
- `money`

### Second wave

- `career`
- `home`
- `partners`
- `personal`
- `friends`
- `beliefs`

### Third wave

- `sex_intimacy`
- `communication`
- `conflict`

## Recommended Vox Stella Interpretation

The new system should not preserve opaque numeric axes like `P2=7` or `A11=*29`.

Instead, each goal model should be re-expressed as explicit factors such as:

- line weights by `planet` and `angle`
- distance scaling rules
- crossing/paran weights
- relocation chart weights
- optional caution weights
- explanation tags

## Proposed English Goal Matrix

This is the English product matrix we should build toward.

| Goal id | Label | Purpose | MVP status |
| --- | --- | --- | --- |
| `education` | `Education` | learning, study, teaching, academic development | phase 1 |
| `love` | `Love` | romance, attraction, emotional partnership fit | phase 1 |
| `work` | `Work` | day-to-day work environment and practical activity | phase 1 |
| `money` | `Money` | earning, commerce, material opportunity | phase 1 |
| `career` | `Career` | visibility, vocation, professional ascent | phase 2 |
| `home` | `Home` | domestic comfort, rootedness, family support | phase 2 |
| `partners` | `Partners` | long-term alliances, collaboration, formal partnership | phase 2 |
| `personal` | `Personal Growth` | self-development, identity, life direction | phase 2 |
| `friends` | `Friends` | affinity, community, social ease | phase 2 |
| `beliefs` | `Beliefs` | worldview, spirituality, conviction, meaning | phase 2 |
| `sex_intimacy` | `Sex / Intimacy` | erotic chemistry, embodied attraction | phase 3 |
| `communication` | `Communication` | networking, conversation, expression | phase 3 |
| `conflict` | `Conflict / Enemies` | friction, rivalry, adversarial environments | phase 3 |

## Recommended Scoring Strategy For Vox Stella

Each goal should be scored as a weighted combination of:

- nearby line strengths
- line distance attenuation
- crossings/parans
- relocation-chart emphasis
- optional caution modifiers

Suggested conceptual scoring layers:

- `line_score`
- `crossing_score`
- `relocation_score`
- `stability_adjustment`
- `goal_total`

## What To Preserve From The Legacy App

- topic-driven place search
- reusable goal profiles
- support for both positive and negative factors
- explainable weighted scoring

## What To Replace

- opaque field names
- hidden category tokens
- duplicated per-topic rule files
- hard-to-maintain custom formats

## Recommended New Storage Format

Vox Stella should use:

- explicit JSON goal models
- one schema for validation
- one model catalog for topic registration
- optional per-goal explanation text stored beside the scoring rules

The new schema lives at:

- `backend/knowledge/astrocartography/place_goal_model.schema.json`

The extracted legacy matrix lives at:

- `backend/knowledge/astrocartography/legacy_almagest_place_goal_matrix.json`

## Confidence Notes

What is high confidence:

- the old system is profile-driven
- `.pls` and `.HYP` are two distinct rule grammars
- most `.HYP` files share one common template
- the Russian topic labels translate cleanly into English goal categories

What remains low confidence:

- the exact semantic meaning of each legacy field such as `P2`, `A1`, or `A44`
- the precise internal meaning of the category token numbers
- the exact runtime relationship between `.pls` and `.HYP`

That uncertainty is acceptable because the right move is not to clone the old field grammar. The right move is to preserve the legacy topic model while replacing the old storage and scoring language with explicit, explainable JSON.
