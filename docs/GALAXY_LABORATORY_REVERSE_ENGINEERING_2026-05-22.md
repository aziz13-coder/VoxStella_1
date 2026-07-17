# Galaxy Laboratory Reverse Engineering

Date: 2026-05-22

Scope: static reverse engineering of Galaxy's `Laboratory` feature from the installed Galaxy binaries and decompiled `xrays.dll` sources. This document focuses on workflow, condition encoding, calculation pipeline, and whether Laboratory conditions can use Galaxy-calculated points.

Primary sources:

- `C:\Program Files (x86)\Galaxy\GalaxyLaboratory.exe`
- `C:\Program Files (x86)\Galaxy\temp\ilspy_xrays\xrays\Obj4Laboratory.cs`
- `C:\Program Files (x86)\Galaxy\temp\ilspy_xrays\xrays\AstroCalc.cs`
- `C:\Program Files (x86)\Galaxy\temp\ilspy_xrays\xrays\AI.cs`
- `C:\Program Files (x86)\Galaxy\temp\ilspy_xrays\xrays\dbwork.cs`
- `C:\Program Files (x86)\Galaxy\DataProg\GalaxyPreView1.xml`

## Executive Summary

Galaxy Laboratory is a statistical astrology research tool. It is not the same as Galaxy certification or rectification. It consumes saved record sets from DataFinder, computes chart data using the normal Galaxy chart engine, applies selected astrological conditions, then visualizes frequency distributions or value-series correlations.

The important architectural point is that Laboratory does not have its own ephemeris engine. It builds `AstroCalc.Chart` objects, calls `AI.GetObjData()`, and then evaluates conditions against the already-computed `AstroCalc.achart[].askyobj` objects.

For points: Laboratory can use some Galaxy-calculated chart points, but only the ones exposed through `askyobj` and the Laboratory operand picker. It can use:

- Main chart objects in indices `0..23`.
- The two built-in calculated parts at indices `22` and `23`, because `AI.GetObjData()` calls `AstroCalc.CalcParts(..., 22, ...)` and `AstroCalc.CalcParts(..., 23, ...)`.
- House cusps `1..12`, implemented as `askyobj[24..35]`.
- A midpoint calculated on the fly between two selectable objects from `0..23`.

It does not appear to expose the separate special-point catalogs (`SpecChart.points_pars` and `SpecChart.points_mid`) as Laboratory condition operands. Those special points are computed into `chart.aspecobj`, while Laboratory's condition evaluator reads `chart.askyobj` only.

## User-Facing Workflow

The docs in `GalaxyPreView1.xml` describe Laboratory as an "Astrologer's tool for research" over sequences of same-type events. The feature searches for statistical dependencies between event sets and astrological conditions.

The workflow is:

1. Load a dataset saved by Galaxy DataFinder.
2. Select checked records.
3. Select an analysis mode.
4. Optionally select a chart instrument.
5. Build or load a set of conditions.
6. Run calculation.
7. Inspect graphs or save filter/result blocks.

The docs describe four modes, which match the `FindRegime` enum in `Obj4Laboratory.cs`:

| Mode | Internal enum | Meaning |
| --- | --- | --- |
| Single chart set | `chart_one` | One chart per record. Used for distribution research over a group. |
| Natal + event | `chart_event` | One subject chart plus a linked event chart. |
| Natal + natal | `chart_chart` | Linked chart-to-chart research, including cross direction. |
| Event + value | `chart_value` | Event chart plus numeric value/time series. |

## Calculation Pipeline

The calculation flow is:

```text
DataFinder saved set
  -> Obj4Laboratory.LoadDataSet()
  -> infer FindRegime from available fields
  -> user selects records and conditions
  -> per checked row, build one or two AstroCalc.Chart objects
  -> AI.GetObjData()
  -> CalcCondition(encoded_condition)
  -> AddVal(...) into AstroCalc.DataLine
  -> paint frequency/value graphs
```

Important code locations:

- `Obj4Laboratory.cs:25`: `FindRegime`.
- `Obj4Laboratory.cs:4118`, `4146`, `4174`, `4195`: per-mode chart construction and condition iteration entry points.
- `Obj4Laboratory.cs:4224`: chart object creation helper.
- `Obj4Laboratory.cs:4244`: calls `AI.GetObjData()`.
- `AstroCalc.cs:1666`: `datapoint`.
- `AstroCalc.cs:1721`: `DataLine.AddVal`.
- `AstroCalc.cs:1752`: `DataLine.SetMinMax`.

In histogram modes, each condition returns bin IDs, and Galaxy increments those histogram bins. In `chart_value`, `GetScale()` returns `null`; conditions are treated as boolean operations aligned against the value time series rather than categorical histogram scales.

## Data And Storage

Laboratory reads DataFinder record sets through `dbwork.GetRecordSetsList` and `dbwork.GetRecordSetsData`.

Relevant block types from `flwork.RecBlockType`:

| Block | ID | Purpose |
| --- | ---: | --- |
| `laboratory` | 37 | Main Laboratory saved block. |
| `laboratory_filter` | 38 | Saved condition/filter block. |
| `laboratory_DC` | 44 | Double-chart Laboratory block alias. |
| `laboratory_DW` | 47 | DataWorker/value Laboratory block alias. |

Condition filters are saved as plain line-oriented text through `dbwork.SaveLoadOneVal(...)`.

Filter save shape:

```text
<find_regime_int>
<condition_1_encoded>
<condition_2_encoded>
...
```

The condition rows are reconstructed for display by `Obj4Laboratory.ReconstructCondition(...)`, but the encoded row is what the calculator uses.

## Condition Encoding

Condition rows are tab-separated. The first field is the condition ID. Remaining fields depend on the condition ID.

```text
<condition_id>\t<operand_1>\t<parameter_or_operand_2>\t<optional_filter_value>
```

The condition builder assembles rows in `Obj4Laboratory.cs:1402`; the evaluator consumes them in `Obj4Laboratory.cs:1457`.

The operand token has this logical shape:

```text
<operand_kind><two_digit_id>[<two_digit_second_id>]
```

Observed operand kinds:

| Operand kind | Meaning | Resolver behavior |
| --- | --- | --- |
| `0` | Direct object | Reads `achart[chart_index].askyobj[id].objpos.longitude`. |
| `1` | Almuten of cusp | Reads cusp `id`, finds `AstroCalc.GetAlmutenFromCuspLon(...)`, then returns that ruler's longitude. |
| `2` | Dispositor of object | Reads object `id`, finds `AstroCalc.GetAlmutenFromCuspLon(object_longitude)`, then returns that ruler's longitude. |
| `3` | Gradarh ruler of object | Reads object `id`, finds `AstroCalc.GetGradarh(object_longitude)`, then returns that ruler's longitude. |
| `4` | House cusp | Reads `askyobj[id + 23]`, so input `1` means cusp 1 at `askyobj[24]`. |
| `5` | Midpoint | Reads two objects from `0..23` and returns `AstroCalc.GetMidPoint(...)`. |

The main resolver is at `Obj4Laboratory.cs:2654` and delegates to `Obj4Laboratory.cs:2690`.

## Chart Direction Rules

The same operand token can resolve against different charts depending on mode.

| Mode | Default operand chart | Secondary/cross behavior |
| --- | --- | --- |
| `chart_one` | Single chart at `achart[0]`. | None. |
| `chart_value` | Single event/value chart at `achart[0]`. | None. |
| `chart_event` | Default condition operand resolves against event chart `achart[1]`. | Secondary operand with `P_1=false` resolves against the selected instrument chart index. |
| `chart_chart` | Default condition operand resolves cross-direction: chart 2 then chart 1. | Secondary operand reverses direction. |

This is why `chart_chart` can count both external-on-internal and internal-on-external relationships without storing two separate records.

## Condition ID Semantics

The condition list names come from the database handbook `dbwork.SHB.s_cnd`, but the actual behavior is hardcoded in `CalcCondition`.

| ID | Meaning inferred from code | Output scale |
| ---: | --- | --- |
| 1 | Object zodiac sign | 12 signs |
| 2 | Object house | 12 houses |
| 3 | Object zodiac sign only if object is inside selected degree sector within sign | 12 signs |
| 4 | Object house only if object is inside selected house sector | 12 houses |
| 5 | Object sign element | 4 elements |
| 6 | Object house element/triplicity by house number grouping | 4 groups |
| 7 | Object sign quadrant | 4 quadrants |
| 8 | Object house quadrant | 4 quadrants |
| 9 | Object sign zone/triplicity group | 3 groups |
| 10 | Object house zone/triplicity group | 3 groups |
| 11 | Object sign semisphere | 4 semisphere bins, two bins may be emitted per object |
| 12 | Object house semisphere | 4 semisphere bins, two bins may be emitted per object |
| 13 | Gradarh of object longitude | Gradarh ruler scale |
| 14 | Absolute zodiac degree or absolute degree sector test | 360 degree bins |
| 15 | Object longitude speed range | -100..130 normalized speed bins |
| 16 | Relation to Sun within same sign/aspect boundary classes | 4 classes |
| 17 | Object proximity to angular cusps | 4 angles plus none |
| 18 | Whether selected object is before/after nearest object of selected type around the Sun/object reference | 2 directions plus none |
| 19 | Aspect between two operands | 19 aspect bins plus none |
| 20 | Aspect between operand and any object from selected object group | 19 aspect bins plus none |
| 21 | Angular distance between two operands | 0..180 degree bins or range test |
| 22 | Zodiac signs occupied by clusters/runs of selected object group | 12 signs plus none |
| 23 | Houses occupied by clusters/runs of selected object group | 12 houses plus none |
| 24 | Self-gradarh condition over objects | Gradarh ruler scale |
| 25 | Day/degree-in-sign bucket for object or group | 1..30 bins |

The scale builder is `Obj4Laboratory.cs:1226`. It returns `null` for `chart_value`, because value mode is not displayed as a category histogram.

## Points Support

Short answer: partly yes, but only for points that live in `askyobj` and are exposed by the Laboratory operand UI.

Galaxy has several categories that can be called "points":

### 1. Built-in chart parts at object indices 22 and 23

`AI.GetObjData()` calculates two parts:

```text
AstroCalc.CalcParts(ref chart, 22, instrumentGroup)
AstroCalc.CalcParts(ref chart, 23, instrumentGroup)
```

These objects are in the `0..23` range used by Laboratory's object picker, so they can be used as condition operands if visible for the selected instrument.

Conclusion: yes, these Galaxy-calculated parts can be conditions.

### 2. House cusps

Cusps are calculated into `askyobj[24..35]`. The condition operand kind `4` exposes them as cusp `1..12`.

Conclusion: yes, cusps can be condition operands.

### 3. On-the-fly midpoints

Operand kind `5` computes a midpoint between two selectable objects from `0..23` by calling `AstroCalc.GetMidPoint(...)`.

Conclusion: yes, a condition can be a computed midpoint, but only a midpoint chosen directly in the condition builder.

### 4. Special "Pars" and "Midpoint" catalogs

Galaxy also has special chart modes:

- `AstroCalc.SpecChart.points_pars`
- `AstroCalc.SpecChart.points_mid`

These are calculated in `AI.cs` into `chart.aspecobj`, not `chart.askyobj`.

Laboratory's condition evaluator does not read `aspecobj`. Its resolvers all read `AstroCalc.achart[...].askyobj[...]`, and its object ranges are fixed:

- planets/main objects: `0..9`
- all normal objects: `0..23`
- cusps: `24..35`

Conclusion: no, arbitrary special-point catalog entries do not appear to be valid Laboratory condition operands without modifying the engine.

### 5. Cusp-derived points such as Vertex/ARMC/Equatorial Ascendant

`AI.GetObjData()` calculates cusp points in the `36..47` range when `ObjView.IsCuspPoint()` is true. However, Laboratory's selectable object/group ranges stop before this range.

Conclusion: these points are calculated by Galaxy, but Laboratory conditions do not appear to expose them.

## Reproduction Notes For VoxStella

To reproduce Galaxy Laboratory behavior, implement this in layers:

1. Dataset model
   - Preserve the four modes: `chart_one`, `chart_event`, `chart_chart`, `chart_value`.
   - Preserve per-row checked/unchecked participation.

2. Chart generation
   - Use the same house system, zodiac/plain setting, instrument visibility flags, and object visibility.
   - Build one or two charts per row according to mode.

3. Operand resolver
   - Implement direct object, cusp almuten, object dispositor, gradarh ruler, cusp, and midpoint operands.
   - Use Galaxy-compatible object index ranges first: `0..23` and cusps `24..35`.

4. Condition evaluator
   - Implement IDs `1..25` as separate named functions.
   - Return arrays of bin IDs, not single booleans, because several conditions can emit multiple bins.
   - Return `-1` for no hit/unusable object.

5. Accumulator
   - Histogram modes increment the returned bins.
   - Value mode treats condition matches as operations aligned to the value series.

6. Point parity decision
   - For strict Galaxy parity, include only the points Laboratory exposes: object indices `22..23`, cusps, and explicit midpoint operands.
   - For an enhanced VoxStella research lab, add a separate operand type for point catalogs, but mark it as beyond Galaxy parity.

## Open Questions

The decompiled code confirms behavior, but exact display names for condition IDs come from Galaxy's database handbook table `s_cnd`. If exact UI labels are required, the next reverse-engineering step is to query `DataProg\datacenter.gdb` or instrument the running UI to dump `dbwork.GetHB(dbwork.SHB.s_cnd)`.

The current scan did not execute Galaxy Laboratory against a sample dataset. It documents static behavior from the decompiled implementation.
