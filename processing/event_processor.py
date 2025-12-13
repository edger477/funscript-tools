import yaml
import zipfile
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from funscript import Funscript
from processing.funscript_editor import FunscriptEditor, FunscriptEditorError


class EventProcessorError(Exception):
    """Custom exception for errors during event processing."""
    pass


def _load_event_definitions(definitions_path: Path) -> tuple[Dict[str, Any], Dict[str, Dict[str, float]]]:
    """Loads event definitions and normalization config from a YAML file.

    Returns:
        Tuple of (event_definitions, normalization_config)
    """
    try:
        with open(definitions_path, 'r') as f:
            config_data = yaml.safe_load(f)
        if not isinstance(config_data, dict) or 'definitions' not in config_data:
            raise EventProcessorError("Event definitions file must contain a top-level 'definitions' key.")

        # Extract normalization config, use defaults if not present
        normalization_config = config_data.get('normalization', {
            'pulse_frequency': {'max': 200.0},
            'pulse_width': {'max': 100.0},
            'frequency': {'max': 360.0},
            'volume': {'max': 1.0}
        })

        return config_data['definitions'], normalization_config
    except Exception as e:
        raise EventProcessorError(f"Failed to load event definitions from {definitions_path}: {e}")


def _find_target_funscripts(event_file_path: Path, config: dict = None) -> Dict[str, Path]:
    """
    Finds funscript files related to the event file and returns them as a dict
    { 'axis_name': Path_to_funscript }.

    Args:
        event_file_path: Path to the events YAML file
        config: Optional configuration dict with file_management settings
    """
    if not event_file_path.name.endswith(('.yml', '.yaml')):
        raise EventProcessorError(f"Event file must be a .yml or .yaml file: {event_file_path.name}")

    # Extract base name (e.g., 'my_video' from 'my_video.events.yml')
    base_name = event_file_path.name.replace('.events.yml', '').replace('.events.yaml', '')
    if not base_name:
        raise EventProcessorError(f"Could not determine base name from event file: {event_file_path.name}")

    # Determine search directory based on file management mode
    search_dir = event_file_path.parent  # Default: local mode (same dir as YAML)

    if config:
        file_mgmt = config.get('file_management', {})
        if file_mgmt.get('mode') == 'central':
            central_path = file_mgmt.get('central_folder_path', '').strip()
            if central_path:
                search_dir = Path(central_path)

    # Search for funscripts like 'my_video.volume.funscript'
    target_files_paths = list(search_dir.glob(f"{base_name}.*.funscript"))
    if not target_files_paths:
        raise EventProcessorError(f"No funscript files found for base name '{base_name}' in '{search_dir}'.")

    funscripts_by_axis = {}
    for fp in target_files_paths:
        # Extract axis name (e.g., 'volume' from 'my_video.volume.funscript')
        axis_name = fp.stem.replace(f"{base_name}.", "")
        if axis_name:
            funscripts_by_axis[axis_name] = fp
        else:
            print(f"WARNING: Could not determine axis name for {fp.name}. Skipping.")

    if not funscripts_by_axis:
        raise EventProcessorError(f"No valid funscript axes found for processing in '{search_dir}'.")

    return funscripts_by_axis


def _backup_files(files_to_backup: List[Path]) -> Path:
    """
    Creates a zip archive of the provided files.
    Returns the path to the created zip file.
    """
    if not files_to_backup:
        raise EventProcessorError("No files provided for backup.")

    first_file = files_to_backup[0]
    base_name = first_file.name.split('.')[0] # Assuming format like 'basename.axis.funscript'
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_filename = first_file.parent / f"{base_name}.{timestamp}.zip"

    try:
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in files_to_backup:
                zipf.write(file, arcname=file.name)
    except Exception as e:
        raise EventProcessorError(f"Failed to create backup archive: {e}")

    return zip_filename


def _parse_and_validate_user_events(event_file_path: Path, event_definitions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses a user's YAML event file and performs basic validation against definitions.
    """
    try:
        with open(event_file_path, 'r') as f:
            user_data = yaml.safe_load(f)
    except Exception as e:
        raise EventProcessorError(f"Failed to parse user event YAML file '{event_file_path.name}': {e}")

    if not isinstance(user_data, dict) or 'events' not in user_data:
        raise EventProcessorError("User event file must contain a top-level 'events' key.")

    user_events = user_data['events']
    if not isinstance(user_events, list):
        raise EventProcessorError("'events' key in user file must contain a list.")

    validated_events = []
    for i, user_event in enumerate(user_events):
        if not all(k in user_event for k in ['time', 'name']):
            raise EventProcessorError(f"Event #{i+1} in user file is missing required key: 'time' or 'name'.")
        
        event_name = user_event['name']
        if event_name not in event_definitions:
            raise EventProcessorError(f"Event '{event_name}' at time {user_event['time']} is not defined in event_definitions.yml.")

        # Ensure time is in milliseconds
        if not isinstance(user_event['time'], (int, float)):
             raise EventProcessorError(f"Event '{event_name}' at time {user_event['time']} has invalid 'time' format. Must be a number (ms).")
        user_event['time'] = int(user_event['time']) # Convert to int ms


        # Merge default_params with user_provided params
        definition = event_definitions[event_name]
        final_params = definition.get('default_params', {}).copy()
        if 'params' in user_event:
            final_params.update(user_event['params'])
        
        # Token substitution for step parameters
        processed_steps = []
        for step in definition.get('steps', []):
            processed_step = step.copy()
            processed_step_params = step.get('params', {}).copy()
            processed_step_start_offset = step.get('start_offset', 0)

            # Substitute tokens like $duration, $volume_boost
            for k, v in processed_step_params.items():
                if isinstance(v, str) and v.startswith('$'):
                    token = v[1:]
                    if token not in final_params:
                        raise EventProcessorError(f"Token '{token}' not found in params for event '{event_name}'.")
                    processed_step_params[k] = final_params[token]
            
            # Substitute start_offset if it's a token
            if isinstance(processed_step_start_offset, str) and processed_step_start_offset.startswith('$'):
                token = processed_step_start_offset[1:]
                if token not in final_params:
                    raise EventProcessorError(f"Token '{token}' not found in params for event '{event_name}'.")
                processed_step_start_offset = final_params[token]

            processed_step['params'] = processed_step_params
            processed_step['start_offset'] = processed_step_start_offset
            processed_steps.append(processed_step)

        user_event['final_params'] = final_params
        user_event['processed_steps'] = processed_steps
        validated_events.append(user_event)

    return sorted(validated_events, key=lambda x: x['time']) # Sort by time


def process_events(event_file_path_str: str, perform_backup: bool, definitions_path: Path, volume_headroom: int = 10, apply_to_linked: bool = True, config: dict = None) -> Tuple[str, List[str], Path]:
    """
    Main entry point for processing custom events.
    Orchestrates finding files, backing up, parsing, and applying events using FunscriptEditor.

    Args:
        event_file_path_str (str): Path to the user's .events.yml file.
        perform_backup (bool): Whether to create a backup of original funscripts.
        definitions_path (Path): Path to the event_definitions.yml file.
        volume_headroom (int): Amount of headroom to create above highest volume point (0-20, default 10).
        apply_to_linked (bool): Whether to apply operations on main axes to linked axes (default True).
        config (dict): Optional configuration dict with file_management settings.

    Returns:
        Tuple[str, List[str], Path]: A success message, list of names of modified files, and backup path (None if no backup).
    """
    event_file_path = Path(event_file_path_str)

    # 1. Load event definitions and normalization config
    event_definitions, normalization_config = _load_event_definitions(definitions_path)

    # 2. Find target funscripts (using config to determine search location)
    target_funscript_paths_by_axis = _find_target_funscripts(event_file_path, config)
    
    # Get base filename stem for the FunscriptEditor
    first_path = next(iter(target_funscript_paths_by_axis.values()))
    filename_stem = first_path.stem.replace(f".{first_path.stem.split('.')[-1]}", "") # Remove axis part

    # 3. Create Funscript objects and prepare for editor
    funscripts_for_editor = {
        axis_name: Funscript.from_file(path)
        for axis_name, path in target_funscript_paths_by_axis.items()
    }

    editor = FunscriptEditor(funscripts_for_editor, filename_stem, normalization_config, apply_to_linked)

    # 4. Apply headroom adjustment to volume funscript if present
    if 'volume' in funscripts_for_editor and volume_headroom > 0:
        volume_fs = funscripts_for_editor['volume']
        max_volume = np.max(volume_fs.y)  # Internal representation is 0.0-1.0

        # Calculate headroom threshold in normalized units (0.0-1.0)
        headroom_threshold = 1.0 - (volume_headroom / 100.0)

        if max_volume > headroom_threshold:
            # Need to shift down
            shift_down = max_volume - headroom_threshold
            volume_fs.y = np.maximum(0.0, volume_fs.y - shift_down)
            print(f"INFO: Applied volume headroom adjustment. Max volume was {max_volume:.3f}, shifted down by {shift_down:.3f} to create {volume_headroom} units of headroom.")

    # 5. Backup files if requested
    backup_path = None
    if perform_backup:
        # Include the event file in the backup
        files_to_backup = list(target_funscript_paths_by_axis.values()) + [event_file_path]
        backup_path = _backup_files(files_to_backup)
        print(f"Backup created at: {backup_path}")

    # 6. Parse and validate user events
    user_events = _parse_and_validate_user_events(event_file_path, event_definitions)

    # 7. Apply events
    for user_event in user_events:
        event_base_time = user_event['time']
        for step in user_event['processed_steps']:
            operation = step['operation']
            axis = step['axis']
            step_params = step['params']
            start_offset_ms = step['start_offset']

            operation_start_time_ms = event_base_time + start_offset_ms

            # Call the appropriate FunscriptEditor method
            if operation == 'apply_linear_change':
                editor.apply_linear_change(
                    axis=axis,
                    start_time_ms=operation_start_time_ms,
                    duration_ms=step_params['duration_ms'],
                    start_value=step_params['start_value'],
                    end_value=step_params.get('end_value', step_params['start_value']),
                    ramp_in_ms=step_params.get('ramp_in_ms', 0),
                    ramp_out_ms=step_params.get('ramp_out_ms', 0),
                    mode=step_params.get('mode', 'additive')
                )
            elif operation == 'apply_modulation':
                editor.apply_modulation(
                    axis=axis,
                    start_time_ms=operation_start_time_ms,
                    duration_ms=step_params['duration_ms'],
                    waveform=step_params['waveform'],
                    frequency=step_params['frequency'],
                    amplitude=step_params['amplitude'],
                    offset=step_params.get('offset', 0.0),
                    phase=step_params.get('phase', 0.0),
                    ramp_in_ms=step_params.get('ramp_in_ms', 0),
                    ramp_out_ms=step_params.get('ramp_out_ms', 0),
                    mode=step_params.get('mode', 'additive')
                )
            else:
                print(f"WARNING: Unknown operation '{operation}'. Skipping.")

    # 8. Final validation/normalization (if needed, otherwise get report)
    # The current FunscriptEditor stubs do clipping per-operation,
    # but a global validation pass could be added here later if needed.

    # 9. Save modified funscripts
    editor.save_funscripts(event_file_path.parent)

    modified_files = [path.name for path in target_funscript_paths_by_axis.values()]
    success_message = f"Successfully applied {len(user_events)} events to {len(modified_files)} files."
    if perform_backup and backup_path:
        success_message += f"\nBackup created at {backup_path.name}."

    return success_message, modified_files, backup_path
