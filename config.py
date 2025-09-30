import json
import os
from pathlib import Path
from typing import Dict, Any


DEFAULT_CONFIG = {
    "general": {
        "rest_level": 0.4,
        "speed_window_size": 5,
        "accel_window_size": 3
    },
    "speed": {
        "interpolation_interval": 0.1,
        "normalization_method": "max"
    },
    "alpha_beta_generation": {
        "points_per_second": 25,
        "auto_generate": True,
        "algorithm": "top-right-left",
        "min_distance_from_center": 0.1,
        "speed_at_edge_hz": 2.0
    },
    "prostate_generation": {
        "generate_from_inverted": True,
        "algorithm": "tear-shaped",
        "points_per_second": 25,
        "min_distance_from_center": 0.5
    },
    "frequency": {
        "pulse_freq_min": 0.40,
        "pulse_freq_max": 0.95,
        "frequency_ramp_combine_ratio": 2,
        "pulse_frequency_combine_ratio": 3
    },
    "volume": {
        "volume_ramp_combine_ratio": 6.0,
        "prostate_volume_multiplier": 1.5,
        "prostate_rest_level": 0.7,
        "stereostim_volume_min": 0.50,
        "stereostim_volume_max": 1.00,
        "ramp_percent_per_hour": 15
    },
    "pulse": {
        "pulse_width_min": 0.1,
        "pulse_width_max": 0.45,
        "pulse_width_combine_ratio": 3,
        "beta_mirror_threshold": 0.5,
        "pulse_rise_min": 0.00,
        "pulse_rise_max": 0.80,
        "pulse_rise_combine_ratio": 2
    },
    "advanced": {
        "enable_pulse_frequency_inversion": False,
        "enable_volume_inversion": False,
        "enable_frequency_inversion": False,
        "custom_output_directory": ""
    },
    "options": {
        "normalize_volume": True,
        "delete_intermediary_files": True
    },
    "positional_axes": {
        "mode": "motion_axis",  # "legacy" for alpha/beta, "motion_axis" for E1-E4
        "e1": {
            "enabled": True,
            "curve": {
                "name": "Linear",
                "description": "Direct 1:1 mapping",
                "control_points": [(0.0, 0.0), (1.0, 1.0)]
            }
        },
        "e2": {
            "enabled": True,
            "curve": {
                "name": "Ease In",
                "description": "Gradual start, strong finish",
                "control_points": [(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)]
            }
        },
        "e3": {
            "enabled": True,
            "curve": {
                "name": "Ease Out",
                "description": "Strong start, gradual finish",
                "control_points": [(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)]
            }
        },
        "e4": {
            "enabled": True,
            "curve": {
                "name": "Bell Curve",
                "description": "Emphasis on middle range",
                "control_points": [(0.0, 0.0), (0.25, 0.3), (0.5, 1.0), (0.75, 0.3), (1.0, 0.0)]
            }
        }
    }
}

# Parameter validation ranges
PARAMETER_RANGES = {
    "general": {
        "rest_level": (0.0, 1.0),
        "speed_window_size": (1, 30),
        "accel_window_size": (1, 10)
    },
    "speed": {
        "interpolation_interval": (0.01, 1.0)
    },
    "alpha_beta_generation": {
        "points_per_second": (1, 100),
        "min_distance_from_center": (0.1, 0.9),
        "speed_at_edge_hz": (1.0, 5.0)
    },
    "prostate_generation": {
        "points_per_second": (1, 100),
        "min_distance_from_center": (0.3, 0.9)
    },
    "frequency": {
        "pulse_freq_min": (0.0, 1.0),
        "pulse_freq_max": (0.0, 1.0),
        "frequency_ramp_combine_ratio": (1, 10),
        "pulse_frequency_combine_ratio": (1, 10)
    },
    "volume": {
        "volume_ramp_combine_ratio": (1.0, 10.0),
        "prostate_volume_multiplier": (1.0, 3.0),
        "prostate_rest_level": (0.0, 1.0),
        "stereostim_volume_min": (0.0, 1.0),
        "stereostim_volume_max": (0.0, 1.0),
        "ramp_percent_per_hour": (0, 40)
    },
    "pulse": {
        "pulse_width_min": (0.0, 1.0),
        "pulse_width_max": (0.0, 1.0),
        "pulse_width_combine_ratio": (1, 10),
        "beta_mirror_threshold": (0.0, 0.5),
        "pulse_rise_min": (0.0, 1.0),
        "pulse_rise_max": (0.0, 1.0),
        "pulse_rise_combine_ratio": (1, 10)
    },
    "positional_axes": {
        # Note: Individual axis validation handled by motion_axis_generation module
        # Basic positional axes validation
    }
}


class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file, falling back to defaults if file doesn't exist."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.config = self._merge_configs(DEFAULT_CONFIG, loaded_config)
                    self.validate_config()
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration.")
                self.config = DEFAULT_CONFIG.copy()
        return self.config

    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config file: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration with new values."""
        try:
            self.config = self._merge_configs(self.config, new_config)
            self.validate_config()
            return True
        except ValueError as e:
            print(f"Invalid configuration: {e}")
            return False

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = DEFAULT_CONFIG.copy()

    def validate_config(self):
        """Validate configuration values against allowed ranges."""
        for section, params in PARAMETER_RANGES.items():
            if section not in self.config:
                continue

            for param, (min_val, max_val) in params.items():
                if param not in self.config[section]:
                    continue

                value = self.config[section][param]
                if not (min_val <= value <= max_val):
                    raise ValueError(f"Parameter {section}.{param} = {value} is outside valid range [{min_val}, {max_val}]")

        # Additional validation
        freq_config = self.config.get('frequency', {})
        if 'pulse_freq_min' in freq_config and 'pulse_freq_max' in freq_config:
            if freq_config['pulse_freq_min'] >= freq_config['pulse_freq_max']:
                raise ValueError("pulse_freq_min must be less than pulse_freq_max")

        pulse_config = self.config.get('pulse', {})
        if 'pulse_width_min' in pulse_config and 'pulse_width_max' in pulse_config:
            if pulse_config['pulse_width_min'] >= pulse_config['pulse_width_max']:
                raise ValueError("pulse_width_min must be less than pulse_width_max")

        if 'pulse_rise_min' in pulse_config and 'pulse_rise_max' in pulse_config:
            if pulse_config['pulse_rise_min'] >= pulse_config['pulse_rise_max']:
                raise ValueError("pulse_rise_min must be less than pulse_rise_max")

        volume_config = self.config.get('volume', {})
        if 'stereostim_volume_min' in volume_config and 'stereostim_volume_max' in volume_config:
            if volume_config['stereostim_volume_min'] >= volume_config['stereostim_volume_max']:
                raise ValueError("stereostim_volume_min must be less than stereostim_volume_max")

    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result