from pathlib import Path
import json

import cv2

from src.core.config import ensure_directory, get_template_dir
from src.core.debug import save_hp_debug_bundle
from src.core.input import pyautogui
from src.core.hp import (
    extract_digit_boxes,
    extract_hp_source_region,
    load_hp_templates,
    match_digit_image,
    normalize_digit_image,
    prepare_hp_detection_images,
    summarize_current_hp_capture,
)
from src.core.window import capture_window_image, find_window, get_display_scale, scale_bounds


def save_digit_templates_from_label(mask, label: str, config, config_dir: Path):
    """Save missing digit templates using the current mask and user-provided label."""
    if not label.isdigit():
        return False, "Calibration values must contain digits only.", []

    boxes = extract_digit_boxes(mask, config)
    inferred_boxes = None
    if len(boxes) != len(label) and len(label) == 1:
        inferred_boxes = infer_digit_boxes_for_single_label(mask, label, config, config_dir)
        if inferred_boxes is not None:
            boxes = inferred_boxes

    if len(boxes) != len(label):
        capture_summary = summarize_current_hp_capture(mask, config, config_dir)
        return False, (
            f"Expected {len(label)} digit boxes for '{label}', but found {len(boxes)}. "
            f"{capture_summary} Adjust the visible HP value and try again."
        ), []

    template_dir = get_template_dir(config, config_dir)
    ensure_directory(template_dir)

    saved_digits = []
    for digit_char, box in zip(label, boxes):
        x, y, width, height = box
        digit_mask = mask[y:y + height, x:x + width]
        normalized = normalize_digit_image(digit_mask, config["hp"]["template_size"])
        if normalized is None:
            return False, f"Could not normalize the digit '{digit_char}'.", saved_digits

        template_path = template_dir / f"{digit_char}.png"
        if template_path.exists():
            continue

        cv2.imwrite(str(template_path), normalized)
        saved_digits.append(digit_char)

    if saved_digits:
        return True, f"Saved templates for digits: {', '.join(saved_digits)}.", saved_digits
    return True, "No new digits were saved from this sample because those digits are already calibrated.", saved_digits


def suggest_calibration_values(missing_digits):
    """Return a few practical HP values that cover missing digits."""
    digits = list(missing_digits)
    suggestions = []
    while len(digits) >= 2:
        first = digits.pop(0)
        second = digits.pop(0)
        suggestions.append(first + second)
    if digits:
        suggestions.append(digits[0])
    return suggestions


def infer_digit_boxes_for_single_label(mask, label: str, config, config_dir: Path):
    """Infer which box belongs to a single-digit label when other visible digits are already known."""
    boxes = extract_digit_boxes(mask, config)
    if len(boxes) <= 1:
        return boxes

    templates, _ = load_hp_templates(config, config_dir)
    if not templates:
        return None

    threshold = max(0.85, float(config["hp"]["digit_match_threshold"]))
    unmatched_boxes = []
    for box in boxes:
        x, y, width, height = box
        digit_mask = mask[y:y + height, x:x + width]
        normalized = normalize_digit_image(digit_mask, config["hp"]["template_size"])
        if normalized is None:
            unmatched_boxes.append(box)
            continue

        matched_digit, score = match_digit_image(normalized, templates)
        if matched_digit is None or score < threshold:
            unmatched_boxes.append(box)

    if len(unmatched_boxes) == 1:
        return unmatched_boxes
    return None


def suggest_reachable_calibration_values(config, config_dir: Path):
    """Suggest calibration HP values that are reachable and useful with current known digits."""
    templates, missing = load_hp_templates(config, config_dir)
    known_digits = set(templates.keys())
    max_value = int(config["hp"].get("max_value_hint", 45))

    suggestions = []
    for digit_char in missing:
        digit_value = int(digit_char)
        candidate = None
        for prefix_char in ("1", "2", "3", "4"):
            if prefix_char not in known_digits:
                continue
            prefix_value = int(prefix_char) * 10
            full_value = prefix_value + digit_value
            if 0 <= full_value <= max_value:
                candidate = str(full_value)
                break

        if candidate is None and digit_value <= max_value and digit_char in known_digits:
            candidate = digit_char

        if candidate and candidate not in suggestions:
            suggestions.append(candidate)

    if not suggestions:
        suggestions = suggest_calibration_values(missing)
    return suggestions


def calibrate_hp_templates(config, config_dir: Path):
    """Interactively capture HP digit templates for the current RuneLite layout."""
    template_dir = get_template_dir(config, config_dir)
    ensure_directory(template_dir)

    print("HP calibration mode started.")
    print("Keep RuneLite at the exact size and UI scale you will use for the bot.")
    print("Change your visible HP in-game, then type that exact number here to save missing digits.")

    while True:
        _, missing = load_hp_templates(config, config_dir)
        if not missing:
            print(f"Calibration complete. Templates saved in {template_dir}.")
            return

        missing_str = ", ".join(missing)
        suggestions = suggest_reachable_calibration_values(config, config_dir)
        if suggestions:
            print(f"Try HP values containing the missing digits, for example: {', '.join(suggestions)}")
        entered = input(
            f"Missing digits: {missing_str}. Enter the visible HP value or 'q' to quit: "
        ).strip()
        if entered.lower() in {"q", "quit", "exit"}:
            print("Calibration stopped before all digits were captured.")
            return
        if not entered.isdigit():
            print("Please enter digits only.")
            continue

        bounds, window_info = find_window(
            config["window"]["owner_contains"],
            config["window"]["title_contains"],
        )
        if not bounds:
            print("RuneLite window not found. Make sure it is visible on the main screen.")
            continue

        window_image = capture_window_image(window_info)
        hp_image, _, hp_source = extract_hp_source_region(window_image, config)
        text_image, digit_mask = prepare_hp_detection_images(
            hp_image,
            config,
            apply_text_inset=(hp_source == "fallback"),
        )

        save_hp_debug_bundle(config, config_dir, "hp_calibration_latest", hp_image, text_image, digit_mask)
        success, message, _ = save_digit_templates_from_label(
            digit_mask,
            entered,
            config,
            config_dir,
        )
        print(message)
        if not success:
            continue

        _, missing_after = load_hp_templates(config, config_dir)
        if not missing_after:
            print(f"Calibration complete. Templates saved in {template_dir}.")
            return


def get_window_relative_click_details(bounds_px, screen_x, screen_y):
    """Return relative pixel and ratio coordinates for a point inside the window."""
    left = int(bounds_px["X"])
    top = int(bounds_px["Y"])
    width = int(bounds_px["Width"])
    height = int(bounds_px["Height"])
    if not (left <= screen_x < left + width and top <= screen_y < top + height):
        raise ValueError("Current mouse position is outside the RuneLite window.")

    rel_x = int(screen_x - left)
    rel_y = int(screen_y - top)
    width_denominator = max(1, width - 1)
    height_denominator = max(1, height - 1)
    return {
        "x": rel_x,
        "y": rel_y,
        "x_ratio": rel_x / width_denominator,
        "y_ratio": rel_y / height_denominator,
    }


def update_click_target_in_config(config_path: Path, target_label: str, details):
    """Persist calibrated click ratios back into the JSON config file."""
    with config_path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a JSON object at the root.")

    if target_label == "magic.click":
        loaded.setdefault("magic", {})
        loaded["magic"].setdefault("click", {})
        click_config = loaded["magic"]["click"]
    elif target_label == "fletching.first_click":
        loaded.setdefault("fletching", {})
        loaded["fletching"].setdefault("first_click", {})
        click_config = loaded["fletching"]["first_click"]
        click_config["x"] = None
        click_config["y"] = None
    elif target_label == "fletching.second_click":
        loaded.setdefault("fletching", {})
        loaded["fletching"].setdefault("second_click", {})
        click_config = loaded["fletching"]["second_click"]
        click_config["x"] = None
        click_config["y"] = None
    else:
        raise ValueError(f"Unsupported calibration target: {target_label}")

    click_config["x_ratio"] = round(float(details["x_ratio"]), 6)
    click_config["y_ratio"] = round(float(details["y_ratio"]), 6)

    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(loaded, fh, indent=2)
        fh.write("\n")


def calibrate_click_position(config, config_path: Path, target_label: str):
    """Capture the current mouse position relative to the RuneLite window."""
    print(
        f"Click calibration for '{target_label}'. "
        "Move the mouse to the desired point inside RuneLite, then press Enter."
    )
    entered = input("Press Enter to capture the current mouse position, or type 'q' to quit: ").strip()
    if entered.lower() in {"q", "quit", "exit"}:
        print("Click calibration cancelled.")
        return None

    bounds, _ = find_window(
        config["window"]["owner_contains"],
        config["window"]["title_contains"],
    )
    if not bounds:
        raise RuntimeError("RuneLite window not found. Make sure it is visible on the main screen.")

    scale = get_display_scale()
    bounds_px = scale_bounds(bounds, scale)
    mouse_x, mouse_y = pyautogui.position()
    details = get_window_relative_click_details(bounds_px, mouse_x, mouse_y)
    update_click_target_in_config(config_path, target_label, details)

    print(f"Captured mouse at screen=({mouse_x},{mouse_y}) window=({details['x']},{details['y']}).")
    print(f"x_ratio={details['x_ratio']:.6f}")
    print(f"y_ratio={details['y_ratio']:.6f}")
    print(f"Updated config file: {config_path}")
    return details
