# Muhammad Ali and James Dean Birth Certification Runs

Date: 2026-05-22

## Purpose

Continue the Vox Stella Birth Certification blog validation set after the Queen Elizabeth II run.

The same workflow was used for each chart:

1. Run the known birth time with `source_time_status = aa` and a one-minute search window.
2. Run a blind validation scan around the known time with `source_time_status = unknown`.
3. Compare the blind candidate field to the externally sourced birth time without claiming the model proves the record.

Endpoint:

```text
POST /api/astro-clock/certification/rectify
```

Backend implementation:

```text
C:\Users\sabaa\Downloads\codexhorary\backend\birth_certification.py
```

Shared settings:

- House system: R
- Orb: 1 degree
- Level threshold: 67
- Search width: two hours around the known time
- Instruments: transits, direction reverse, profection reverse, primary progression, secondary progression local, secondary progression natal, tertiary progression, minor progression

## Muhammad Ali

Birth data used:

- 17 January 1942
- 18:35
- Louisville, Kentucky, United States
- Astro-Databank/Astro.com: Rodden AA / source-backed birth data

Event anchors used:

- Olympic light-heavyweight final, Rome, 5 September 1960, 21:00.
- First world heavyweight title, Miami Beach, 25 February 1964, day precision.
- Draft induction refusal, Houston, 28 April 1967, 08:30 report marker.
- Supreme Court conviction reversal, Washington DC, 28 June 1971, day precision.
- Rumble in the Jungle, Kinshasa, 30 October 1974, 04:00 local time.
- Death in Scottsdale, 3 June 2016, 21:10 local time.

### Source-Backed Certification

Input:

```text
source_time_status = aa
search = 18:35 to 18:35
```

Result:

```json
{
  "status": "certified_source",
  "confidence": "high",
  "reason": "Birth time is marked as externally sourced; rectification is not required to certify it."
}
```

### Blind Validation Scan

Input:

```text
source_time_status = unknown
search = 17:35 to 19:35
row_count = 121
```

Result:

```json
{
  "status": "unresolved_rectification",
  "confidence": "low",
  "candidate": {
    "timestamp": "1942-01-17T18:49:00-06:00",
    "strength": 100.0,
    "dominant_curve": "favorable",
    "favorable": 100.0,
    "tense": 45.45
  }
}
```

Top validation windows:

| Rank | Window | Peak | Dominant curve |
| ---: | --- | ---: | --- |
| 1 | 18:41-18:56 | 100.00 | favorable |
| 2 | 17:51-18:07 | 97.82 | favorable |
| 3 | 17:35-17:46 | 89.35 | favorable |
| 4 | 19:12-19:15 | 78.39 | favorable |
| 5 | 18:17-18:20 | 74.05 | favorable |
| 6 | 18:28-18:34 | 71.89 | favorable |

Known 18:35 row:

```json
{
  "timestamp": "1942-01-17T18:35:00-06:00",
  "rank": 67,
  "strength": 66.56,
  "favorable": 66.56,
  "tense": 39.36,
  "dominant_curve": "favorable",
  "hit_count": 1233
}
```

Interpretation:

Ali is a good second blog case. The blind scan did not cross the model's isolation threshold at the exact known minute, but it placed the top candidate at 18:49, only 14 minutes from the externally sourced 18:35 time. The thresholded field also included 18:28-18:34, stopping one minute before the known time. This is a strong "near corridor" result, while the certification itself still comes from the AA source.

## James Dean

Birth data used:

- 8 February 1931
- 09:00
- Marion, Indiana, United States
- Astro-Databank/Astro.com current listing: Rodden AA / BC-BR in hand

Important caveat:

James Dean is less clean as a source example than Queen Elizabeth II or Muhammad Ali. Astro-Databank currently lists 09:00 with an AA rating, but the same source notes also discuss older competing 2 AM material and a baby-card / certificate discrepancy. This makes Dean useful as a caveated stress test, not as the cleanest source-certification demonstration.

Event anchors used:

- Fairmount High School graduation, 16 May 1949, day precision.
- East of Eden world premiere, New York, 9 March 1955, day precision.
- Completed final Giant scene, Burbank, 27 September 1955, end-of-workday precision.
- Speeding ticket before crash, Bakersfield, 30 September 1955, 15:30.
- Fatal crash near Cholame, 30 September 1955, 17:45.

### Source-Backed Certification

Input:

```text
source_time_status = aa
search = 09:00 to 09:00
```

Result:

```json
{
  "status": "certified_source",
  "confidence": "high",
  "reason": "Birth time is marked as externally sourced; rectification is not required to certify it."
}
```

### Blind Validation Scan

Input:

```text
source_time_status = unknown
search = 08:00 to 10:00
row_count = 121
```

Result:

```json
{
  "status": "rectified_candidate",
  "confidence": "medium",
  "candidate": {
    "timestamp": "1931-02-08T08:50:00-06:00",
    "strength": 100.0,
    "dominant_curve": "favorable",
    "favorable": 100.0,
    "tense": 16.5
  },
  "reason": "A strong top minute exists across multiple relatively precise and independent events, but this is still rectification rather than external certification."
}
```

Top validation windows:

| Rank | Window | Peak | Dominant curve |
| ---: | --- | ---: | --- |
| 1 | 08:48-08:54 | 100.00 | favorable |
| 2 | 09:08-09:13 | 86.89 | favorable |
| 3 | 09:26-09:27 | 75.27 | favorable |
| 4 | 08:30-08:32 | 74.71 | favorable |
| 5 | 09:52-09:54 | 71.91 | favorable |
| 6 | 09:16-09:17 | 70.44 | favorable |

Known 09:00 row:

```json
{
  "timestamp": "1931-02-08T09:00:00-06:00",
  "rank": 79,
  "strength": 51.18,
  "favorable": 51.18,
  "tense": 7.47,
  "dominant_curve": "favorable",
  "hit_count": 913
}
```

Interpretation:

Dean is a compelling but caveated third example. The blind model produced a `rectified_candidate` at 08:50, only 10 minutes before the listed 09:00 time, but the exact 09:00 row was not strong. This should be framed as "the model lands in the same local corridor but prefers 08:50," not as validation of the exact listed minute. Because the source notes themselves are nuanced, Dean is better for explaining why the UI separates source status, scan score, and model candidate.

## Blog Use Ranking

1. Queen Elizabeth II: cleanest source-certification demonstration; near-hour but unresolved blind scan.
2. Muhammad Ali: best second example; clean AA chart and strong blind near-hit, 14 minutes from source time.
3. James Dean: interesting stress test; close blind candidate, but source notes and death-heavy event set require careful wording.

## Source Links

- Muhammad Ali Astro-Databank/Astro.com: https://www.astro.com/adbvip/adbvip_01_17.htm
- Olympic boxing schedule: https://en.wikipedia.org/wiki/Boxing_at_the_1960_Summer_Olympics_%E2%80%93_Light_heavyweight
- Muhammad Ali Center, Rumble in the Jungle: https://alicenter.org/roadwork-to-the-rumble/
- Cornell LII, Clay v. United States: https://www.law.cornell.edu/supremecourt/text/403/698
- Al Jazeera / news agencies on Ali death time: https://www.aljazeera.com/sports/2016/6/4/death-of-muhammad-ali-boxer-died-of-septic-shock
- James Dean Astro-Databank/Astro.com: https://www.astro.com/astro-databank/Dean%2C_James
- HISTORY on James Dean crash/death time: https://www.history.com/this-day-in-history/september-30/james-dean-dies-in-car-accident
- TCM on Giant final scene timing: https://www.tcm.com/articles/581457/behind-the-camera-giant
- East of Eden premiere reference: https://en.wikipedia.org/wiki/East_of_Eden_%28film%29
