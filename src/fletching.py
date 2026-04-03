import time

from src.core.input import (
    choose_configured_window_click_point,
    is_configured_point_inside_window,
    move_mouse_smoothly_to,
    point_config_uses_ratio,
    pyautogui,
)
from src.core.timing import choose_interval_seconds
from src.core.window import find_window, get_display_scale, scale_bounds


def validate_fletching_point_config(point_config, label):
    """Validate a configured fletching click point."""
    if not isinstance(point_config, dict):
        raise ValueError(f"Fletching config '{label}' must be an object.")

    if point_config_uses_ratio(point_config):
        for axis in ("x_ratio", "y_ratio"):
            value = point_config.get(axis)
            if value is None:
                raise ValueError(
                    f"Fletching config '{label}' is missing '{axis}'. "
                    f"Set `fletching.{label}.{axis}` in the config file."
                )
            if not isinstance(value, (int, float)):
                raise ValueError(f"Fletching config '{label}.{axis}' must be numeric.")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"Fletching config '{label}.{axis}' must be between 0.0 and 1.0.")
    else:
        for axis in ("x", "y"):
            value = point_config.get(axis)
            if value is None:
                raise ValueError(
                    f"Fletching config '{label}' is missing '{axis}'. "
                    f"Set `fletching.{label}.{axis}` in the config file."
                )
            if not isinstance(value, (int, float)):
                raise ValueError(f"Fletching config '{label}.{axis}' must be numeric.")

    for axis in ("jitter_x", "jitter_y"):
        value = point_config.get(axis, 0)
        if not isinstance(value, (int, float)):
            raise ValueError(f"Fletching config '{label}.{axis}' must be numeric.")
        if value < 0:
            raise ValueError(f"Fletching config '{label}.{axis}' cannot be negative.")


def validate_fletching_config(fletching_config):
    """Validate the full fletching config block."""
    if not isinstance(fletching_config, dict):
        raise ValueError("Fletching config must be a JSON object.")

    for field_name in ("move_duration_seconds", "step_delay_seconds", "cycle_delay_seconds"):
        if field_name not in fletching_config:
            raise ValueError(f"Fletching config is missing '{field_name}'.")
        choose_interval_seconds(fletching_config[field_name])

    validate_fletching_point_config(fletching_config.get("first_click"), "first_click")
    validate_fletching_point_config(fletching_config.get("second_click"), "second_click")


def run_fletching_bot(config):
    """Repeat the configured fletching sequence on the RuneLite window."""
    fletching_config = config["fletching"]
    validate_fletching_config(fletching_config)

    scale = get_display_scale()
    cycle_number = 0

    while True:
        try:
            bounds, _ = find_window(
                config["window"]["owner_contains"],
                config["window"]["title_contains"],
            )
            if not bounds:
                print("RuneLite window not found. Retrying in 5s.")
                time.sleep(5)
                continue

            bounds_px = scale_bounds(bounds, scale)
            if not is_configured_point_inside_window(bounds_px, fletching_config["first_click"]):
                print("Fletching first_click is outside the current RuneLite window. Retrying in 5s.")
                time.sleep(5)
                continue
            if not is_configured_point_inside_window(bounds_px, fletching_config["second_click"]):
                print("Fletching second_click is outside the current RuneLite window. Retrying in 5s.")
                time.sleep(5)
                continue

            cycle_number += 1

            first_x, first_y = choose_configured_window_click_point(bounds_px, fletching_config["first_click"])
            move_duration = choose_interval_seconds(fletching_config["move_duration_seconds"])
            move_mouse_smoothly_to(first_x, first_y, move_duration)
            pyautogui.click(first_x, first_y)
            print(f"[fletching cycle {cycle_number}] Clicked first point at ({first_x},{first_y}).")

            step_delay = choose_interval_seconds(fletching_config["step_delay_seconds"])
            time.sleep(step_delay)

            second_x, second_y = choose_configured_window_click_point(bounds_px, fletching_config["second_click"])
            move_duration = choose_interval_seconds(fletching_config["move_duration_seconds"])
            move_mouse_smoothly_to(second_x, second_y, move_duration)
            pyautogui.click(second_x, second_y)
            print(f"[fletching cycle {cycle_number}] Clicked second point at ({second_x},{second_y}).")

            step_delay = choose_interval_seconds(fletching_config["step_delay_seconds"])
            time.sleep(step_delay)

            pyautogui.press("space")
            print(f"[fletching cycle {cycle_number}] Pressed Space.")

            cycle_delay = choose_interval_seconds(fletching_config["cycle_delay_seconds"])
            print(f"[fletching cycle {cycle_number}] Waiting {cycle_delay:.2f}s before the next cycle.")
            time.sleep(cycle_delay)
        except pyautogui.FailSafeException:
            print("PyAutoGUI fail-safe triggered. Exiting.")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down gracefully.")
            break
        except Exception as exc:
            print(f"Unexpected error in fletching loop: {exc}")
            time.sleep(0.5)
