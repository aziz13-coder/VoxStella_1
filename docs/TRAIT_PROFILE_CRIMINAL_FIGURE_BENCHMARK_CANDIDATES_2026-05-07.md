# Trait Profile Criminal-Figure Benchmark Candidates

Date: 2026-05-07

## Purpose

This batch benchmarks whether each person's top Trait Profile results are biographically correct for documented criminal-case figures. It is not a criminality detector and must not be used to infer guilt, risk, diagnosis, or future behavior.

Pass rule matches the public-figure biography benchmark: at least one expected biography trait must score `>= 30` and appear within summary rank `<= 12`.

## Inclusion Rules

- Birth time source must be Rodden `AA` or `A`.
- Birth source must be a timed Arcadia AstroDB page citing Astro-Databank.
- Biography source must be a stable public biography page.
- Expectations must describe documented biography themes, not medical diagnosis or criminal prediction.

## Implemented Batch

| Case | Group | Rodden | Source local time | Birth place | Birth source | Biography source |
| --- | --- | --- | --- | --- | --- | --- |
| Ted Bundy | violent_offender | AA | 24/11/1946 22:35, GMT -5 | Burlington, Vermont | [Arcadia](https://arcadia-astrology.com/en/astrodb/bundy-ted) | [Biography](https://en.wikipedia.org/wiki/Ted_Bundy) |
| Jeffrey Dahmer | violent_offender | AA | 21/05/1960 16:34, GMT -5 | Milwaukee, Wisconsin | [Arcadia](https://arcadia-astrology.com/en/astrodb/dahmer-jeffrey) | [Biography](https://en.wikipedia.org/wiki/Jeffrey_Dahmer) |
| John Wayne Gacy | violent_offender | AA | 17/03/1942 00:29, GMT -5 | Chicago, Illinois | [Arcadia](https://arcadia-astrology.com/en/astrodb/gacy-john-wayne) | [Biography](https://en.wikipedia.org/wiki/John_Wayne_Gacy) |
| Charles Manson | cult_crime | AA | 12/11/1934 16:40, GMT -5 | Cincinnati, Ohio | [Arcadia](https://arcadia-astrology.com/en/astrodb/manson-charles) | [Biography](https://en.wikipedia.org/wiki/Charles_Manson) |
| David Berkowitz | violent_offender | AA | 01/06/1953 16:52, GMT -4 | Brooklyn, New York | [Arcadia](https://arcadia-astrology.com/en/astrodb/berkowitz-david) | [Biography](https://en.wikipedia.org/wiki/David_Berkowitz) |
| Mark David Chapman | assassination | AA | 10/05/1955 19:30, GMT -6 | Fort Worth, Texas | [Arcadia](https://arcadia-astrology.com/en/astrodb/chapman-mark-david) | [Biography](https://en.wikipedia.org/wiki/Mark_David_Chapman) |
| Gary Gilmore | violent_offender | AA | 04/12/1940 06:30, GMT -6 | McCamey, USA | [Arcadia](https://arcadia-astrology.com/en/astrodb/gilmore-gary) | [Biography](https://en.wikipedia.org/wiki/Gary_Gilmore) |
| John Hinckley Jr. | assassination | AA | 29/05/1955 23:42, GMT -6 | Ardmore, Oklahoma | [Arcadia](https://arcadia-astrology.com/en/astrodb/hinckley-john-jr) | [Biography](https://en.wikipedia.org/wiki/John_Hinckley_Jr.) |
| Squeaky Fromme | cult_crime | AA | 22/10/1948 05:37, GMT -7 | Santa Monica, California | [Arcadia](https://arcadia-astrology.com/en/astrodb/fromme-squeaky) | [Biography](https://en.wikipedia.org/wiki/Squeaky_Fromme) |
| Robert Hansen | violent_offender | AA | 15/02/1939 05:56, GMT -6 | Estherville, Iowa | [Arcadia](https://arcadia-astrology.com/en/astrodb/hansen-robert) | [Biography](https://en.wikipedia.org/wiki/Robert_Hansen) |
| Clifford Olson | violent_offender | A | 01/01/1940 22:10, GMT -8 | Vancouver, British Columbia | [Arcadia](https://arcadia-astrology.com/en/astrodb/olson-clifford) | [Biography](https://en.wikipedia.org/wiki/Clifford_Olson) |
| Nathan Leopold | violent_offender | AA | 19/11/1904 15:55, GMT -6 | Chicago, Illinois | [Arcadia](https://arcadia-astrology.com/en/astrodb/leopold-nathan) | [Biography](https://en.wikipedia.org/wiki/Leopold_and_Loeb) |
| Reggie Kray | organized_crime | AA | 24/10/1933 20:00, GMT +0 | London, England | [Arcadia](https://arcadia-astrology.com/en/astrodb/kray-reggie) | [Biography](https://en.wikipedia.org/wiki/Kray_twins) |
| Ronnie Kray | organized_crime | AA | 24/10/1933 20:10, GMT +0 | London, England | [Arcadia](https://arcadia-astrology.com/en/astrodb/kray-ronnie) | [Biography](https://en.wikipedia.org/wiki/Kray_twins) |
| Lucky Luciano | organized_crime | AA | 24/11/1897 12:00, GMT +1 | Lercara Friddi, Italy | [Arcadia](https://arcadia-astrology.com/en/astrodb/luciano-lucky) | [Biography](https://en.wikipedia.org/wiki/Lucky_Luciano) |
| Frank Coppola | organized_crime | AA | 06/10/1899 06:00, GMT +1 | Partinico, Italy | [Arcadia](https://arcadia-astrology.com/en/astrodb/coppola-frank) | [Biography](https://en.wikipedia.org/wiki/Frank_Coppola_(mobster)) |
| David Carpenter | violent_offender | AA | 06/05/1930 21:16, GMT -8 | San Francisco, California | [Arcadia](https://arcadia-astrology.com/en/astrodb/carpenter-david) | [Biography](https://en.wikipedia.org/wiki/David_Carpenter) |
| Caryl Chessman | violent_offender | AA | 27/05/1921 12:10, GMT -5 | St. Joseph, USA | [Arcadia](https://arcadia-astrology.com/en/astrodb/chessman-caryl) | [Biography](https://en.wikipedia.org/wiki/Caryl_Chessman) |
| Kenneth Kimes Jr. | fraud_murder | AA | 24/03/1975 08:19, GMT -7 | Los Angeles, California | [Arcadia](https://arcadia-astrology.com/en/astrodb/kimes-kenneth-jr) | [Biography](https://en.wikipedia.org/wiki/Sante_Kimes) |
| Giovanni Brusca | organized_crime | AA | 20/02/1957 22:00, GMT +1 | San Giuseppe, Italy | [Arcadia](https://arcadia-astrology.com/en/astrodb/brusca-giovanni) | [Biography](https://en.wikipedia.org/wiki/Giovanni_Brusca) |
| Salvatore Riina | organized_crime | AA | 16/11/1930 16:00, GMT +1 | Palermo, Italy | [Arcadia](https://arcadia-astrology.com/en/astrodb/riina-salvatore) | [Biography](https://en.wikipedia.org/wiki/Salvatore_Riina) |

## Benchmark Outcome

Command:

```powershell
python backend\trait_logic_benchmark_runner.py --suite criminals-bio --output docs\TRAIT_PROFILE_CRIMINAL_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md
```

Result: `PASS`, 21/21 cases and 21/21 biography clusters.

Report: [TRAIT_PROFILE_CRIMINAL_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md](TRAIT_PROFILE_CRIMINAL_FIGURE_BIOGRAPHY_BENCHMARK_RUN_2026-05-07.md)

## Held Out Or Excluded

These candidates were checked but not included in the implemented suite:

| Candidate | Reason |
| --- | --- |
| Anders Breivik | Rodden `B`, below cutoff. |
| John Dillinger | Rodden `C`, below cutoff. |
| Billy the Kid | Rodden `DD`, below cutoff. |
| Clyde Barrow | Rodden `C`, below cutoff. |
| Richard Loeb | Rodden `C`, below cutoff. |
| Meyer Lansky | Rodden `X`, no timed birth. |
| Albert DeSalvo | Rodden `C`, below cutoff. |
| Frank Abagnale | Rodden `XX`, no timed birth. |
| Bonnie Parker | Arcadia slug found did not match the outlaw biography/date, so excluded. |
| Amanda Knox | Rodden `AA`, but excluded because the criminal-biography framing is inappropriate for an exonerated/acquitted case. |
| Tommaso Buscetta | Rodden `AA`, held for a possible Mafia-informant/control batch rather than this first criminal-focused batch. |
