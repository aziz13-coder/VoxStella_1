# Prohibition Detection Bug Analysis Session
**Date**: 2025-09-01  
**Issue**: Traditional horary engine fails to detect Mars-Jupiter prohibition in lottery question

## Problem Summary

**Chart Details:**
- **Question**: "Will I win in the lottery?"
- **Category**: GAMBLING 
- **Significators**: Sun (querent/1st house ruler) → Jupiter (quesited/5th house ruler)
- **Expected Perfection**: Sun sextile Jupiter in 11.4 days
- **Clear Prohibition**: Mars squares Jupiter in 4.08 days (should block Sun-Jupiter perfection)

**Current Bug:**
- Engine returns: "YES (Confidence: 99%)" with perfection_type: "direct_timed"
- Should return: "NO" due to Mars prohibition
- **Critical Point**: Engine DOES detect the Mars-Jupiter square aspect correctly - bug is in prohibition processing logic

## Root Cause Investigation

### Initial Hypothesis (INCORRECT)
**My First Theory**: Refranation filter was killing prohibitions
- **Analysis**: `_leg_valid()` function applies refranation checks to all aspects
- **Logic**: If Mars or Jupiter stations before Mars-Jupiter square completes, aspect gets filtered out
- **Problem**: Refranation should only apply to primary perfections, not prohibitions

### Code Modifications Attempted

#### Modification 1: Remove Refranation Check (REVERTED)
**File**: `backend/horary_engine/perfection.py`  
**Lines**: 97-115

**Original Code**:
```python
# Refranation: station before leg completes
jd0 = chart.julian_day
for p in (p_a, p_b):
    swe_id = SWE_ID.get(p.planet)
    if swe_id is None:
        continue
    try:
        st_jd = calculate_next_station_time(swe_id, jd0)
    except Exception:
        st_jd = None
    if st_jd is not None and (st_jd - jd0) < t_leg:
        return False
return True
```

**Modified Code**:
```python
# CRITICAL FIX: Only apply refranation to primary perfections, NOT prohibitions
# Prohibition is about one planet interfering with significator perfection
# If the prohibiting planet will station later, the damage is already done when aspect perfects
# Traditional refranation only applies when the promising planet itself stations

# Skip refranation check for prohibition aspects - they should trigger regardless
# The refranation check was incorrectly filtering out valid prohibitions

# Commenting out the refranation check that was causing prohibition failures:
# [refranation code commented out]
return True
```

**Result**: NO CHANGE - Engine still returned "YES (99%)" 
**Status**: REVERTED

#### Modification 2: Add Debug Logging (KEPT)
**File**: `backend/horary_engine/perfection.py`
**Purpose**: Add comprehensive debug output to trace prohibition detection

**Added**:
```python
print(f"\n=== PROHIBITION CHECK DEBUG ===")
print(f"Checking for prohibitions before {sig1.value}-{sig2.value} perfection in {days_ahead} days")
print(f"\n--- Checking {planet.value} for prohibition ---")
if planet.value == 'Mars' and aspect.value == 'Square':
    print(f"Mars Square: t1({sig1.value})={t1}, t2({sig2.value})={t2}")
    print(f"Mars Square validation: valid1={valid1}, valid2={valid2}")
```

**Status**: KEPT for debugging

#### Modification 3: Reorder Logic Priority (REVERTED)
**File**: `backend/horary_engine/perfection.py`
**Theory**: Simple prohibitions were being masked by translation/collection logic

**Original Logic Order**:
```python
if valid1 and valid2:
    # Translation/collection logic
elif valid1 and t1 > 0:
    # Simple prohibition of sig1
elif valid2 and t2 > 0:
    # Simple prohibition of sig2
```

**Modified Logic Order**:
```python
if valid1 and t1 > 0 and t1 < days_ahead:
    # Simple prohibition of sig1 (PRIORITIZED)
elif valid2 and t2 > 0 and t2 < days_ahead:
    # Simple prohibition of sig2 (PRIORITIZED)
elif valid1 and valid2:
    # Translation/collection logic (DEPRIORITIZED)
```

**Result**: NO CHANGE - Engine still returned "YES (99%)"
**Status**: REVERTED

## Key Findings

### What Works Correctly
1. **Aspect Detection**: Mars-Jupiter square (4.08 days, applying) is correctly calculated and included in chart aspects array
2. **Significator Assignment**: Sun (L1) and Jupiter (L5) correctly identified for GAMBLING category
3. **Perfection Detection**: Sun-Jupiter sextile (11.4 days) correctly found as "direct_timed" perfection
4. **Prohibition Function Call**: `_check_future_prohibitions()` is being called (line 4751 in engine.py)

### What's Still Broken
1. **Prohibition Recognition**: Despite Mars-Jupiter square being calculated, it's not recognized as blocking the Sun-Jupiter perfection
2. **Validation Logic**: Something in `_leg_valid()` or the prohibition logic flow is filtering out or ignoring the valid Mars-Jupiter prohibition

### Remaining Questions
1. **Single vs. Both Significators**: Does Mars need to aspect BOTH Sun AND Jupiter, or is aspecting just Jupiter sufficient for prohibition?
2. **Validation Failure**: What specific validation step is causing `valid2` to be False for Mars-Jupiter?
3. **Timing Windows**: Are there boundary checks beyond refranation that might exclude the Mars-Jupiter aspect?
4. **Category-Specific Logic**: Is there any GAMBLING-specific behavior affecting prohibition detection?

## Current Status
- **Refranation theory**: DISPROVEN (removing it had no effect)
- **Logic priority theory**: DISPROVEN (reordering had no effect)  
- **Code state**: Reverted to original with debug logging added
- **Bug**: Still present - engine still returns "YES (99%)" instead of detecting prohibition

## Next Steps
External AI agent consultation requested to review prohibition detection logic with comprehensive context including:
- Traditional prohibition definition
- Confirmation that aspect calculation works
- Complete chart data and question context
- Specific focus on why calculated aspects aren't processed as prohibitions