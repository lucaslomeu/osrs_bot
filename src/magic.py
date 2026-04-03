import random
import time

from src.core.input import choose_configured_window_click_point, move_mouse_smoothly_to, pyautogui
from src.core.timing import choose_interval_seconds
from src.core.window import find_window, get_display_scale, scale_bounds


def validate_magic_click_config(point_config):
    """Validate the configured magic click point."""
    if not isinstance(point_config, dict):
        raise ValueError("Magic config 'click' must be an object.")

    for axis in ("x_ratio", "y_ratio"):
        value = point_config.get(axis)
        if value is None:
            raise ValueError(
                f"Magic config 'click' is missing '{axis}'. "
                f"Set `magic.click.{axis}` in the config file."
            )
        if not isinstance(value, (int, float)):
            raise ValueError(f"Magic config 'click.{axis}' must be numeric.")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"Magic config 'click.{axis}' must be between 0.0 and 1.0.")

    for axis in ("jitter_x", "jitter_y"):
        value = point_config.get(axis, 0)
        if not isinstance(value, (int, float)):
            raise ValueError(f"Magic config 'click.{axis}' must be numeric.")
        if value < 0:
            raise ValueError(f"Magic config 'click.{axis}' cannot be negative.")


def validate_magic_config(magic_config):
    """Validate the full magic config block."""
    if not isinstance(magic_config, dict):
        raise ValueError("Magic config must be a JSON object.")

    for field_name in (
        "pre_space_delay_seconds",
        "cycle_delay_seconds",
        "idle_mouse_pause_seconds",
        "idle_mouse_move_duration_seconds",
    ):
        if field_name not in magic_config:
            raise ValueError(f"Magic config is missing '{field_name}'.")
        choose_interval_seconds(magic_config[field_name])

    move_pixels = magic_config.get("idle_mouse_move_pixels")
    if not isinstance(move_pixels, (int, float)):
        raise ValueError("Magic config 'idle_mouse_move_pixels' must be numeric.")
    if move_pixels < 0:
        raise ValueError("Magic config 'idle_mouse_move_pixels' cannot be negative.")

    validate_magic_click_config(magic_config.get("click"))


def perform_idle_mouse_drift(magic_config, total_wait_seconds):
    """Move the mouse by a few random pixels while idling between cycles."""
    deadline = time.monotonic() + max(0.0, float(total_wait_seconds))
    max_pixels = max(0, int(magic_config.get("idle_mouse_move_pixels", 0)))

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return

        pause_seconds = min(
            remaining,
            choose_interval_seconds(magic_config["idle_mouse_pause_seconds"]),
        )
        time.sleep(pause_seconds)
        remaining = deadline - time.monotonic()
        if remaining <= 0 or max_pixels == 0:
            continue

        current_x, current_y = pyautogui.position()
        screen_width, screen_height = pyautogui.size()
        offset_x = random.randint(-max_pixels, max_pixels)
        offset_y = random.randint(-max_pixels, max_pixels)
        target_x = max(0, min(current_x + offset_x, screen_width - 1))
        target_y = max(0, min(current_y + offset_y, screen_height - 1))

        if target_x == current_x and target_y == current_y:
            continue

        move_duration = min(
            remaining,
            choose_interval_seconds(magic_config["idle_mouse_move_duration_seconds"]),
        )
        move_mouse_smoothly_to(target_x, target_y, move_duration)


def run_magic_bot(config):
    """Repeat the enchanting click, Space, and idle-drift cycle on the RuneLite window."""
    magic_config = config["magic"]
    validate_magic_config(magic_config)

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
            cycle_number += 1

            click_x, click_y = choose_configured_window_click_point(bounds_px, magic_config["click"])
            move_duration = choose_interval_seconds(magic_config["idle_mouse_move_duration_seconds"])
            move_mouse_smoothly_to(click_x, click_y, move_duration)
            pyautogui.click(click_x, click_y)
            print(f"[magic cycle {cycle_number}] Clicked enchant point at ({click_x},{click_y}).")

            pre_space_delay = choose_interval_seconds(magic_config["pre_space_delay_seconds"])
            time.sleep(pre_space_delay)
            pyautogui.press("space")
            print(f"[magic cycle {cycle_number}] Pressed Space after {pre_space_delay:.2f}s.")

            cycle_delay = choose_interval_seconds(magic_config["cycle_delay_seconds"])
            print(f"[magic cycle {cycle_number}] Idling for {cycle_delay:.2f}s with mouse drift.")
            perform_idle_mouse_drift(magic_config, cycle_delay)
        except pyautogui.FailSafeException:
            print("PyAutoGUI fail-safe triggered. Exiting.")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down gracefully.")
            break
        except Exception as exc:
            print(f"Unexpected error in magic loop: {exc}")
            time.sleep(0.5)
