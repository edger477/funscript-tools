# Funscript Editor: Fundamental Operations Guide

This document is for advanced users who want to create their own composite events in an `event_definitions.yml` file. It details the core building blocks available in the `FunscriptEditor`.

Every operation is applied to a specific `axis` (e.g., `volume`, `pulse_frequency`) at a specified `start_time_ms` for a `duration_ms`.

---

## I. Value-Shaping Operations

These operations modify existing values within a funscript. They are the most common and versatile building blocks.

### 1. `apply_modulation`

This is the most powerful operation for creating dynamic effects. It adds or overwrites a segment of a funscript with a generated waveform.

**Use Cases:**
*   Creating a "buzz" or "hum" on the `volume` axis (like `edge` or `spike`).
*   Creating a wide, slow oscillation on the `volume` axis (like `tranquil`).
*   Making the `pulse_frequency` or `pulse_width` waver rhythmically (like the new `tantalize`).

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `axis` | `string`| **(Required)** The funscript axis to target (e.g., `volume`, `pulse_frequency`). |
| `duration_ms`| `int` | **(Required)** The duration of the effect in milliseconds. |
| `mode` | `string` | **(Required)** How to apply the effect. Must be one of: <br> • `additive`: Adds the generated wave to the existing values. <br> • `overwrite`: Replaces the existing values with the generated wave. |
| `waveform`| `string` | **(Required)** The shape of the wave. Supported: `sin`, `saw`, `square`, `triangle`. |
| `frequency` | `float` | **(Required)** The frequency of the wave in Hz. |
| `amplitude` | `float` | **(Required)** The height of the wave. For `volume` in `additive` mode, this is a special "headroom intensity" from 0.0-1.0. For other axes/modes, it's a direct value (e.g., `0.2` for a wave from -0.2 to +0.2). |
| `offset` | `float` | `Default: 0.0`. A constant value to add to the generated wave, shifting its center point. |
| `phase` | `float` | `Default: 0.0`. The starting phase of the wave, in degrees (0-360). |
| `ramp_in_ms` | `int` | `Default: 0`. Duration in milliseconds for a linear fade-in of the wave's amplitude. |
| `ramp_out_ms`| `int` | `Default: 0`. Duration in milliseconds for a linear fade-out of the wave's amplitude. |


### 2. `apply_linear_change`

This operation is for simple, non-oscillating changes, like setting a value, applying a boost, or creating a simple ramp.

**Use Cases:**
*   Applying a `volume_boost` for the duration of an `edge`.
*   Implementing a `pulse_set` to change the `pulse_frequency` to a new constant value.
*   Creating a long, slow `fadeout` effect on the `volume` axis.

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `axis` | `string`| **(Required)** The funscript axis to target. |
| `duration_ms`| `int` | **(Required)** The duration of the effect in milliseconds. |
| `mode` | `string` | **(Required)** How to apply the effect: `additive` or `overwrite`.|
| `start_value`| `float`| **(Required)** The value of the effect at its beginning. |
| `end_value`| `float` | `Default: start_value`. The value of the effect at its end. If different from `start_value`, this creates a ramp. |
| `ramp_in_ms` | `int` | `Default: 0`. Duration in milliseconds for a fade-in of the *entire effect*. |
| `ramp_out_ms`| `int` | `Default: 0`. Duration in milliseconds for a fade-out of the *entire effect*. |

---

### Example: Building `tantalize` from Scratch

This example shows how an event is composed of multiple steps, each with a potential `start_offset`. All time values are in **milliseconds**.

```yaml
tantalize:
  default_params:
    duration: 12000
    volume_boost: 0.03
    ramp_up: 500
    buzz_freq: 20
    buzz_intensity: 1.0
    pulse_osc_freq: 20
    pulse_osc_amp: 0.1
    width_osc_amp: 0.05
    pulse_delay: 200 # Start the pulse oscillation slightly after the volume change

  steps:
    # 1. Add a small, ramped boost to volume (starts immediately)
    - operation: apply_linear_change
      axis: volume
      start_offset: 0
      params:
        start_value: $volume_boost
        duration_ms: $duration
        ramp_in_ms: $ramp_up
        mode: additive

    # 2. Add the "buzz" on top of the volume (also starts immediately)
    - operation: apply_modulation
      axis: volume
      start_offset: 0
      params:
        waveform: sin
        frequency: $buzz_freq
        amplitude: $buzz_intensity
        duration_ms: $duration
        ramp_in_ms: $ramp_up
        mode: additive

    # 3. Make the pulse frequency waver (starts after a 200ms delay)
    - operation: apply_modulation
      axis: pulse_frequency
      start_offset: $pulse_delay
      params:
        waveform: sin
        frequency: $pulse_osc_freq
        amplitude: $pulse_osc_amp
        duration_ms: $duration - $pulse_delay # Adjust duration for the delay
        mode: additive

    # 4. Make the pulse width waver (also starts after 200ms)
    - operation: apply_modulation
      axis: pulse_width
      start_offset: $pulse_delay
      params:
        waveform: sin
        frequency: $pulse_osc_freq
        amplitude: $width_osc_amp
        duration_ms: $duration - $pulse_delay
        mode: additive
```
