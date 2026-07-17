# Forensic Worst Ex Ever Benchmark Plan - 2026-05-08

## Scope

This benchmark moves the forensic evaluation from biography/personality claims into event-chart replay.
The goal is to compare the engine output against known event families from Netflix's `Worst Ex Ever` cases:

- intimate-partner violence and coercive control
- kidnapping, confinement, or forced movement
- family/custody violence
- murder-for-hire or deception-by-proxy
- fatal versus survivor outcome direction

Netflix is used only as the discovery index. Fixture truth labels must come from court opinions,
prosecutor releases, police records, or stable reporting. The benchmark remains directional:
we assert that the top event axes match real events, not that the engine reproduces every narrative detail.

## Implementation Policy

Runnable cases need an event anchor strong enough for chart replay:

- `high`: court/prosecutor/police source gives date, local time or tight response time, and location.
- `medium`: source gives date and a tight window, or the time is a court-supported response/proxy anchor.
- `holdout`: the case is useful, but the public source set does not yet support a defensible replay time.

Each runnable fixture freezes:

- event anchor and source basis
- expected primary and secondary axes
- contradictory axes
- current comparison baseline
- expected survivability direction

Current comparison baselines are not marketing claims. `partially_aligned` and `misaligned` cases are useful because
they expose drift and make future rule changes measurable without adding case-id exceptions.

## Runnable First Batch

| Case | Episode | Anchor | Benchmark reason | Expected primary axes |
| --- | --- | --- | --- | --- |
| Geoffrey Paschel / Kristen Wilson Chapman | Season 2, "Primetime Predator" | June 9, 2019, about 11:00 p.m., Knoxville, TN | Survivor control for intimate-partner assault plus confinement and blocked emergency help. | domestic partner, abduction/confinement, violence |
| Alisha Canales-McGuire / Kevin Lewis | Season 1, "Married to a Monster" | September 20, 2017, 1:55 a.m. 911 call, Everett, WA | Fatal domestic-by-proxy / murder-for-hire shooting with mistaken target. | homicide, domestic-by-proxy, deception |
| Rosa Hill / Mei Li / Eric and Selma Hill | Season 1, "Killing for Custody" | January 7, 2009, 5:53 p.m. deputy arrival, Dublin, CA | Custody/family attack with child present, attempted murder survivor, and already completed elder homicide. | family/custody, child, violence, domestic/custody |
| Scott Freeman / Karen Kummerer | Season 2, "Ride or Die" | November 27, 2006, morning trunk ambush proxy, Daytona Beach, FL | Survivor route-abduction case after injunction violation; good test for forced movement without fatal outcome. | abduction, domestic partner, route/vehicle |

## Holdout Candidates

These should stay documented but should not become hard replay assertions until their event anchors are improved.

| Case | Why useful | Why held |
| --- | --- | --- |
| Wade Wilson / Kristine Melton and Diane Ruiz | Double homicide, vehicle movement, opportunistic second victim, later death sentence. | Public prosecutor source confirms October 7, 2019 and Cape Coral, but not a precise replay time for either murder. Split into separate Melton and Ruiz anchors once trial/probable-cause timing is sourced. |
| Benjamin Foster / Justine Siemens | Extreme survivor IPV, confinement, later manhunt/standoff and suspected double homicide while fleeing. | Discovery and standoff times are better sourced than assault onset; split into survivor discovery, Sunny Valley double homicide, and standoff anchors before automation. |
| Jerry Ramrattan / Seemona Sumasar | Deception, false police reports, legal weaponization, sexual assault survivor. | Excellent deception benchmark, but the public source set needs exact or tight timing for the assault and later false-report anchors. |
| Joyce Pelzer / Shawndell McLeod / Rosalyn Lewis | Missing-person/no-body homicide plus later fatal stabbing and flight. | Needs source separation between the 2011 missing-person homicide and the 2018 motel stabbing; each should be benchmarked as a separate event. |

## Source Basis

- Netflix Tudum, Season 1 overview: `https://www.netflix.com/tudum/articles/worst-ex-ever-release-date-news`
- Netflix Tudum, Season 2 overview: `https://www.netflix.com/tudum/articles/worst-ex-ever-season-2-release-date-news`
- Tennessee Court of Criminal Appeals, `State of Tennessee v. Geoffrey Ian Paschel`: `https://www.tncourts.gov/courts/court-criminal-appeals/opinions/2023/09/14/state-tennessee-v-geoffrey-ian-paschel`
- Washington Courts, Kevin Lewis petition record: `https://www.courts.wa.gov/content/petitions/102751-6%20Petition%20for%20Review.pdf`
- California Court of Appeal, `People v. Rosa Pui Hill et al.`: `https://cases.justia.com/california/court-of-appeal/2015-a133121.pdf?ts=1431550820`
- Florida Fifth District Court of Appeal, `Freeman v. State`: `https://law.justia.com/cases/florida/fifth-district-court-of-appeal/2009/5d07-4337.html`
- Florida State Attorney, Wade Wilson double homicide release: `https://sao20.org/news-releases/jury-recommends-the-death-penalty-for-killer-wade-wilson/`
- CBS New York, Jerry Ramrattan sentencing coverage: `https://www.cbsnews.com/newyork/news/queens-man-convicted-of-raping-framing-ex-girlfriend-gets-prison/`

## Current Gaps to Watch

- Domestic-by-proxy can be missed when the chart does not emit explicit partner wording even though the real event is spouse/estranged-spouse driven.
- Custody cases can drift into generic domestic wording while missing child/family custody context.
- Route-abduction survivor cases can pick up false family/child contradictions from broad 4th/5th testimony.
- Fatality scoring is reliable on some fatal anchors, but date-only homicide proxies should not be promoted until exact timing is sourced.

## Validation

Implemented by:

- `tests/fixtures/forensic_worst_ex_ever_cases.json`
- `tests/test_forensic_worst_ex_ever_benchmarks.py`

Run with:

```powershell
python -m pytest tests\test_forensic_worst_ex_ever_benchmarks.py -q
```
