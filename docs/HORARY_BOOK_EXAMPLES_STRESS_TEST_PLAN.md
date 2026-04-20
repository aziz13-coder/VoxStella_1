# Horary Book Examples Stress-Test Plan

Primary source file:
`C:\Users\sabaa\Downloads\Horary Examples Traditional Horary Astrology By Example ( etc.) (z-library.sk, 1lib.sk, z-lib.sk).epub`

Goal:
Use the worked examples in the book as a structured external corpus to stress-test the horary engine for doctrinal correctness, while protecting Astro Clock and every feature that depends on shared horary/chart helpers.

## Implementation Status

Phase 1 through Phase 5 are now implemented for the first deterministic replay slice.
Phase 6 is partially implemented: the remaining unresolved case from the first slice has been isolated as a deeper chained-state/property-transfer problem, not another safe routing bug.
The second replay slice now has both harness coverage and a completed rule-fix pass for Relationship plus Pregnancy & Children.
The third replay slice now has harness coverage for Health / death-edge cases, with disagreement classes isolated for the next rule-fix pass.
The third replay slice now also has a completed phase 5/6 pass for the fixable health disagreement classes.
The fourth and fifth replay slices now extend the harness into Lost & Found plus Contests/public-event questions, with a completed phase 5/6 doctrine pass for the rule-level cases that generalized safely.

Artifacts:

- extractor script:
  - `C:\Users\sabaa\Downloads\codexhorary\scripts\extract_horary_book_corpus.py`
- generated corpus:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_corpus.json`
- structure validation test:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_corpus.py`
- replay fixture:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_book_examples_replay.json`
- backend replay helper:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\horary_book_examples_utils.py`
- backend replay tests:
  - `C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_book_examples_replay.py`
- frontend parity tests:
  - `C:\Users\sabaa\Downloads\codexhorary\frontend\src\tests\horaryBookExamplesParity.test.mjs`
- replay results note:
  - `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_PHASE_3_4_RESULTS.md`
- phase 5/6 implementation note:
  - `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_PHASE_5_6_RESULTS.md`
- second-slice results note:
  - `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_2_RESULTS.md`
- fourth/fifth-slice phase 5/6 note:
  - `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_4_5_PHASE56_RESULTS.md`

Current corpus summary:

- total case entries: `64`
- `tier_1_deterministic_candidate`: `18`
- `tier_2_replay_ready_doctrinal_review`: `46`
- `tier_3_manual_review_only`: `0`

Important note:

- the current EPUB extraction found explicit header date, time, and location for all 64 case chapters
- that means the initial split is mostly between deterministic candidates and doctrinal-review cases, not between metadata-complete and metadata-missing cases
- some cases may still be downgraded later if deeper chapter review reveals altered details, ambiguous location wording, or interpretation too broad for deterministic replay

Phase 3/4 first-slice summary:

- replay fixture cases implemented: `10`
- source-aligned at primary route level: `2`
- verdict-aligned but route-misaligned: `6`
- verdict-disagreement cases: `2`

Current Phase 5/6 status for the same 10-case slice:

- source-aligned at route and verdict level: `9`
- remaining explicit disagreement: `1`
- remaining disagreement id: `will_we_rent_the_house`

Current second-slice replay status:

- additional replay cases implemented: `8`
- cumulative replay cases implemented: `18`
- cumulative source-aligned cases: `17`
- cumulative explicit disagreement cases: `1`
- notable analyzer fix: first-person fertility wording like `my own child` now stays on `L1/L5` instead of being falsely turned into a third-person child chart

Second-slice status:

- source-aligned cases: `8/8`
- disagreement ids: `none`

Current third-slice replay status:

- additional replay cases implemented: `6`
- cumulative replay cases implemented: `24`
- cumulative source-aligned cases: `22`
- cumulative explicit disagreement cases: `2`

Third-slice status:

- source-aligned cases: `5/6`
- disagreement ids:
  - `will_we_rent_the_house`
  - `will_grandfather_survive_this_time`
- current disagreement classes isolated for phase 5/6:
  - maternal-grandfather death derivation

Third-slice phase 5/6 note:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_3_PHASE56_RESULTS.md`

Current fourth/fifth-slice replay status:

- additional replay cases implemented: `6`
- cumulative replay cases implemented: `30`
- cumulative source-aligned cases: `27`
- cumulative explicit disagreement cases: `3`

Fourth-slice note:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_4_LOST_FOUND_RESULTS.md`

Fifth-slice note:

- `C:\Users\sabaa\Downloads\codexhorary\docs\HORARY_BOOK_EXAMPLES_SLICE_5_CONTEST_RESULTS.md`

Newest disagreement classes isolated for the next fix passes:

- contextual contest identification where the title alone does not explicitly name office or incumbent status
- contextual kinship derivation where the title alone does not explicitly encode the maternal branch
- chained ownership/state questions after a property sale or transfer

## Why This Book Is Useful

The EPUB already provides a broad spread of question families that match the app's current surface area:

- Contests
- Money & Jobs
- Housing
- Relationship
- Pregnancy & Children
- Health
- Lost & Found
- Miscellaneous / public-event questions

That makes it suitable for both:

- correctness checks against real horary examples
- regression checks across multiple engine branches, especially category routing, significator selection, turned houses, perfection, and reception logic

## Core Rule For This Project

The book is a source of examples and worked judgments. It is not by itself the only doctrinal authority.

For each case we should distinguish:

- `book outcome`: what the example says happened or how it judged the chart
- `book rationale`: the reasoning given in the example
- `engine result`: what our backend currently returns
- `doctrinal baseline`: Lilly-first judgment when the book's rationale is compressed, modernized, or ambiguous

The engine should never be changed simply to mimic a single published answer. Changes must target the underlying rule or routing fault.

## Required Safety Constraint

No horary change is allowed to land without checking shared consumers.

At minimum, each fix must be reviewed against:

- `/api/calculate-chart`
- saved/rerun horary flows
- frontend verdict display parity
- Astro Clock shared chart consumers
- receptions/dignities/significator utilities if touched

If a rule is implemented in shared helpers, Astro Clock regression checks must be run before considering the change safe.

## Planned Workflow

### Phase 1: Build a Book Corpus Inventory

Create a machine-readable inventory from the EPUB table of contents and chapter files.

Each case entry should capture:

- book section
- example title
- EPUB chapter file
- expected question family
- whether the chapter appears to include:
  - exact date
  - exact time
  - exact location
  - house system
  - explicit verdict
  - explicit outcome/result
- whether the example is immediately replay-ready or manual-review only

Initial sections to inventory from the EPUB TOC:

- Contests
  - `Will Deirdre Be Sent Down?`
  - `Will Brazil Beat Argentina?`
  - `Will Barrett Win?`
  - `Will the Champion Retain His Belt?`
  - `Has X Won the Election?`
  - `Will Romney Win the US Presidency?`
  - `Will Brazil Win the 2014 World Cup?`
  - `Will the Brewers Make the Playoffs?`
  - `When Will I Win the Money from This Trial?`
  - `Will the Badgers Win the Rose Bowl?`
- Money & Jobs
  - `Will I Get a Good Yearly Review of My Work?`
  - `Will My Tenant Send Full Payment?`
  - `Will I Get the Job at UW?`
  - `Will I Profit from This Bet?`
  - `Should I Make This Trip or Open a Co-Working Spot?`
  - `Should I Start This Business?`
  - `When Will We Get Paid from X?`
  - `Will Investing in This Business Prove Profitable for Me?`
- Housing
  - `Will We Be Flooded?`
  - `Should I Stay Here or Move Back to X?`
  - `Will the Bank Foreclose?`
  - `Should I Move to My Friend’s House?`
  - `When Will the House Get Rented? Will We Need to Hire an Agent?`
  - `Should I Buy This Flat?`
  - `Will We Rent the House?`
- Relationship
  - `Will the Relationship Last?`
  - `Will I Be Any Happier If I Leave Him?`
  - `Any Chance of a Romance with X?`
  - `Is There Any Hope for Us Getting Back Together? Should I Wait for Her?`
  - `Will She Talk to Me Again? Am I Important to Her?`
  - `Will I Find a New Relationship and When?`
- Pregnancy & Children
  - `Will I Conceive?`
  - `When Will The Baby Come?`
  - `Will They Put the Baby Up for Adoption?`
  - `Am I Pregnant?`
  - `When Will My Friend Have Her Baby?`
  - `Is There Anything Wrong With the Baby? When It Will Be Born?`
  - `Any Chance of Having My Own Child?`
- Health
  - `Where’s the Inflammation?`
  - `Am I Overworking?`
  - `What’s the Problem With My Stomach? What Can I Do to Relieve It?`
  - `Will Dad Die Soon? If So, When?`
  - `Will Mum’s Tumor Stop Growing?`
  - `Will I Die Soon?`
  - `Will Darryl Die?`
  - `Is It Multiple Sclerosis?`
  - `Will My Dog Get Better? Will It Survive?`
  - `Will Zaza Recover?`
  - `Will Grandfather Survive This Time?`
- Lost & Found
  - `Where Is My ATM Card?`
  - `Where Is My Scarf?`
  - `Where Is the Tape?`
  - `Where’s My Passport?`
  - `Where’s My Notebook?`
  - `Where is my pendant? Did I misplace it or was it stolen?`
- Miscellaneous
  - `Are the Electrical Parts I Bought Fake or Original?`
  - `Will Britain Join the Euro?`
  - `What Time Tomorrow Will the Wine Arrive?`
  - `When Will the Power-Cut End?`
  - `Will My Daughter Get the Funded Spot?`
  - `Will the Thief Come Back?`
  - `When Will the Internet Be Cut Off?`
  - `Will Scotland Leave the UK?`
  - `The Kidnapped Priest`

### Phase 2: Split Cases Into Test Tiers

Each book example must be assigned to one of three tiers:

- `Tier 1: deterministic replay-ready`
  - exact chart metadata can be recovered with confidence
  - verdict is explicit enough to assert
  - useful for automated backend tests
- `Tier 2: replay-ready with doctrinal review`
  - chart can be reconstructed, but expected result needs source comparison
  - useful for regression plus manual review
- `Tier 3: manual-review only`
  - metadata is incomplete, chart is anonymized, or the case is too interpretive
  - useful for audit reports and doctrine notes, not strict pass/fail automation

No case should be promoted into deterministic automation unless the chart data is trustworthy enough to replay.

### Phase 3: Extract What the Engine Must Match

For each replayable case, record:

- expected category
- expected question family
  - occurrence
  - advisability/quality
  - timing
  - discovery/lost object
  - third-person
  - death/health distinction
- expected primary houses
- expected significators
- expected verdict direction
- expected key testimonies
  - reception
  - perfection or lack of perfection
  - Moon testimony
  - turned houses
  - debility/combustion/cadency if central

This is important because correctness is not just `YES` or `NO`. The route and reasoning also need to be right.

### Phase 4: Build the Engine Replay Harness

Add a dedicated book corpus fixture and replay helpers.

For each deterministic case, run:

- question analysis
- horary engine judgment
- serialized chart output
- frontend normalization/parity

Each replay should assert at least:

- category matched
- relevant houses are correct
- significators are correct
- verdict direction is correct
- perfection type is plausible
- key reasoning contains the right core testimonies

### Phase 5: Add Frontend and Astro Clock Safety Gates

After every horary fix, rerun:

- backend horary corpus tests
- frontend parity tests for horary result display
- Astro Clock shared tests that depend on chart transformation, receptions, or shared evaluation helpers

At minimum the safety suite should include:

- horary backend corpus
- frontend verdict normalization/parity
- Astro Clock API shape tests
- receptions/chart bundle tests if shared helpers changed

If a change touches shared chart utilities, also rerun election and context-layer tests that consume the same helpers.

### Phase 6: Apply Fixes By Fault Type, Not By Example

Allowed fix classes:

- category router faults
- question family classification faults
- turned-house/significator faults
- perfection selection faults
- reception weighting faults
- Moon testimony ordering faults
- serialization or frontend parity faults

Not allowed:

- chart-specific answer forcing
- patches that only make one example pass without fixing the general rule

Every fix should be documented as:

- faulty current rule
- correct general rule
- affected case families
- shared dependency risk
- regression coverage added

## Recommended Execution Order

Start with the families most likely to expose current engine weaknesses while still being safe to reason about:

1. Money & Jobs
   - strong overlap with current career/profit logic
   - good for L1/L10/L2/L11 routing tests
2. Housing
   - good for property/advisability logic and L4/L2/L10 weighting
3. Relationship
   - good for affection vs outcome splits and reception logic
4. Health / death-edge cases
   - good for turned houses and explicit death routing
5. Lost & Found
   - good for object-location logic and special-purpose reasoning
6. Contests / public-event questions
   - good for competition/politics handling and third-party routing

## Concrete First Slice

The first stress-test slice from this book should aim for 10 to 12 cases:

- `Will I Get the Job at UW?`
- `Will I Get a Good Yearly Review of My Work?`
- `Will My Tenant Send Full Payment?`
- `Will Investing in This Business Prove Profitable for Me?`
- `Should I Buy This Flat?`
- `Will the Bank Foreclose?`
- `Any Chance of a Romance with X?`
- `Will She Talk to Me Again? Am I Important to Her?`
- `Will I Conceive?`
- `Will Dad Die Soon? If So, When?`
- `Where’s My Passport?`
- `Will My Daughter Get the Funded Spot?`

This first slice gives a broad test of:

- career and salary logic
- property and advisability logic
- relationship reciprocity logic
- child/pregnancy routing
- third-person health/death routing
- lost-object logic
- turned-house public/relative questions

## Output Expectations

The final deliverables for this project should be:

- a book-derived machine-readable corpus
- a deterministic automated subset
- a manual-review subset
- a correctness audit report for disagreements
- category-local fixes with Astro Clock-safe regression coverage

## Completion Standard

The book stress-test project should be considered successful only when all of the following are true:

- the corpus is structured and replayable
- deterministic cases assert more than just verdict polarity
- engine disagreements are investigated at the rule level
- frontend does not drift from backend verdicts
- Astro Clock and other shared consumers remain green after each fix
