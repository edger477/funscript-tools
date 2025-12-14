# Funscript Editor: Fundamental Operations Guide

This document is for advanced users who want to create their own composite events in an `event_definitions.yml` file. It details the core building blocks available in the `FunscriptEditor`.

Every operation is applied to a specific `axis` (e.g., `volume`, `pulse_frequency`) at a specified `start_time_ms` for a `duration_ms`.

---

## Linked Axes

Some axes are automatically linked, meaning operations applied to a primary axis will also be applied to its linked axes (if those files exist):

- **`volume`** → also applies to `volume-prostate`
- **`alpha`** → also applies to `alpha-prostate`
- **`beta`** → also applies to `beta-prostate`

This means if you apply a modulation to the `volume` axis and a `video.volume-prostate.funscript` file exists, both files will be modified identically.

---

## Value Normalization

All parameter values are automatically normalized from their axis-specific units to the internal 0.0-1.0 funscript range. The normalization is configured in the `normalization` section of your event definitions file:

```yaml
normalization:
  pulse_frequency:
    max: 200.0      # Values in Hz (e.g., 100 Hz → 0.5 normalized)
    unit: "Hz"
  pulse_width:
    max: 100.0      # Values in % (e.g., 50% → 0.5 normalized)
    unit: "%"
  frequency:
    max: 1200.0     # Values in Hz (e.g., 600 Hz → 0.5 normalized)
    unit: "Hz"
  volume:
    max: 1.0        # Already normalized (0.0-1.0)
    unit: "normalized"
```

**Normalization Rules:**
1. If `max` is 1.0, values are assumed to already be normalized (no conversion)
2. If `max` > 1.0 and your value is ≤ 1.0, it's assumed to be pre-normalized (no conversion)
3. Otherwise, the value is divided by `max` to normalize it

**Examples:**
- `pulse_frequency: 100` → normalized to `100 / 200.0 = 0.5`
- `pulse_width: 50` → normalized to `50 / 100.0 = 0.5`
- `volume: 0.3` → already normalized, stays `0.3`
- `frequency: 600` → normalized to `600 / 1200.0 = 0.5`

---

## I. Value-Shaping Operations

These operations modify existing values within a funscript. They are the most common and versatile building blocks.

### 1. `apply_modulation`

This is the most powerful operation for creating dynamic effects. It adds or overwrites a segment of a funscript with a generated waveform.

**Use Cases:**
*   Creating a "buzz" or "hum" on the `volume` axis (like `edge` or `spike`).
*   Creating a wide, slow oscillation on the `volume` axis (like `tranquil`).
*   Making the `pulse_frequency` or `pulse_width` waver rhythmically (like `tantalize`).

**Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `axis` | `string`| **(Required)** | The funscript axis to target (e.g., `volume`, `pulse_frequency`, `alpha`, `beta`). Operations also apply to linked axes automatically. |
| `duration_ms`| `int` | **(Required)** | The duration of the effect in milliseconds. |
| `waveform`| `string` | **(Required)** | The shape of the wave. Supported waveforms: <br>• `sin` - Smooth sinusoidal oscillation <br>• `square` - Square wave (use with `duty_cycle`) <br>• `triangle` - Linear ramp up and down <br>• `sawtooth` - Linear ramp up with instant drop |
| `frequency` | `float` | **(Required)** | The frequency of the wave in Hz. **Avoid multiples of 10 Hz** (10, 20, 30...) to prevent sampling aliasing issues. Use values like 9, 11, 15, 21, 23, 65 Hz instead. |
| `amplitude` | `float` | **(Required)** | The swing amplitude of the wave in axis-specific units (will be normalized). The wave oscillates ±amplitude around the center point. For example, `amplitude: 0.35` on volume creates oscillations from -0.35 to +0.35 relative to the baseline. |
| `offset` | `float` | `0.0` | Additive shift to the baseline in axis-specific units (will be normalized). <br>• In `additive` mode: shifts the center point of oscillation relative to original values. <br>• In `overwrite` mode: sets the baseline value around which the wave oscillates. |
| `phase` | `float` | `0.0` | The starting phase of the wave, in degrees (0-360). Use this to offset the waveform's starting position. |
| `duty_cycle` | `float` | `0.5` | For `square` waveform only: the percentage of time at maximum value (0.01-0.99). Default 0.5 is 50% duty cycle (equal high/low time). Higher values = more time at max, lower values = more time at min. Ignored for other waveforms. |
| `mode` | `string` | `additive` | How to apply the effect: <br>• `additive`: `final = original + offset + amplitude*waveform(...)` <br>• `overwrite`: `final = offset + amplitude*waveform(...)` |
| `ramp_in_ms` | `int` | `0` | Duration in milliseconds for a linear fade-in of the wave's amplitude envelope. |
| `ramp_out_ms`| `int` | `0` | Duration in milliseconds for a linear fade-out of the wave's amplitude envelope. |

**Mathematical Formulas:**
- **Additive mode**: `final = original_value + normalized_offset + normalized_amplitude * waveform(frequency, time, phase)`
- **Overwrite mode**: `final = normalized_offset + normalized_amplitude * waveform(frequency, time, phase)`

Where `waveform()` generates values in the range [-1, +1] based on the selected waveform type:
- **sin**: `sin(2π * frequency * time + phase)` - smooth sinusoidal oscillation
- **square**: `+1` for duty_cycle% of period, `-1` for remainder - sharp on/off transitions
- **triangle**: linear ramp from -1 to +1 (first half), then +1 to -1 (second half)
- **sawtooth**: linear ramp from -1 to +1, then instant reset

**Important Notes:**
1. All waveforms are **bipolar** (range from -1 to +1), creating true oscillations above and below the center point.
2. Final values are **clipped to 0.0-1.0** range after all operations to prevent out-of-bounds values.
3. Ramp envelopes are applied to the entire generated wave, creating smooth fade-in/fade-out effects.
4. **Sampling aliasing**: If your modulation frequency matches or is a multiple of the funscript sample rate (~10 Hz), you may get no oscillation because all samples land at the same phase. Use frequencies like 9, 11, 15, 21, 23, 65 Hz instead of 10, 20, 30, 60 Hz.
5. **Square wave duty cycle**: Use duty_cycle < 0.5 for short pulses (more time at min), > 0.5 for wide pulses (more time at max).

---

### 2. `apply_linear_change`

This operation is for simple, non-oscillating changes, like setting a value, applying a boost, or creating a simple ramp.

**Use Cases:**
*   Applying a `volume_boost` for the duration of an effect.
*   Setting the `pulse_frequency` to a new constant value.
*   Creating a long, slow fade-in or fade-out effect on any axis.
*   Ramping between two values over time.

**Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `axis` | `string`| **(Required)** | The funscript axis to target. Operations also apply to linked axes automatically. |
| `duration_ms`| `int` | **(Required)** | The duration of the effect in milliseconds. |
| `start_value`| `float`| **(Required)** | The value of the effect at its beginning, in axis-specific units (will be normalized). |
| `end_value`| `float` | `start_value` | The value of the effect at its end, in axis-specific units (will be normalized). If different from `start_value`, creates a linear ramp between the two values. |
| `mode` | `string` | `additive` | How to apply the effect: <br>• `additive`: Adds the linear change to existing values. <br>• `overwrite`: Replaces existing values with the linear change. |
| `ramp_in_ms` | `int` | `0` | Duration in milliseconds for a fade-in envelope applied to the entire effect. |
| `ramp_out_ms`| `int` | `0` | Duration in milliseconds for a fade-out envelope applied to the entire effect. |

**Mathematical Formula:**
- **Linear interpolation**: Values are interpolated linearly from `normalized_start_value` to `normalized_end_value` over the duration.
- **Additive mode**: `final = original_value + interpolated_value * envelope`
- **Overwrite mode**: `final = interpolated_value * envelope`

**Important Notes:**
1. If `start_value == end_value`, this creates a constant value for the duration (no ramp).
2. Ramp envelopes are applied **multiplicatively** to the linear values, allowing smooth transitions in and out.
3. Final values are **clipped to 0.0-1.0** range after all operations.

---

## II. Event Composition

Events are composed of multiple **steps**, each representing one operation. Steps can have different `start_offset` values to sequence operations in time.

### Event Structure

```yaml
event_name:
  default_params:
    # Define default parameter values with descriptive names
    duration_ms: 10000
    volume_boost: 0.05
    buzz_freq: 15

  steps:
    # Step 1: Starts at event time (offset 0)
    - operation: apply_linear_change
      axis: volume
      start_offset: 0
      params:
        start_value: $volume_boost
        end_value: $volume_boost
        duration_ms: $duration_ms
        mode: additive

    # Step 2: Starts 200ms after event time
    - operation: apply_modulation
      axis: volume
      start_offset: 200
      params:
        waveform: sin
        frequency: $buzz_freq
        amplitude: 0.1
        duration_ms: $duration_ms
        mode: additive
```

### Parameter Substitution

Use `$parameter_name` to reference values from `default_params`. This allows:
1. **Reusability**: Users can override defaults when placing events
2. **Clarity**: Descriptive names instead of magic numbers
3. **Calculations**: Simple math like `$duration_ms - $start_offset`

**Example user event file:**
```yaml
events:
  - time: 5000
    name: edge
    params:
      duration_ms: 12000    # Override default
      buzz_freq: 11         # Override default
```

---

## III. Complete Example: Building a Complex Effect

This example shows how to create a multi-layered effect with synchronized operations on different axes:

```yaml
intense_edge:
  default_params:
    duration_ms: 15000
    pulse_rate: 120          # Hz - will be normalized by max 200.0
    volume_boost: 0.05       # Already normalized (0.0-1.0)
    buzz_freq: 11            # Hz - avoid aliasing
    buzz_amplitude: 0.08     # Normalized
    alpha_freq: 9            # Hz - avoid aliasing
    alpha_amp: 0.35          # Normalized
    ramp_ms: 500

  steps:
    # 1. Set high pulse frequency
    - operation: apply_linear_change
      axis: pulse_frequency
      start_offset: 0
      params:
        start_value: $pulse_rate      # 120 Hz → normalized to 0.6
        end_value: $pulse_rate
        duration_ms: $duration_ms
        ramp_in_ms: $ramp_ms
        ramp_out_ms: $ramp_ms
        mode: overwrite

    # 2. Add volume boost
    - operation: apply_linear_change
      axis: volume
      start_offset: 0
      params:
        start_value: $volume_boost    # Already normalized
        end_value: $volume_boost
        duration_ms: $duration_ms
        ramp_in_ms: $ramp_ms
        ramp_out_ms: $ramp_ms
        mode: additive

    # 3. Add high-frequency buzz on volume
    - operation: apply_modulation
      axis: volume
      start_offset: 0
      params:
        waveform: sin
        frequency: $buzz_freq         # 11 Hz (avoid 10 Hz aliasing)
        amplitude: $buzz_amplitude    # ±0.08 oscillation
        offset: 0
        duration_ms: $duration_ms
        ramp_in_ms: $ramp_ms
        ramp_out_ms: $ramp_ms
        mode: additive

    # 4. Modulate alpha axis (also affects alpha-prostate if it exists)
    - operation: apply_modulation
      axis: alpha
      start_offset: 0
      params:
        waveform: sin
        frequency: $alpha_freq        # 9 Hz (avoid 10 Hz aliasing)
        amplitude: $alpha_amp         # ±0.35 oscillation
        offset: 0.55                  # Center point at 0.55
        duration_ms: $duration_ms
        ramp_in_ms: $ramp_ms
        ramp_out_ms: $ramp_ms
        mode: additive
```

**What this does:**
1. Sets pulse frequency to 120 Hz (high intensity) with smooth ramp in/out
2. Adds 5% volume boost throughout the effect
3. Overlays an 11 Hz buzzing sensation on top
4. Modulates the alpha axis with a 9 Hz wave centered at 0.55 (affects both alpha and alpha-prostate files)

---

## IV. Best Practices

### Frequency Selection
**Avoid sampling aliasing** by not using frequencies that are multiples of 10 Hz:
- ❌ Bad: 10, 20, 30, 60, 100 Hz
- ✅ Good: 9, 11, 15, 17, 21, 23, 65, 120 Hz

### Ramp Usage
- Use `ramp_in_ms` and `ramp_out_ms` to create smooth transitions
- Short effects (3-5s): ramp_ms = 200-250
- Medium effects (5-10s): ramp_ms = 500
- Long effects (>10s): ramp_ms = 1000-2000

### Mode Selection
- **Additive mode**: Best for effects that layer on top of existing patterns
- **Overwrite mode**: Best for completely replacing values in a time segment

### Parameter Organization
- Group related parameters together in `default_params`
- Use descriptive names that explain the purpose
- Provide sensible defaults that create a good effect without user customization

### Multi-Axis Effects
- Operations on `volume`, `alpha`, `beta` automatically affect their `-prostate` variants
- Synchronize operations across axes using the same `start_offset` values
- Use different frequencies on different axes to create complex, layered sensations

---

## V. Troubleshooting

### No oscillations visible
**Cause**: Sampling aliasing - frequency matches sample rate
**Solution**: Change frequency from multiples of 10 (e.g., 10→11, 20→21, 60→65)

### Effect too weak
**Cause**: Amplitude too small or values getting clipped
**Solution**: Increase amplitude, or use volume headroom feature to create space for additive effects

### Values clipping at 0 or 100
**Cause**: Effects pushing values out of valid 0.0-1.0 range
**Solution**:
- Reduce amplitude or offset values
- Use the volume headroom setting in the UI (shifts baseline down before applying effects)
- Switch from additive to overwrite mode if appropriate

### Effect not smooth
**Cause**: Missing or insufficient ramp envelopes
**Solution**: Add or increase `ramp_in_ms` and `ramp_out_ms` values

### Linked axis not affected
**Cause**: Linked axis file doesn't exist
**Solution**: Ensure files like `video.volume-prostate.funscript`, `video.alpha-prostate.funscript` exist alongside the primary axis files
