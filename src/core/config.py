import copy
import json
from pathlib import Path


DEFAULT_CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG = {
    "debug": {
        "save_frames": False,
        "dir": "debug_frames",
    },
    "window": {
        "owner_contains": "runelite",
        "title_contains": "",
    },
    "attack": {
        "min_area": 200,
        "max_area": 12000,
        "min_width": 30,
        "max_width": 160,
        "min_height": 30,
        "max_height": 140,
        "min_aspect_ratio": 0.45,
        "max_aspect_ratio": 2.6,
        "target_missing_streak": 2,
        "click_cooldown_seconds": [0.15, 0.35],
        "engaged_hold_seconds": [1.2, 1.8],
        "track_max_distance": 90,
        "status_log_interval_seconds": 1.0,
        "engaged_panel": {
            "missing_streak": 3,
            "roi": {
                "left": 0,
                "top": 0,
                "width": 320,
                "height": 140,
            },
            "bar_roi": {
                "left": 0,
                "top": 25,
                "width": 320,
                "height": 95,
            },
            "color_ranges": [
                [[0, 80, 40], [10, 255, 255]],
                [[170, 80, 40], [180, 255, 255]],
                [[45, 40, 40], [95, 255, 255]],
            ],
            "min_area": 500,
            "min_width": 70,
            "max_width": 220,
            "min_height": 8,
            "max_height": 30,
        },
        "color_ranges": [
            [[0, 120, 120], [10, 255, 255]],
            [[170, 120, 120], [180, 255, 255]],
        ],
    },
    "heal": {
        "eat_at_hp": 15,
        "min_area": 200,
        "click_cooldown_seconds": [1.0, 1.5],
        "no_food_retry_seconds": 1.0,
        "no_food_log_interval_seconds": 2.0,
        "color_ranges": [
            [[85, 120, 120], [100, 255, 255]],
        ],
        "inventory_roi": {
            "right": 0,
            "bottom": 0,
            "width": 300,
            "height": 300,
        },
    },
    "fletching": {
        "move_duration_seconds": [0.25, 0.6],
        "step_delay_seconds": [1.0, 2.0],
        "cycle_delay_seconds": [9.0, 15.0],
        "first_click": {
            "x": None,
            "y": None,
            "x_ratio": None,
            "y_ratio": None,
            "jitter_x": 6,
            "jitter_y": 6,
        },
        "second_click": {
            "x": None,
            "y": None,
            "x_ratio": None,
            "y_ratio": None,
            "jitter_x": 6,
            "jitter_y": 6,
        },
    },
    "magic": {
        "pre_space_delay_seconds": [1.0, 4.0],
        "cycle_delay_seconds": [10.0, 15.0],
        "idle_mouse_move_pixels": 6,
        "idle_mouse_pause_seconds": [0.6, 2.0],
        "idle_mouse_move_duration_seconds": [0.05, 0.25],
        "click": {
            "x_ratio": None,
            "y_ratio": None,
            "jitter_x": 4,
            "jitter_y": 4,
        },
    },
    "hp": {
        "auto_locate": True,
        "heart_color_ranges": [
            [[0, 100, 80], [10, 255, 255]],
            [[170, 100, 80], [180, 255, 255]],
        ],
        "heart_search_left_fraction": 0.55,
        "heart_search_height_fraction": 0.24,
        "heart_min_area": 80,
        "heart_max_area": 1200,
        "heart_digit_left_widths": 2.0,
        "heart_digit_widths": 2.6,
        "heart_digit_height": 1.05,
        "max_value_hint": 45,
        "overlay_roi": {
            "right": 425,
            "top": 70,
            "width": 70,
            "height": 35,
        },
        "text_inset": {
            "left": 8,
            "top": 8,
            "right": 34,
            "bottom": 4,
        },
        "digit_color_ranges": [
            [[18, 70, 120], [42, 255, 255]],
            [[42, 50, 120], [95, 255, 255]],
        ],
        "template_dir": "data/hp_templates",
        "template_size": {
            "width": 24,
            "height": 36,
        },
        "digit_match_threshold": 0.78,
        "max_digits": 3,
        "min_digit_width": 4,
        "min_digit_height_ratio": 0.15,
        "max_segment_gap": 4,
    },
}


def deep_merge_dicts(base, override):
    """Merge override values into a nested dictionary."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: Path):
    """Load the JSON config file and merge it with tracked defaults."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a JSON object at the root.")

    return deep_merge_dicts(copy.deepcopy(DEFAULT_CONFIG), loaded)


def resolve_relative_path(base_dir: Path, raw_path: str):
    """Resolve a potentially relative path against the config directory."""
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def get_debug_dir(config, config_dir: Path):
    """Return the debug output directory configured for this run."""
    return resolve_relative_path(config_dir, config["debug"]["dir"])


def get_template_dir(config, config_dir: Path):
    """Return the configured HP template directory."""
    return resolve_relative_path(config_dir, config["hp"]["template_dir"])


def ensure_directory(path: Path):
    """Create a directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)
