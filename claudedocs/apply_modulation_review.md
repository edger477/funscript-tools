# Code Review: `apply_modulation` Function

## Summary
The `apply_modulation` function in `processing/funscript_editor.py:135-242` has critical issues preventing proper sinusoidal oscillations, particularly for the volume axis.

## Issues Identified

### 1. **Headroom-Aware Mode is Overly Complex**
**Location:** Lines 172-182

**Problem:**
- Calculates available "headroom" (1.0 - current_value) and uses it to scale amplitude
- Remaps sine wave from bipolar [-1, 1] to unipolar [0, 1]
- This creates a buzz that only adds positive values, eliminating oscillations

**Current Code:**
```python
if mode == 'additive' and axis == 'volume':
    # Headroom-aware additive modulation for volume
    original_values_in_range = fs.y[indices].copy()
    current_values_after_offset = original_values_in_range + self._normalize_value(axis, offset)

    headroom = 1.0 - current_values_after_offset
    headroom[headroom < 0] = 0

    mod_amplitude = headroom * amplitude  # amplitude is intensity (0.0-1.0)

    # Remap base_wave from [-1, 1] to [0, 1] for purely additive buzz
    positive_base_wave = (base_wave + 1) / 2
    generated_wave = mod_amplitude * positive_base_wave
```

**Why This Fails:**
- `positive_base_wave = (base_wave + 1) / 2` converts sin wave to range [0, 1]
- Result: values only increase, never decrease → no oscillation
- The headroom calculation makes amplitude unpredictable based on current values

### 2. **Offset Applied Incorrectly**
**Location:** Lines 184, 192-193

**Problem:**
- Offset is added to values separately from modulation
- Should act as a multiplier for the entire section, not an additive constant

**Current Code:**
```python
fs.y[indices] = fs.y[indices] + self._normalize_value(axis, offset)  # Applied separately
```

### 3. **Confusing Parameter Semantics**
**Problem:**
- `amplitude` parameter has different meanings in different modes:
  - Volume additive: intensity (0.0-1.0) of headroom usage
  - Other modes: direct normalized value
- This is unintuitive and makes the YAML configs hard to understand

## Proposed Simplified Implementation

### Mathematical Model

**Additive mode:**
```
final_value = original_value + offset + amplitude * sin(2πft + φ)
```

**Overwrite mode:**
```
final_value = offset + amplitude * sin(2πft + φ)
```

Where:
- `amplitude`: Direct swing amount in normalized units [0.0, 1.0]
- `offset`: Baseline value or shift (default 0.0)
- Sine wave remains bipolar [-1, 1], creating true oscillations

### Benefits
1. **Predictable oscillations:** Values swing ±amplitude around (original + offset)
2. **Simple offset semantics:** Shifts the center point of oscillation
3. **No special cases:** Same logic for all axes
4. **True sinusoidal behavior:** Matches frequency parameter expectations

## Recommended Fix

Replace lines 172-193 with simplified logic:

```python
# Generate modulation wave (bipolar)
normalized_amplitude = self._normalize_value(axis, amplitude)
normalized_offset = self._normalize_value(axis, offset)
modulation_wave = normalized_amplitude * base_wave  # Bipolar [-amplitude, +amplitude]

# The generated wave is always: offset + modulation
# The difference is in how it's applied (add vs replace)
generated_wave = normalized_offset + modulation_wave
```

And update the final application (around lines 224-231):

```python
# Apply envelope to the generated wave
final_effect_values = generated_wave * envelope

if mode == 'additive':
    # Additive: add (offset + modulation) to original values
    # Result: original_value + offset + amplitude*sin(...)
    fs.y[indices] = fs.y[indices] + final_effect_values
elif mode == 'overwrite':
    # Overwrite: replace values with (offset + modulation)
    # Result: offset + amplitude*sin(...)
    fs.y[indices] = final_effect_values
else:
    print(f"WARNING: Unknown mode '{mode}'. Skipping.")
    return

# Ensure values remain within [0.0, 1.0]
fs.y[indices] = np.clip(fs.y[indices], 0.0, 1.0)
```

## Impact on Event Definitions

### Current `edge` Event (config.event_definitions.yml:5-30)
```yaml
edge:
  default_params:
    buzz_freq: 60          # Hz - should create 60 oscillations per second
    buzz_intensity: 0.3    # Currently: 30% of headroom
    volume_boost: 0.03     # +3% volume boost
```

**After fix:**
- `buzz_intensity: 0.3` → Direct amplitude of ±0.3 (or ±30 in funscript units)
- Will create visible 60 Hz oscillations around current value
- More predictable and testable behavior

### Current `tranquil` Event (config.event_definitions.yml:32-50)
```yaml
tranquil:
  default_params:
    osc_freq: 15           # Hz - slow oscillation
    osc_amplitude: 0.5     # ±0.5 swing
    osc_offset: -0.25      # Currently adds -0.25, should multiply
```

**After fix:**
- `osc_amplitude: 0.5` → ±0.5 swing (±50 funscript units)
- `osc_offset: -0.25` → Shifts baseline down by 0.25 (or -25 funscript units)
- Result: oscillates between (original - 0.75) and (original + 0.25)

## Testing Recommendations

After implementing the fix, test with:

1. **Simple sine test:**
   - Flat funscript at value 50
   - Apply 1 Hz sine, amplitude 0.1
   - Verify: values oscillate between 40 and 60

2. **Frequency verification:**
   - Apply 10 Hz sine for 1 second
   - Count peaks in output: should be ~10

3. **Offset baseline shift:**
   - Original values at 50
   - Apply with offset=0.1, amplitude=0.05
   - Verify: oscillates between 55 and 65 (centered at 60)

4. **Edge event:**
   - Verify 60 Hz oscillations are visible
   - Check that volume_boost and buzz work together correctly

## Files to Review/Modify

1. **processing/funscript_editor.py:135-242** - Main fix location
2. **config.event_definitions.yml:5-50** - May need parameter adjustments
3. **@analysis/sample_events.yaml** - Update example parameters if needed
4. **tests/test_event_processor.py** - Add tests for new behavior

## Summary of Changes Needed

1. Remove headroom-aware logic entirely
2. Keep sine wave bipolar [-1, 1] for true oscillations
3. Change offset from additive to multiplicative
4. Simplify code by removing special cases
5. Update event definitions to match new parameter semantics
