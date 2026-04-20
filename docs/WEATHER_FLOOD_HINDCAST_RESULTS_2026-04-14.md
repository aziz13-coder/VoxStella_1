# Weather Flood Hindcast Results

Run date: 2026-04-14

## Benchmark Scope

This run isolates the existing `flood_risk` predictive hindcast cases from the weather benchmark suite.

The cases are:

- `weather_predictive_flood_heppner_1903`
- `weather_predictive_flood_dyersburg_2011`

Each case includes:

- one real flood target window
- two matched nearby no-flood control windows

## Result

- cases: `2`
- alignment passes: `2`
- alignment pass rate: `100%`
- target-window passes: `2`
- target-window pass rate: `100%`
- near passes: `0`
- median target percentile: `1.0`
- median peak distance: `0.0` hours
- target beats controls: `2/2`

## Case Detail

### Heppner flood hindcast window

- location: `Heppner, Oregon, USA`
- target window: `1903-06-13 00:00` to `1903-06-14 18:00`
- peak score: `86`
- peak datetime: `1903-06-13 06:00`
- control peak max: `77`
- control margin: `+9`
- target beats controls: `yes`

### Dyersburg flood hindcast window

- location: `Dyersburg, Tennessee, USA`
- target window: `2011-05-01 00:00` to `2011-05-03 18:00`
- peak score: `72`
- peak datetime: `2011-05-03 06:00`
- control peak max: `64`
- control margin: `+8`
- target beats controls: `yes`

## Critical Reading

This is a good flood-family result, but it is still a narrow hindcast:

- only `2` flood cases are in scope
- both passed against the matched no-flood controls
- this supports the claim that the current `flood_risk` model is the strongest weather family in the runtime
- it does **not** yet justify saying the model is broadly validated for prospective flood prediction

## Practical Conclusion

The present evidence supports this narrower claim:

- when tested on the current source-backed flood cases, the `flood_risk` model successfully elevated the real flood windows above the matched nearby no-flood windows

The evidence does **not** yet support this broader claim:

- that the model is generally proven to predict floods across a large or diverse out-of-sample set
