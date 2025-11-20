# Alpha/Beta Generation Algorithm Redesign

## Major Change: Stroke-Relative → Global Center

### Previous Algorithm (Stroke-Relative)
Motion was created **around each individual stroke's center point**:

```python
center = (end_p + start_p) / 2  # Stroke midpoint
r = (start_p - end_p) / 2       # Half stroke range
x = center + r * np.cos(theta)  # Relative to stroke center
y = r * np.sin(theta) + 0.5     # Beta centered at 0.5
```

**Problem:**
- A stroke from 0.2→0.8 created motion centered at 0.5
- With max radius_scale, alpha/beta still only oscillated 0.2-0.8
- **Never reached the edges** (0,0) or (1,1)

### New Algorithm (Global Center)
All motion is from the **global center (0.5, 0.5)**:

```python
# Scale radius: 0 to 0.5 (circle boundary at edges)
target_radius = 0.5 * radius_scale

# Map funscript position to angle
position_angles = (1.0 - current_positions) * np.pi

# Generate from global center (0.5, 0.5)
x = 0.5 + target_radius * np.cos(position_angles)
y = 0.5 + target_radius * np.sin(position_angles)
```

**Result:**
- With `radius_scale = 1.0`: radius = 0.5 → **reaches circle edge**
- Position 1.0 → (1.0, 0.5) - right edge
- Position 0.0 → (0.0, 0.5) - left edge
- Position 0.5 → (0.5, 1.0) - top edge

## Behavior Comparison

### Example: Stroke from position 0.2 to 0.8

#### Old Algorithm (max speed):
```
center = 0.5, r = 0.3
Alpha range: 0.5 ± 0.3 = 0.2 to 0.8
Beta range: 0.5 ± 0.3 = 0.2 to 0.8
NEVER reaches 0 or 1
```

#### New Algorithm (max speed):
```
target_radius = 0.5
Position 0.2 → angle = 144° → Alpha ≈ 0.09, Beta ≈ 0.79
Position 0.8 → angle = 36° → Alpha ≈ 0.90, Beta ≈ 0.79
CAN reach near 0 and 1
```

## Speed Threshold Scaling

### Min Distance from Center (0.1)
- Slow speeds (below threshold): Stay near center
- `radius = 0.5 * 0.1 = 0.05` (very small circle)
- Alpha/Beta range: ~0.45 to 0.55

### Max Distance (1.0)
- Fast speeds (at/above threshold): Reach circle edge
- `radius = 0.5 * 1.0 = 0.5` (full circle)
- Alpha/Beta range: 0.0 to 1.0 (full range!)

### 50% Speed Threshold Example

| Speed Value | Radius Scale | Radius | Alpha Range | Beta Range |
|-------------|--------------|--------|-------------|------------|
| 0% | 0.1 | 0.05 | 0.45-0.55 | 0.45-0.55 |
| 25% | 0.55 | 0.275 | 0.225-0.775 | 0.225-0.775 |
| 50%+ | 1.0 | 0.5 | 0.0-1.0 | 0.0-1.0 |

## Angle Mapping

### Circular Algorithm (0°-180°)
- Position 1.0 → 0° → (1.0, 0.5) - right
- Position 0.5 → 90° → (0.5, 1.0) - top
- Position 0.0 → 180° → (0.0, 0.5) - left

### Top-Left-Right (0°-270°)
- Position 1.0 → 0° → (1.0, 0.5) - right
- Position 0.67 → 90° → (0.5, 1.0) - top
- Position 0.33 → 180° → (0.0, 0.5) - left
- Position 0.0 → 270° → (0.5, 0.0) - bottom

### Top-Right-Left (0°-90°)
- Position 1.0 → 0° → (1.0, 0.5) - right
- Position 0.5 → 45° → (0.85, 0.85) - top-right
- Position 0.0 → 90° → (0.5, 1.0) - top

## Impact on Users

### What Changes
1. **Full Range Motion**: Fast speeds now reach edges (0,0) and (1,1)
2. **Speed Matters More**: Speed threshold has dramatic effect on motion range
3. **Uniform Scaling**: All motion scales uniformly from center

### What Stays Same
- Speed threshold percentage control (0-100%)
- Min distance from center setting (0.1-0.9)
- Three algorithms: circular, top-left-right, top-right-left
- Speed funscript used for radius scaling

### Migration Notes
- Existing configurations will work but produce **different motion patterns**
- Motion will be **more expanded** at high speeds
- May need to **adjust min_distance_from_center** settings
- Recommended: Start with default 50% threshold and 0.1 min distance

## Testing Recommendations

1. **Test at extremes:**
   - Speed threshold 0% → everything at max radius
   - Speed threshold 100% → everything at min radius

2. **Verify full range:**
   - Check alpha/beta reach 0.0-1.0 at max speed
   - Check alpha/beta stay near 0.5 at min speed

3. **Test all algorithms:**
   - Circular (semicircle)
   - Top-left-right (3/4 circle)
   - Top-right-left (quarter circle)

4. **Visual inspection:**
   - Plot alpha vs beta to verify circular patterns
   - Confirm motion is centered at (0.5, 0.5)
