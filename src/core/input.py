import random

import pyautogui


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


def choose_random_offset(max_offset):
    """Return a signed random offset limited by the configured jitter."""
    max_offset = max(0, int(max_offset))
    if max_offset == 0:
        return 0
    return random.randint(-max_offset, max_offset)


def is_relative_point_inside_window(bounds, point_config):
    """Return True when a relative point is inside the current window bounds."""
    rel_x = int(point_config["x"])
    rel_y = int(point_config["y"])
    return 0 <= rel_x < int(bounds["Width"]) and 0 <= rel_y < int(bounds["Height"])


def choose_window_click_point(bounds, point_config):
    """Return a randomized absolute click point from a window-relative config."""
    rel_x = int(point_config["x"])
    rel_y = int(point_config["y"])
    jitter_x = int(point_config.get("jitter_x", 0))
    jitter_y = int(point_config.get("jitter_y", 0))
    min_x = int(bounds["X"])
    min_y = int(bounds["Y"])
    max_x = min_x + int(bounds["Width"]) - 1
    max_y = min_y + int(bounds["Height"]) - 1
    screen_x = min_x + rel_x + choose_random_offset(jitter_x)
    screen_y = min_y + rel_y + choose_random_offset(jitter_y)
    return (
        max(min_x, min(screen_x, max_x)),
        max(min_y, min(screen_y, max_y)),
    )


def choose_window_ratio_click_point(bounds, point_config):
    """Return a randomized absolute click point from a window-relative ratio config."""
    width = max(1, int(bounds["Width"]))
    height = max(1, int(bounds["Height"]))
    ratio_x = float(point_config["x_ratio"])
    ratio_y = float(point_config["y_ratio"])
    rel_x = int(round((width - 1) * ratio_x))
    rel_y = int(round((height - 1) * ratio_y))
    return choose_window_click_point(
        bounds,
        {
            "x": rel_x,
            "y": rel_y,
            "jitter_x": point_config.get("jitter_x", 0),
            "jitter_y": point_config.get("jitter_y", 0),
        },
    )


def point_config_uses_ratio(point_config):
    """Return True when the click point is configured via window ratios."""
    return point_config.get("x_ratio") is not None or point_config.get("y_ratio") is not None


def is_ratio_point_config_valid(point_config):
    """Return True when ratio values are present and normalized."""
    for axis in ("x_ratio", "y_ratio"):
        value = point_config.get(axis)
        if value is None:
            return False
        if not isinstance(value, (int, float)):
            return False
        if not 0.0 <= float(value) <= 1.0:
            return False
    return True


def is_configured_point_inside_window(bounds, point_config):
    """Return True when the configured click point is valid for the current window."""
    if point_config_uses_ratio(point_config):
        return is_ratio_point_config_valid(point_config)
    return is_relative_point_inside_window(bounds, point_config)


def choose_configured_window_click_point(bounds, point_config):
    """Choose a click point from either pixel-relative or ratio-relative config."""
    if point_config_uses_ratio(point_config):
        return choose_window_ratio_click_point(bounds, point_config)
    return choose_window_click_point(bounds, point_config)


def move_mouse_smoothly_to(x, y, duration_seconds):
    """Move the cursor with a smooth tween to make clicks less robotic."""
    tween = random.choice(
        [
            pyautogui.easeInOutQuad,
            pyautogui.easeInOutSine,
            pyautogui.easeOutQuad,
        ]
    )
    pyautogui.moveTo(int(x), int(y), duration=max(0.0, float(duration_seconds)), tween=tween)
