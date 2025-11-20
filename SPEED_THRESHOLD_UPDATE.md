# Speed Threshold Feature Update

## Summary of Changes

Changed the "Speed at Edge (Hz)" setting to "Speed Threshold (%)" with improved speed-based radius scaling using the generated speed.funscript.

## What Changed

### 1. Configuration (`config.py`)
- **Old:** `speed_at_edge_hz: 2.0` (range: 1.0-5.0 Hz)
- **New:** `speed_threshold_percent: 50` (range: 0-100%)

### 2. UI (`ui/conversion_tabs.py`)
- **Old:** "Speed at Edge (Hz)" slider (1-5 Hz)
- **New:** "Speed Threshold (%)" slider (0-100%)
- Updated label: "(0-100%) Speed percentile for maximum radius"

### 3. Processing Flow
- **Old Flow:** main → alpha/beta → speed
- **New Flow:** main → **speed** → alpha/beta (using speed data)

The speed.funscript is now generated (or loaded if exists) BEFORE alpha/beta generation, so it can be used for radius scaling.

### 4. Core Algorithm Changes

#### Old Behavior (`processing/funscript_1d_to_2d.py`)
```python
# Calculated speed from position changes
current_speed = position_change / segment_duration
speed_ratio = min(current_speed / max_speed_threshold, 1.0)
radius_scale = min_distance + (1.0 - min_distance) * speed_ratio
```

#### New Behavior
```python
# Get speed from speed.funscript at current timestamp
time_diffs = np.abs(speed_funscript.x - start_t)
closest_idx = np.argmin(time_diffs)
speed_value = speed_funscript.y[closest_idx] * 100  # 0-100 range

# Apply threshold-based scaling
if speed_value >= speed_threshold_percent:
    radius_scale = 1.0  # Maximum radius
else:
    ratio = speed_value / speed_threshold_percent
    radius_scale = min_distance + (1.0 - min_distance) * ratio
```

## How It Works Now

### Speed Value Lookup
1. For each segment in the main funscript (between two consecutive actions)
2. Find the closest timestamp in speed.funscript
3. Get the speed value at that timestamp (0-100 range)

### Radius Calculation
- **If `speed_value >= threshold`**: Use maximum radius (1.0)
- **If `speed_value < threshold`**: Interpolate between min_distance and 1.0

### Example with 50% Threshold

| Speed Value | Threshold | Ratio | Min Dist | Radius Scale | Result |
|-------------|-----------|-------|----------|--------------|--------|
| 0 | 50 | 0/50 = 0.0 | 0.1 | 0.1 + 0.9×0.0 = **0.1** | Minimum |
| 25 | 50 | 25/50 = 0.5 | 0.1 | 0.1 + 0.9×0.5 = **0.55** | Halfway |
| 50 | 50 | 50/50 = 1.0 | 0.1 | **1.0** | Maximum |
| 75 | 50 | ≥ threshold | - | **1.0** | Maximum |
| 100 | 50 | ≥ threshold | - | **1.0** | Maximum |

## Benefits

1. **More Intuitive:** Percentage threshold instead of Hz value
2. **Better Control:** Direct mapping from normalized speed values (0-100)
3. **Consistent Speed:** Uses the same speed.funscript that's used elsewhere in processing
4. **Predictable Results:** 50% threshold means top half of speeds reach maximum radius

## Migration Notes

### For Existing Configurations
Old `speed_at_edge_hz` values will be ignored. The new default of 50% should work well for most content.

### Recommended Settings
- **Default (50%):** Top half of speeds reach maximum radius
- **Compact motion (70%):** Only fastest 30% reach maximum
- **Expanded motion (30%):** Top 70% reach maximum
- **Aggressive (90%):** Only extreme speeds stay at minimum
- **Conservative (10%):** Almost everything reaches maximum

## Files Modified

1. `config.py` - Parameter definition and validation ranges
2. `ui/conversion_tabs.py` - UI controls and variable management
3. `processing/funscript_1d_to_2d.py` - Core circular algorithm
4. `processing/funscript_oscillating_2d.py` - Oscillating algorithms
5. `processor.py` - Pipeline execution order (speed before alpha/beta)
6. `ui/main_window.py` - Standalone conversion in UI

## Testing Checklist

- [ ] Test with default 50% threshold
- [ ] Test with low threshold (10%) - should expand motion
- [ ] Test with high threshold (90%) - should compress motion
- [ ] Verify speed.funscript is generated before alpha/beta
- [ ] Test all algorithms: circular, top-left-right, top-right-left
- [ ] Verify UI slider works correctly (0-100 range)
- [ ] Test with existing speed.funscript file
- [ ] Test without existing speed.funscript file
