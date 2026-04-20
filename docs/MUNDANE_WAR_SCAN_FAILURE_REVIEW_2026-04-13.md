# Mundane War Scan Failure Review

## Scope

This review inspects the two failing war-scan hindcast cases from the current suite:

- `war_scan_hindcast_desert_storm_outbreak_1991`
- `war_scan_hindcast_pearl_harbor_outbreak_1941`

The review is split into:

1. source doctrine
2. atlas / region coverage
3. runtime scan behavior
4. likely fix direction

## Desert Storm Outbreak 1991

### Source Doctrine

The current local source is not purely a Baghdad-locality source.

Annotated Raphael says:

- Bush would go to war against Iraq around the January 15, 1991 solar eclipse
- Desert Storm began on January 17, 1991
- the war then lasted 38 days

That is strong support for:

- war timing
- eclipse proximity
- opening-war doctrine

It is weaker support for:

- exact top-1 Baghdad localization inside a Persian Gulf city field

So the current benchmark is slightly harder than the source claim itself.

### Atlas / Region Behavior

The region is doctrinally reasonable:

- `persian_gulf`

The scan field is also reasonable:

- Baghdad is present
- Tehran is present
- Gulf cities are present

So this failure is not an atlas-missing-target problem.

### Runtime Behavior

The target place survives:

- Baghdad rank `6`
- target-window peak score `43`
- target-window peak datetime `1991-01-17 12:00 +03:00`

The actual failure is narrower:

- Baghdad's own series repeats the same top score across multiple nearby slices
- a matched control window ties the same peak score
- higher-ranked Gulf cities outperform Baghdad on breakout index and peak score

So the runtime is recovering broad theater pressure, but it is not isolating Baghdad as the clear opening-air-war hotspot.

This looks like:

- broad regional war pressure outranking target-city concentration
- insufficient opening-hostilities localization inside the Persian Gulf field
- plateau behavior making control-window discrimination too weak

### Likely Fix Direction

Most justified:

- sharpen war-event opening-hostilities weighting for direct target cities versus supportive rear-area Gulf cities
- strengthen first-strike locality concentration inside the first 24 to 48 hours
- add a separate scan diagnostic for repeated equal-peak windows so tie-driven failures are easier to distinguish from true misses

Less justified:

- simply loosening the benchmark threshold further

## Pearl Harbor Outbreak 1941

### Source Doctrine

Watters is clear about outbreak-war doctrine:

- the war chart begins with first hostilities
- the first house tracks the aggressor
- the seventh tracks the defender

Watters also explicitly discusses Pearl Harbor in national-chart terms.

That supports:

- Pearl Harbor as a real war-outbreak anchor
- outbreak logic at the actual Pacific attack location

### Atlas / Region Behavior

This is where the biggest product limitation appears.

Facts from the current atlas:

- `country:us` does include Honolulu
- Honolulu sits at candidate rank `19`
- Charleston sits at rank `74`

Facts from current thematic regions:

- there is `middle_east`
- there is `levant`
- there is `persian_gulf`
- there is no Pacific / Hawaii / Pacific-theater region

So Pearl Harbor is being forced through:

- `country:us`

instead of a theater-appropriate Pacific field.

That means the scan is competing Honolulu against many continental U.S. cities in a geometry that does not resemble the doctrinal war theater.

### Runtime Behavior

The target place survives:

- Honolulu rank `18`

The target window also does technically hit:

- Honolulu peak datetime `1941-12-07 00:00 -10:00`

But the series is flat:

- Honolulu score `8` at every sampled slice

And the whole scan is dominated by unrelated mainland locations:

- Chula Vista
- Anaheim
- Irvine
- Long Beach
- Sacramento

So this is not a near-miss on Pearl Harbor timing.

It is a locality / theater-geometry failure:

- the target survives
- but the runtime does not meaningfully privilege the actual Pacific attack theater
- the target series is flat and low, so matched controls tie it automatically

### Likely Fix Direction

Most justified:

- add a Pacific / Hawaii / Pacific-theater scan region before treating Pearl Harbor as a fair scan-localization benchmark
- keep Pearl Harbor in the suite as a documented stress case until that region exists
- do not treat this failure as pure scoring weakness alone

Less justified:

- over-tuning war scoring against the current `country:us` field

That would solve the wrong problem.

## Combined Assessment

The two failures are different.

### Desert Storm

Primary issue:

- scan scoring and window discrimination inside a plausible theater

### Pearl Harbor

Primary issue:

- atlas / theater geometry mismatch

## Recommended Order

1. Add a Pacific-theater region for war scans.
2. Re-run Pearl Harbor before changing war-outbreak scoring around that case.
3. Tighten war-event opening-hostilities localization for the first 24 to 48 hours in Gulf-style outbreak scans.
4. Re-run the hindcast suite and only then decide whether benchmark thresholds should move.
