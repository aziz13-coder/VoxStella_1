# Shadow Mode Testing Guide

## Overview

The Shadow Mode system runs both the old and new perfection detection systems in parallel for safe testing of the unified `perfection_core.py` module. This ensures zero risk to production functionality while validating the new system.

## How Shadow Mode Works

1. **Parallel Execution**: Both old (`_check_enhanced_perfection`) and new (`PerfectionCoreAPI`) systems run on the same chart
2. **Result Comparison**: Detailed comparison identifies any differences in:
   - Perfection found/not found
   - Perfection type (direct, translation, collection, etc.)
   - Confidence levels 
   - Reasoning text
3. **Safe Fallback**: Always uses the old system result for the actual judgment
4. **Logging**: Comprehensive logs show exactly where systems agree or differ

## Enabling Shadow Mode

Set the environment variable before running the application:

```bash
export HORARY_SHADOW_MODE=true
```

Or on Windows:
```cmd
set HORARY_SHADOW_MODE=true
```

## Reading Shadow Mode Output

### When Systems Agree:
```
=== SHADOW MODE: Running OLD perfection detection ===
OLD RESULT: direct - Square between significators
=== SHADOW MODE: Running NEW perfection detection ===  
NEW RESULT: direct_penalized - Square between significators with difficulty
=== SHADOW MODE COMPARISON SUMMARY ===
✅ SYSTEMS AGREE: Both systems produced equivalent results
PERFECTION SELECTION: Using OLD system result (shadow mode active)
```

### When Systems Differ:
```
=== SHADOW MODE COMPARISON SUMMARY ===
⚠️  SYSTEMS DIFFER: 2 differences found
   - perfection_type_mismatch: medium severity
     OLD: direct
     NEW: direct_penalized
   - confidence_mismatch: low severity  
     OLD: 80
     NEW: 55
```

## Interpreting Differences

### Severity Levels:

- **HIGH**: One system found perfection, other didn't
- **MEDIUM**: Different perfection types or major confidence differences (>20%)
- **LOW**: Minor differences in confidence (<20%) or reasoning text

### Expected Differences (OK):

- **Type refinement**: `direct` → `direct_penalized` (new system is more specific)
- **Confidence calibration**: Small differences due to improved calculations
- **Reasoning clarity**: More detailed explanations in new system

### Concerning Differences (Review Required):

- **Perfection found mismatch**: One system finds perfection, other doesn't
- **Major type differences**: Completely different perfection types
- **Large confidence swings**: >30% differences suggest calculation errors

## Testing Workflow

1. **Enable Shadow Mode**: Set `HORARY_SHADOW_MODE=true`
2. **Run Test Questions**: Process various question types
3. **Review Logs**: Check for differences and their severity
4. **Fix Issues**: Address any concerning differences in `perfection_core.py`
5. **Validate**: Ensure systems converge to equivalent results
6. **Switch Over**: When confident, modify `_use_perfection_result` to use new system

## Safety Guarantees

- **Zero Risk**: Old system always used for actual judgments
- **No Breaking Changes**: All existing functionality preserved
- **Reversible**: Simply unset `HORARY_SHADOW_MODE` to disable
- **Isolated**: New system errors don't affect application functionality

## Migration Path

Phase 1: **Shadow Mode Testing** (Current)
- Run both systems, use old results
- Identify and fix differences
- Build confidence in new system

Phase 2: **Gradual Switchover** (After testing)
- Modify `_use_perfection_result` to prefer new system when systems agree
- Keep old system as fallback for disagreements
- Monitor for issues

Phase 3: **Full Migration** (After validation) 
- Use new system exclusively
- Remove old perfection detection code
- Clean up shadow mode infrastructure

## Troubleshooting

### New System Errors:
- Check `perfection_core.py` imports and dependencies
- Verify chart data format compatibility
- Review timing calculation logic

### Comparison Failures:
- Ensure both systems handle edge cases
- Check for floating point precision differences
- Validate data structure formats

### Performance Issues:
- Shadow mode doubles perfection calculation time
- Disable for production if needed
- Optimize new system based on profiling

## Key Files

- `perfection_core.py`: New unified perfection detection system
- `engine.py`: Shadow mode integration and comparison logic  
- `horary_constants.yaml`: Configuration for both systems
- This file: Documentation and testing guide

Remember: **Safety first, migration second**. The shadow mode ensures the new system is battle-tested before any production changes.