import time
from pathlib import Path

import cv2
import numpy as np

from src.core.config import get_template_dir
from src.core.debug import save_hp_debug_bundle
from src.core.vision import crop_nonzero_mask, hsv_text_mask, raw_hsv_mask
from src.core.window import capture_window_image, clamp_region, crop_window_roi, find_window


def find_hp_heart_box(window_image, config):
    """Find the red heart orb in the top-right RuneLite UI."""
    hp_config = config["hp"]
    search_left = int(window_image.shape[1] * hp_config.get("heart_search_left_fraction", 0.55))
    search_height = int(window_image.shape[0] * hp_config.get("heart_search_height_fraction", 0.24))
    search_image = window_image[:search_height, search_left:]
    mask = raw_hsv_mask(
        search_image,
        hp_config.get(
            "heart_color_ranges",
            [
                [[0, 100, 80], [10, 255, 255]],
                [[170, 100, 80], [180, 255, 255]],
            ],
        ),
    )

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        if area < hp_config.get("heart_min_area", 80) or area > hp_config.get("heart_max_area", 1200):
            continue
        aspect = width / max(height, 1)
        if not (0.6 <= aspect <= 1.4):
            continue
        score = (x + width / 2.0) - (y * 0.5)
        candidates.append((score, x, y, width, height))

    if not candidates:
        return None

    _, x, y, width, height = max(candidates, key=lambda item: item[0])
    return {
        "left": int(search_left + x),
        "top": int(y),
        "width": int(width),
        "height": int(height),
    }


def extract_hp_source_region(window_image, config):
    """Return the best current HP source crop from the window image."""
    hp_config = config["hp"]
    if hp_config.get("auto_locate", True):
        heart_box = find_hp_heart_box(window_image, config)
        if heart_box is not None:
            dynamic_region = clamp_region(
                {
                    "left": int(heart_box["left"] - heart_box["width"] * hp_config.get("heart_digit_left_widths", 2.0)),
                    "top": int(heart_box["top"]),
                    "width": int(heart_box["width"] * hp_config.get("heart_digit_widths", 2.6)),
                    "height": int(heart_box["height"] * hp_config.get("heart_digit_height", 1.05)),
                },
                window_image.shape,
            )
            crop = window_image[
                dynamic_region["top"]:dynamic_region["top"] + dynamic_region["height"],
                dynamic_region["left"]:dynamic_region["left"] + dynamic_region["width"],
            ]
            return crop, dynamic_region, "heart"

    crop, region = crop_window_roi(window_image, hp_config["overlay_roi"])
    return crop, region, "fallback"


def crop_hp_text_region(img_bgr, text_inset):
    """Crop just the HP digit region, excluding the orb border and heart icon."""
    height, width = img_bgr.shape[:2]
    left = min(max(0, text_inset["left"]), max(0, width - 1))
    top = min(max(0, text_inset["top"]), max(0, height - 1))
    right = max(left + 1, width - max(0, text_inset["right"]))
    bottom = max(top + 1, height - max(0, text_inset["bottom"]))
    return img_bgr[top:bottom, left:right]


def prepare_hp_detection_images(hp_roi_image, config, apply_text_inset=True):
    """Build the cropped text image and binary digit mask for HP recognition."""
    text_image = (
        crop_hp_text_region(hp_roi_image, config["hp"]["text_inset"])
        if apply_text_inset
        else hp_roi_image
    )
    scaled_text_image = cv2.resize(
        text_image,
        None,
        fx=6.0,
        fy=6.0,
        interpolation=cv2.INTER_CUBIC,
    )
    digit_mask = hsv_text_mask(scaled_text_image, config["hp"]["digit_color_ranges"])
    return scaled_text_image, digit_mask


def extract_digit_boxes(mask, config):
    """Return left-to-right digit boxes using connected components."""
    binary = ((mask > 0).astype(np.uint8) * 255)
    if not np.any(binary):
        return []

    hp_config = config["hp"]
    min_width = max(hp_config["min_digit_width"], int(mask.shape[1] * 0.02))
    min_height = max(1, int(mask.shape[0] * hp_config["min_digit_height_ratio"]))
    max_height = max(min_height, int(mask.shape[0] * 0.95))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        if width < min_width:
            continue
        if height < min_height or height > max_height:
            continue
        if area < max(10, width * height * 0.15):
            continue
        boxes.append((x, y, width, height))

    boxes.sort(key=lambda box: box[0])
    if len(boxes) > hp_config["max_digits"]:
        return []
    return boxes


def normalize_digit_image(mask, template_size):
    """Normalize a single digit mask onto a fixed canvas for matching."""
    cropped = crop_nonzero_mask(mask)
    if cropped is None:
        return None

    target_width = int(template_size["width"])
    target_height = int(template_size["height"])
    available_width = max(1, target_width - 4)
    available_height = max(1, target_height - 4)

    src_height, src_width = cropped.shape[:2]
    scale = min(available_width / src_width, available_height / src_height)
    resized_width = max(1, int(round(src_width * scale)))
    resized_height = max(1, int(round(src_height * scale)))
    resized = cv2.resize(
        cropped,
        (resized_width, resized_height),
        interpolation=cv2.INTER_NEAREST,
    )
    _, resized = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)

    canvas = np.zeros((target_height, target_width), dtype=np.uint8)
    offset_x = (target_width - resized_width) // 2
    offset_y = (target_height - resized_height) // 2
    canvas[offset_y:offset_y + resized_height, offset_x:offset_x + resized_width] = resized
    return canvas


def template_similarity(sample, template):
    """Return an IOU-style similarity score between two normalized digit masks."""
    sample_binary = sample > 0
    template_binary = template > 0
    union = np.logical_or(sample_binary, template_binary).sum()
    if union == 0:
        return 0.0
    intersection = np.logical_and(sample_binary, template_binary).sum()
    return float(intersection) / float(union)


def load_hp_templates(config, config_dir: Path):
    """Load normalized HP digit templates from disk."""
    template_dir = get_template_dir(config, config_dir)
    templates = {}
    missing = []

    for digit_char in "0123456789":
        template_path = template_dir / f"{digit_char}.png"
        if not template_path.exists():
            missing.append(digit_char)
            continue

        image = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            missing.append(digit_char)
            continue

        _, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        normalized = normalize_digit_image(image, config["hp"]["template_size"])
        if normalized is None:
            missing.append(digit_char)
            continue

        templates[digit_char] = normalized

    return templates, missing


def match_digit_image(digit_image, templates):
    """Return the highest-scoring digit template match."""
    best_digit = None
    best_score = 0.0
    for digit_char, template in templates.items():
        score = template_similarity(digit_image, template)
        if score > best_score:
            best_score = score
            best_digit = digit_char
    return best_digit, best_score


def summarize_current_hp_capture(mask, config, config_dir: Path):
    """Summarize what the current calibration capture seems to contain."""
    boxes = extract_digit_boxes(mask, config)
    box_count = len(boxes)
    templates, missing = load_hp_templates(config, config_dir)

    if templates:
        value, details = recognize_hp_value_from_mask(mask, templates, config)
        if value is not None:
            return f"Current capture looks like '{value}' ({box_count} box{'es' if box_count != 1 else ''})."
        if details["digit_text"]:
            return (
                f"Current capture partially matches '{details['digit_text']}' "
                f"({box_count} box{'es' if box_count != 1 else ''})."
            )

    return f"Current capture has {box_count} box{'es' if box_count != 1 else ''}."


def recognize_hp_value_from_mask(mask, templates, config):
    """Recognize the current HP value from a segmented binary digit mask."""
    boxes = extract_digit_boxes(mask, config)
    if not boxes:
        return None, {
            "digit_text": "",
            "score": 0.0,
            "scores": [],
            "reason": "no_digits",
        }

    digit_chars = []
    scores = []
    threshold = float(config["hp"]["digit_match_threshold"])
    for x, y, width, height in boxes:
        digit_mask = mask[y:y + height, x:x + width]
        normalized = normalize_digit_image(digit_mask, config["hp"]["template_size"])
        if normalized is None:
            return None, {
                "digit_text": "".join(digit_chars),
                "score": min(scores) if scores else 0.0,
                "scores": scores,
                "reason": "empty_digit",
            }

        matched_digit, score = match_digit_image(normalized, templates)
        if matched_digit is None or score < threshold:
            return None, {
                "digit_text": "".join(digit_chars),
                "score": score,
                "scores": scores + [score],
                "reason": "low_confidence",
            }

        digit_chars.append(matched_digit)
        scores.append(score)

    digit_text = "".join(digit_chars)
    return int(digit_text), {
        "digit_text": digit_text,
        "score": min(scores) if scores else 0.0,
        "scores": scores,
        "reason": "ok",
    }


def detect_current_hp_from_roi(hp_roi_image, templates, config, apply_text_inset=True):
    """Recognize current HP from a captured HP ROI image."""
    text_image, digit_mask = prepare_hp_detection_images(
        hp_roi_image,
        config,
        apply_text_inset=apply_text_inset,
    )
    hp_value, details = recognize_hp_value_from_mask(digit_mask, templates, config)
    details["text_image"] = text_image
    details["mask"] = digit_mask
    return hp_value, details


def read_current_hp(window_image, templates, config, config_dir: Path):
    """Capture the HP ROI from the current window image and return the current HP or None."""
    hp_image, hp_region, hp_source = extract_hp_source_region(window_image, config)
    hp_value, details = detect_current_hp_from_roi(
        hp_image,
        templates,
        config,
        apply_text_inset=(hp_source == "fallback"),
    )
    details["region"] = hp_region
    details["source"] = hp_source

    prefix = "hp_success" if hp_value is not None else "hp_unreadable"
    save_hp_debug_bundle(config, config_dir, prefix, hp_image, details["text_image"], details["mask"])
    return hp_value, details


def ensure_hp_templates_ready(config, config_dir: Path):
    """Load HP templates or raise with a clear calibration message."""
    templates, missing = load_hp_templates(config, config_dir)
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            "HP calibration is incomplete. Missing digit templates for "
            f"{missing_str}. Run `uv run calibrate-hp` first."
        )
    return templates


def format_hp_status(current_hp, details):
    """Build a concise HP status string for logs."""
    if current_hp is None:
        return (
            "HP unreadable "
            f"(reason={details['reason']} score={details['score']:.2f} digits='{details['digit_text']}')"
        )
    return f"HP {current_hp} (digits='{details['digit_text']}' score={details['score']:.2f})"


def run_hp_monitor(config, config_dir: Path, templates):
    """Continuously print the calibrated current HP without clicking."""
    while True:
        try:
            bounds, window_info = find_window(
                config["window"]["owner_contains"],
                config["window"]["title_contains"],
            )
            if not bounds:
                print("RuneLite window not found. Retrying in 5s.")
                time.sleep(5)
                continue

            window_image = capture_window_image(window_info)
            current_hp, details = read_current_hp(
                window_image,
                templates,
                config,
                config_dir,
            )
            print(f"[HP_ONLY] {format_hp_status(current_hp, details)}")
            time.sleep(0.25)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down gracefully.")
            break
