# Queen Elizabeth II Birth Certification Run

Date: 2026-05-22

## Purpose

Use Vox Stella's Birth Certification tool on a known-time public natal chart, so the result can anchor a blog walkthrough of the feature.

This run uses Queen Elizabeth II because her birth time is externally source-backed and public: 21 April 1926, 02:40, Mayfair, London. The key blog point is that Vox Stella separates source certification from model rectification:

- A source-backed time can be certified as externally sourced.
- A blind rectification scan can be reviewed as supporting evidence, but it does not become proof unless the model isolates a candidate under its own rules.

## Source Notes

- Birth data: Royal Collection Trust gives 02:40 on 21 April 1926 at 17 Bruton Street, Mayfair, London. Astro-Databank/Astro.com lists the chart as Rodden AA / quoted birth certificate or birth record.
- Event anchors:
  - Marriage: Westminster Abbey, 20 November 1947.
  - Birth of Prince Charles: Buckingham Palace, 14 November 1948 at 21:14.
  - Accession: 6 February 1952, tied to George VI's death. The exact death moment is not known, so this was treated as hours-level precision around the reported morning discovery/accession marker.
  - Coronation: Westminster Abbey, 2 June 1953. Westminster Abbey records the Queen entering the nave at 11:20 and being crowned at 12:34; this run used 11:15 as the service-opening marker.
  - Death: Balmoral, 8 September 2022 at 15:10, from the death certificate reporting.

Source links:

- Royal Collection Trust, Queen Elizabeth II life focus: https://www.rct.uk/schools/school-and-family-resources/a-focus-on-the-life-of-queen-elizabeth-ii-school-resources
- Astro-Databank/Astro.com entry: https://www.astro.com/adbvip/adbvip_04_21.htm
- Royal Family, Prince Charles birth fact sheet: https://www.royal.uk/clarencehouse/70-facts-about-hrh-prince-wales
- Westminster Abbey, Elizabeth II page: https://www.westminster-abbey.org/abbey-commemorations/royals/elizabeth-ii
- ITV News on death certificate / National Records of Scotland extract: https://www.itv.com/news/2022-09-29/the-queen-died-from-old-age-death-certificate-reveals
- TIME on accession timing caveat: https://time.com/4019998/queen-elizabeth-ii-reign-began/

## Tool Invocation

Endpoint used:

```text
POST /api/astro-clock/certification/rectify
```

Implementation path:

```text
C:\Users\sabaa\Downloads\codexhorary\backend\birth_certification.py
```

The run used the same Flask route consumed by the frontend helper `AstroClockAPI.rectifyBirthTime(...)`.

Settings:

- Birth date: 1926-04-21
- Birth location: Mayfair, London, England
- Coordinates used: 51.5074, -0.1278
- Timezone: Europe/London
- House system: R
- Orb: 1 degree
- Level threshold: 67
- Instruments: transits, direction reverse, profection reverse, primary progression, secondary progression local, secondary progression natal, tertiary progression, minor progression

## Pass 1: Source-Backed Certification

Input status:

```text
source_time_status = aa
search = 02:40 to 02:40
```

Vox Stella result:

```json
{
  "status": "certified_source",
  "confidence": "high",
  "reason": "Birth time is marked as externally sourced; rectification is not required to certify it."
}
```

Interpretation:

This is the actual certification outcome for the chart. The feature certifies the time because the user supplied an external reliable source status. The single-minute score normalizes to 100 by design, so it should not be presented as independent rectification evidence.

## Pass 2: Blind Validation Scan Around Known Hour

Input status:

```text
source_time_status = unknown
search = 01:40 to 03:40
row_count = 121
```

Vox Stella result:

```json
{
  "status": "unresolved_rectification",
  "confidence": "low",
  "candidate": {
    "timestamp": "1926-04-21T02:14:00+01:00",
    "strength": 100.0,
    "dominant_curve": "favorable",
    "favorable": 100.0,
    "tense": 22.1
  },
  "data_quality": {
    "event_count": 5,
    "near_exact_event_count": 5,
    "independent_theme_count": 5,
    "month_or_weaker_event_count": 0
  },
  "reason": "The scan does not produce a sufficiently isolated, independently supported candidate."
}
```

Top validation windows:

| Rank | Window | Peak | Dominant curve |
| ---: | --- | ---: | --- |
| 1 | 02:11-02:28 | 100.00 | favorable |
| 2 | 02:43-02:50 | 94.32 | favorable |
| 3 | 02:32-02:39 | 92.55 | favorable |

Known 02:40 row inside this blind scan:

```json
{
  "timestamp": "1926-04-21T02:40:00+01:00",
  "rank": 59,
  "strength": 66.39,
  "favorable": 66.39,
  "tense": 34.5,
  "dominant_curve": "favorable",
  "hit_count": 1174
}
```

Interpretation:

The blind scan does not validate 02:40 as an isolated rectified candidate. It finds high activity near the known hour, especially 02:32-02:50, but the exact sourced time is just below the 67 threshold and ranks 59 within the two-hour validation window. This is useful for the blog because it demonstrates responsible behavior: the app certifies source-backed time, while refusing to overstate an unresolved model scan.

## Blog Angle

Recommended framing:

1. Start with the known public source: Queen Elizabeth II, 02:40, Mayfair, London.
2. Run Vox Stella with the source marked AA/certificate and show `certified_source`.
3. Then hide the source status and run a blind scan around the same hour.
4. Explain that the model produced activity near the known hour but did not isolate 02:40, so the correct conclusion is not "the model proved it"; the correct conclusion is "the source certifies it, and the model review remains secondary evidence."

Suggested headline:

```text
Certification Is Not Guesswork: Testing a Known Birth Time in Vox Stella
```

Suggested thesis:

```text
Vox Stella's Birth Certification workflow is deliberately conservative. It can certify a birth time when the source is reliable, and it can review life-event timing for rectification, but it keeps those two evidentiary lanes separate.
```
