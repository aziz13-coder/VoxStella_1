# Horary External Source-Pass Slice 22

Date:
2026-03-25

Repository:
`C:\Users\sabaa\Downloads\codexhorary`

Primary fixture:
`C:\Users\sabaa\Downloads\codexhorary\tests\fixtures\horary_external_source_pass_slice22.json`

Primary test:
`C:\Users\sabaa\Downloads\codexhorary\tests\test_horary_external_source_pass_slice22.py`

## Purpose

This slice probes landlord, tenant, occupancy-change, and eviction questions.

The goal is to test whether the router can distinguish:

- a landlord asking when a tenant will move out
- an unwanted occupant or tenant leaving a property
- an explicit eviction question from the occupier's side

This remains a source-pass slice, not a replay slice.

## Cases Added

1. `When will my tenant move out?`
2. `Will he leave the property?`
3. `Will I get evicted/loose my Home?`

## Results

Summary:

- fetched source-pass cases: `3`
- source-aligned router observations: `3`
- source-misaligned router observations: `0`

Aligned:

- `tenant_move_out_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 7]`
  - note: tenant move-out questions now keep the property and the tenant together instead of flattening into generic `1/7`

- `illegal_tenant_leave_property_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 7]`
  - note: occupant-leaving questions now keep the property on the `4th` and the unwanted occupant on the `7th`

- `evicted_lose_home_astrologyweekly_source_pass`
  - current router: `property`
  - houses: `[1, 4, 7]`
  - note: explicit eviction wording continues to keep the home and landlord together

## Interpretation

This slice confirms a real family-level fix rather than a title patch.

The shared tenancy doctrine now covers:

1. a tenant moving out
2. an occupant leaving a property
3. explicit eviction or loss-of-home questions

The operative logic is now stable:

- querent or operative holder remains visible
- property stays on the `4th`
- tenant, landlord, or unwanted occupant stays on the `7th`

So slice 22 is now closed as a routing gap.

## Sources

- [Astrology Weekly: When will my tenant move out?](https://astrologyweekly.com/threads/when-will-my-tenant-move-out.133408/post-1041727)
- [Astrology Weekly: Will he leave the property?](https://astrologyweekly.com/threads/will-he-leave-the-property-please-help-read.154775/post-1365899)
- [Astrology Weekly: Will I get evicted/loose my Home?](https://astrologyweekly.com/threads/will-i-get-evicted-loose-my-home.21088/)

## Verification

- `python -m pytest tests\\test_horary_external_source_pass_slice22.py -q`
  - result: `3 passed`
- `python -m pytest tests\\test_horary_external_slice22_rules.py tests\\test_horary_external_source_pass_slice22.py tests\\test_property_doctrine_pass.py -q`
  - result: `10 passed`

Runtime horary logic changed in this step through the shared tenancy / landlord-tenant occupancy doctrine pass.
