# Memo Score Normalization

## Problem

The memo headline was still computed as a linear weighted sum and then hard-clamped into the `0..100` display range.

That created two visible problems:

- intense long-form pairs could reach `100` too easily even when `friction` and `burden` were materially present
- the headline could look "perfect" while the underlying category breakdown clearly was not

## Resolution

The live memo headline now has three guards:

1. lighter communication dominance
2. a direct `friction` penalty alongside `burden`
3. sigmoid normalization instead of `sum then clip`

Current live headline config in [synastry_rule_catalog.json](C:/Users/sabaa/Downloads/codexhorary/backend/synastry_rule_catalog.json):

- `0.26 * compatibility`
- `1.2 * communication`
- `0.12 * attachment`
- `0.18 * attraction`
- `-0.06 * friction`
- `-0.4 * burden`
- normalization: `sigmoid(center=40, scale=18)`

## Why This Is General

- `compatibility` and `communication` still anchor lived fit
- `attachment` and `attraction` still preserve bond and chemistry
- `friction` now affects the headline directly instead of living only in the descriptive layers
- `burden` still represents chronic pressure, obligation, and heaviness
- sigmoid normalization keeps the ordering signal but stops artificial ceiling saturation

## Expected Effect

- `100` becomes rare
- strong but flawed couples can land in the high `80s` or `90s`
- the category stack and the headline read more coherently together
- benchmark ordering stays materially intact because the normalization step is monotonic
