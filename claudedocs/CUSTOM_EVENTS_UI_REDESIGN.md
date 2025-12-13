# Custom Events Dialog - UI Redesign Specification

## Overview
Complete redesign of the Custom Events Dialog to provide a visual, user-friendly interface for creating and managing custom events without manual YAML editing.

## Current Issues
- Text-only YAML editor is error-prone
- No validation until file selection
- No visual timeline of events
- No parameter discovery or guidance
- Requires knowledge of YAML syntax and event structure

## New UI Architecture

### Layout Structure (3-Panel Design)

```
┌─────────────────────────────────────────────────────────────────┐
│ Custom Event Builder                                    [×]      │
├─────────────────────────────────────────────────────────────────┤
│ Event File: [video.events.yml                    ] [Load] [Save]│
├──────────────┬──────────────────────────────┬───────────────────┤
│              │                              │                   │
│  EVENT       │  PARAMETERS                  │   TIMELINE        │
│  LIBRARY     │                              │                   │
│              │  Event: edge                 │   0:00            │
│ [Search...]  │  ┌────────────────────────┐  │    ├─ edge       │
│              │  │ Duration (ms)          │  │   0:15           │
│ General:     │  │ [15000        ]        │  │    ├─ tranquil   │
│  ◉ edge      │  │                        │  │   0:35           │
│  ○ tranquil  │  │ Buzz Freq (Hz)         │  │    └─ edge       │
│              │  │ [60           ]        │  │   0:50           │
│ MCB:         │  │                        │  │                   │
│  ○ submit    │  │ Buzz Intensity         │  │  [Add Event]     │
│  ○ edge      │  │ [0.10         ] 10%    │  │  [Edit Event]    │
│  ○ edge_ce   │  │                        │  │  [Remove Event]  │
│  ○ obey      │  │ Volume Boost           │  │  [Duplicate]     │
│  ○ denial    │  │ [0.03         ] 3%     │  │                   │
│  ...         │  │                        │  │  ✓ Auto-sort by  │
│              │  │ Ramp Up (ms)           │  │    time          │
│ Clutch:      │  │ [250          ]        │  │                   │
│  ○ good_slave│  │                        │  │                   │
│  ○ reward    │  └────────────────────────┘  │                   │
│  ○ push      │                              │                   │
│  ...         │  [Apply Parameters]          │                   │
│              │  [Reset to Defaults]         │                   │
├──────────────┴──────────────────────────────┴───────────────────┤
│ Options:                                                         │
│ ✓ Backup files   ✓ Apply to linked axes   Headroom: [10   ]    │
├─────────────────────────────────────────────────────────────────┤
│ [View YAML] [Apply Effects] [Restore Backup] [Close]            │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Event Library Panel (Left)
**Purpose:** Browse and select from available event definitions

**Features:**
- **Search box:** Filter events by name or keywords
- **Categorization:** Group events by source (General, MCB, Clutch)
- **Radio buttons:** Single event selection for parameter editing
- **Event metadata display:** Show brief description on hover
- **Add to timeline button:** Quick add selected event with default params

**Implementation:**
- Use ttk.Treeview with categories as parent nodes
- Search filters visible items in real-time
- Double-click to add event to timeline at current time

### 2. Parameters Panel (Center)
**Purpose:** Edit parameters for selected event

**Features:**
- **Dynamic form generation:** Create controls based on event's default_params
- **Smart input controls:**
  - Spinbox for numeric values (duration_ms, frequencies)
  - Scale/Slider for 0-1 values (amplitudes, intensities)
  - Entry for all values with validation
  - Unit labels (Hz, ms, %)
  - Real-time validation with visual feedback
- **Parameter descriptions:** Tooltip or help text for each parameter
- **Normalization indicators:** Show when values will be normalized
- **Reset button:** Restore default values
- **Apply button:** Update event in timeline

**Control Type Selection Logic:**
```python
def create_control(param_name, param_value):
    if param_name.endswith('_ms'):
        return Spinbox(from_=0, to=60000, increment=100)
    elif param_name.endswith('_freq'):
        return Spinbox(from_=1, to=200, increment=1)
    elif 'amplitude' in param_name or 'intensity' in param_name:
        return Scale(from_=0.0, to=1.0, resolution=0.01)
    elif 'boost' in param_name or 'offset' in param_name:
        return Scale(from_=-1.0, to=1.0, resolution=0.01)
    else:
        return Entry()  # Generic entry with validation
```

### 3. Timeline Panel (Right)
**Purpose:** Visual timeline of events with time markers

**Features:**
- **Time markers:** Show event times in MM:SS format
- **Event list:** Ordered by time, showing event name
- **Visual duration bars:** Optional graphical representation
- **Selection:** Click to select event for editing
- **Reordering:** Drag-and-drop to change time (optional for v1)
- **Context menu:** Right-click for duplicate/delete
- **Buttons:**
  - Add Event: Add selected event from library
  - Edit Event: Modify selected timeline event
  - Remove Event: Delete from timeline
  - Duplicate: Copy event with offset time
- **Auto-sort checkbox:** Automatically order by time

**Timeline Event Structure:**
```python
{
    'time': 15000,           # milliseconds
    'name': 'edge',          # event type
    'params': {              # user-specified parameters
        'duration_ms': 15000,
        'buzz_freq': 60,
        ...
    }
}
```

### 4. File Operations Bar (Top)
- **Event file path:** Entry showing current .events.yml file
- **Load button:** Load existing event file
- **Save button:** Save current timeline to file
- **New button:** Clear timeline and start fresh

### 5. Options Bar (Bottom)
- Same as current: backup checkbox, linked axes checkbox, headroom spinbox

### 6. Action Buttons (Bottom)
- **View YAML:** Pop-up dialog showing generated YAML
- **Apply Effects:** Process events (same as current)
- **Restore Backup:** Same as current
- **Close:** Exit dialog

## Dynamic Form Generation

### Parameter Type Detection
```python
PARAMETER_CONTROLS = {
    # Time parameters
    'duration_ms': {'type': 'spinbox', 'from': 0, 'to': 60000, 'increment': 100, 'unit': 'ms'},
    'ramp_ms': {'type': 'spinbox', 'from': 0, 'to': 10000, 'increment': 50, 'unit': 'ms'},
    'ramp_in_ms': {'type': 'spinbox', 'from': 0, 'to': 10000, 'increment': 50, 'unit': 'ms'},
    'ramp_out_ms': {'type': 'spinbox', 'from': 0, 'to': 10000, 'increment': 50, 'unit': 'ms'},

    # Frequency parameters
    '*_freq': {'type': 'spinbox', 'from': 1, 'to': 200, 'increment': 1, 'unit': 'Hz'},
    'pulse_rate': {'type': 'spinbox', 'from': 1, 'to': 200, 'increment': 1, 'unit': 'Hz'},

    # Percentage/normalized parameters
    '*_amplitude': {'type': 'scale', 'from': 0.0, 'to': 1.0, 'resolution': 0.01, 'unit': '%'},
    '*_intensity': {'type': 'scale', 'from': 0.0, 'to': 1.0, 'resolution': 0.01, 'unit': '%'},
    '*_boost': {'type': 'scale', 'from': -0.5, 'to': 0.5, 'resolution': 0.01, 'unit': '%'},
    'offset': {'type': 'scale', 'from': -1.0, 'to': 1.0, 'resolution': 0.01, 'unit': ''},

    # Pulse width (percentage)
    'pulse_width': {'type': 'spinbox', 'from': 0, 'to': 100, 'increment': 1, 'unit': '%'},

    # Phase (degrees)
    '*_phase': {'type': 'spinbox', 'from': 0, 'to': 360, 'increment': 15, 'unit': '°'},

    # Volume (normalized)
    'volume*': {'type': 'scale', 'from': 0.0, 'to': 1.0, 'resolution': 0.01, 'unit': ''},
}
```

### Wildcard Pattern Matching
```python
def match_parameter_pattern(param_name):
    """Match parameter name to control configuration using wildcards"""
    for pattern, config in PARAMETER_CONTROLS.items():
        if pattern.startswith('*'):
            if param_name.endswith(pattern[1:]):
                return config
        elif pattern.endswith('*'):
            if param_name.startswith(pattern[:-1]):
                return config
        elif pattern == param_name:
            return config
    return {'type': 'entry'}  # Default to generic entry
```

## Workflow Examples

### Creating New Event Timeline
1. Click "New" or select empty .events.yml file
2. Browse event library (left panel)
3. Click "edge" event in General category
4. Parameters panel shows: duration_ms, buzz_freq, buzz_intensity, volume_boost, ramp_up_ms
5. Adjust parameters using spinboxes/sliders
6. Click "Add Event" in timeline panel
7. Enter time: "0:15" (15 seconds)
8. Event appears in timeline at 15s
9. Repeat for more events
10. Click "Save" to write .events.yml file
11. Click "Apply Effects" to process

### Editing Existing Event File
1. Click "Load" button
2. Select "video.events.yml"
3. Timeline panel populates with existing events
4. Click event in timeline to select
5. Parameters panel shows event's current parameters
6. Modify parameters
7. Click "Apply Parameters" to update
8. Timeline updates automatically
9. Click "Save" to persist changes

### Quick Event Addition
1. Select event in library
2. Double-click or drag to timeline
3. Event added at current playhead position (or prompted for time)
4. Uses default parameters
5. Can edit afterward if needed

## Implementation Classes

### EventLibraryPanel
- Manages event browsing and selection
- Loads definitions from YAML
- Provides search/filter
- Emits events when user selects

### ParameterPanel
- Dynamic form generation
- Validation and type conversion
- Parameter value management
- Emits events when parameters change

### TimelinePanel
- Event list management
- Time-based ordering
- Selection and editing
- Add/remove/duplicate operations

### EventBuilderDialog
- Main container
- Coordinates panels
- File I/O operations
- YAML generation/parsing
- Integration with existing processing backend

## Data Flow

```
User Action → Panel Event → Dialog Controller → Update Other Panels
                                              ↓
                                    Generate YAML (on save)
                                              ↓
                                    Pass to process_events()
```

## Backward Compatibility

### Loading Legacy YAML Files
- Parse existing .events.yml files
- Populate timeline with events
- Allow editing with new UI
- Save back to same format

### Manual YAML Editing
- "View YAML" button shows generated YAML
- Optional: Allow editing YAML directly in popup
- Re-parse to update UI panels

## Validation

### Real-time Validation
- Parameter ranges checked on input
- Invalid values highlighted in red
- Tooltips explain valid ranges
- Prevent saving invalid data

### Pre-apply Validation
- Check all events have required parameters
- Verify time values are valid
- Ensure no time conflicts (optional warning)
- Same validation as current text-based system

## Phase 1 Implementation (MVP)
1. Basic 3-panel layout
2. Event library with categories
3. Dynamic parameter forms for common types
4. Simple timeline list (no drag-drop)
5. Load/Save YAML files
6. Apply effects integration

## Phase 2 Enhancements
1. Event search and filtering
2. Drag-and-drop timeline reordering
3. Visual duration bars
4. Event templates and favorites
5. Time input helpers (MM:SS parser)
6. Parameter presets
7. Event duplication with offset
8. Undo/redo support

## Benefits
- **Lower barrier to entry:** Visual interface, no YAML knowledge needed
- **Fewer errors:** Validation prevents invalid parameters
- **Faster workflow:** Browse events, quick parameter adjustment
- **Better discovery:** See all available events and their parameters
- **Timeline visualization:** Clear overview of event sequence
- **Professional UX:** Modern, intuitive interface
- **Backward compatible:** Works with existing .events.yml files
