import time

import cv2

from src.core.debug import save_debug_image
from src.core.hp import format_hp_status, read_current_hp
from src.core.input import pyautogui
from src.core.timing import choose_interval_seconds
from src.core.vision import (
    box_center,
    choose_largest_box,
    find_box_containing_point,
    find_boxes_from_mask,
    raw_hsv_mask,
    scan_color_boxes_in_frame,
)
from src.core.window import capture_window_image, crop_window_roi, find_window, get_display_scale, scale_bounds


STATE_ACQUIRE = "ACQUIRE"
STATE_ATTACK = "ATTACK"


def filter_attack_boxes(boxes, attack_config):
    """Filter raw red detections down to plausible NPC highlight boxes."""
    filtered = []
    for box in boxes:
        _, _, width, height, area, *_ = box
        if area < float(attack_config["min_area"]):
            continue
        if area > float(attack_config.get("max_area", area)):
            continue
        if width < int(attack_config.get("min_width", 1)):
            continue
        if width > int(attack_config.get("max_width", width)):
            continue
        if height < int(attack_config.get("min_height", 1)):
            continue
        if height > int(attack_config.get("max_height", height)):
            continue

        aspect_ratio = width / max(height, 1)
        if aspect_ratio < float(attack_config.get("min_aspect_ratio", 0.0)):
            continue
        if aspect_ratio > float(attack_config.get("max_aspect_ratio", aspect_ratio)):
            continue
        filtered.append(box)

    filtered.sort(key=lambda box: box[4], reverse=True)
    return filtered


def detect_engaged_target_panel(window_image, config):
    """Detect the top-left target panel that appears only while attacking."""
    panel_config = config["attack"]["engaged_panel"]
    panel_image, panel_region = crop_window_roi(window_image, panel_config["roi"])
    bar_image, bar_region = crop_window_roi(panel_image, panel_config["bar_roi"])

    mask = raw_hsv_mask(bar_image, panel_config["color_ranges"])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    boxes = find_boxes_from_mask(mask)
    valid_boxes = []
    for box in boxes:
        _, _, width, height, area, *_ = box
        if area < float(panel_config["min_area"]):
            continue
        if width < int(panel_config["min_width"]) or width > int(panel_config["max_width"]):
            continue
        if height < int(panel_config["min_height"]) or height > int(panel_config["max_height"]):
            continue
        valid_boxes.append(box)

    valid_boxes.sort(key=lambda box: box[4], reverse=True)
    best_box = valid_boxes[0] if valid_boxes else None
    details = {
        "panel_region": panel_region,
        "bar_region": bar_region,
        "box_count": len(valid_boxes),
        "best_box": best_box,
        "mask": mask,
        "visible": best_box is not None,
    }
    return best_box is not None, details


def should_unlock_heal_wait(waiting_for_hp_refresh, last_food_click_hp, current_hp):
    """Return True when a new valid HP read has arrived after eating."""
    return (
        waiting_for_hp_refresh
        and last_food_click_hp is not None
        and current_hp is not None
        and current_hp != last_food_click_hp
    )


def should_attempt_heal(current_hp, eat_at_hp, waiting_for_hp_refresh, now, next_heal_click_time):
    """Return True when a heal click is allowed for the current loop iteration."""
    if current_hp is None:
        return False
    if waiting_for_hp_refresh:
        return False
    if now < next_heal_click_time:
        return False
    return current_hp <= eat_at_hp


def should_log_status(now, snapshot, last_snapshot, next_log_time):
    """Return True when the status line should be printed again."""
    return snapshot != last_snapshot or now >= next_log_time


def run_combat_bot(config, config_dir, templates):
    """Main combat loop: attack marked targets and eat marked food at a fixed HP threshold."""
    attack_config = config["attack"]
    heal_config = config["heal"]

    state = STATE_ACQUIRE
    target_missing_streak = 0
    next_attack_click_time = 0.0
    next_heal_click_time = 0.0
    attack_hold_until = 0.0

    waiting_for_hp_refresh = False
    last_food_click_hp = None
    last_status_snapshot = None
    next_status_log_time = 0.0
    next_missing_food_log_time = 0.0
    next_no_target_log_time = 0.0

    scale = get_display_scale()
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

            bounds_px = scale_bounds(bounds, scale)
            now = time.time()
            window_image = capture_window_image(window_info)

            current_hp, hp_details = read_current_hp(
                window_image,
                templates,
                config,
                config_dir,
            )
            engaged_panel_visible, _ = detect_engaged_target_panel(window_image, config)

            if should_unlock_heal_wait(waiting_for_hp_refresh, last_food_click_hp, current_hp):
                waiting_for_hp_refresh = False
                last_food_click_hp = None

            status_snapshot = (
                state,
                current_hp,
                hp_details["digit_text"],
                hp_details["reason"],
                waiting_for_hp_refresh,
                engaged_panel_visible,
            )
            if should_log_status(
                now,
                status_snapshot,
                last_status_snapshot,
                next_status_log_time,
            ):
                print(
                    f"[{state}] {format_hp_status(current_hp, hp_details)} "
                    f"heal_lock={waiting_for_hp_refresh} "
                    f"combat_panel={engaged_panel_visible}"
                )
                last_status_snapshot = status_snapshot
                next_status_log_time = now + choose_interval_seconds(
                    attack_config.get("status_log_interval_seconds", 1.0)
                )

            if should_attempt_heal(
                current_hp,
                heal_config["eat_at_hp"],
                waiting_for_hp_refresh,
                now,
                next_heal_click_time,
            ):
                heal_image, heal_region = crop_window_roi(window_image, heal_config["inventory_roi"])
                heal_boxes = scan_color_boxes_in_frame(
                    heal_image,
                    heal_config["color_ranges"],
                    int(heal_config["min_area"]),
                )
                heal_box = choose_largest_box(heal_boxes)
                if heal_box:
                    heal_cx, heal_cy = box_center(heal_box)
                    screen_x = bounds_px["X"] + heal_region["left"] + heal_cx
                    screen_y = bounds_px["Y"] + heal_region["top"] + heal_cy
                    if (
                        bounds_px["X"] <= screen_x <= bounds_px["X"] + bounds_px["Width"]
                        and bounds_px["Y"] <= screen_y <= bounds_px["Y"] + bounds_px["Height"]
                    ):
                        pyautogui.click(screen_x, screen_y)
                        next_heal_click_time = now + choose_interval_seconds(
                            heal_config["click_cooldown_seconds"]
                        )
                        waiting_for_hp_refresh = True
                        last_food_click_hp = current_hp
                        next_missing_food_log_time = 0.0
                        print(
                            f"Heal click at ({screen_x},{screen_y}) because HP={current_hp} "
                            f"<= {heal_config['eat_at_hp']}."
                        )
                        save_debug_image(config, config_dir, "heal_latest.png", heal_image)
                else:
                    next_heal_click_time = max(
                        next_heal_click_time,
                        now + choose_interval_seconds(heal_config.get("no_food_retry_seconds", 1.0)),
                    )
                    if now >= next_missing_food_log_time:
                        print("HP is low, but no highlighted food was found in the heal inventory ROI.")
                        next_missing_food_log_time = now + choose_interval_seconds(
                            heal_config.get("no_food_log_interval_seconds", 2.0)
                        )

            if engaged_panel_visible:
                state = STATE_ATTACK
                target_missing_streak = 0
                time.sleep(0.08)
                continue

            if state == STATE_ATTACK:
                if now >= attack_hold_until:
                    target_missing_streak += 1

                if target_missing_streak >= int(attack_config["engaged_panel"]["missing_streak"]):
                    print("Combat panel missing. Re-acquiring.")
                    state = STATE_ACQUIRE
                    target_missing_streak = 0
                    time.sleep(0.05)
                    continue

                time.sleep(0.08)
                continue

            raw_attack_boxes = scan_color_boxes_in_frame(
                window_image,
                attack_config["color_ranges"],
                int(attack_config["min_area"]),
            )
            attack_boxes = filter_attack_boxes(raw_attack_boxes, attack_config)

            if state == STATE_ACQUIRE:
                if not attack_boxes:
                    if now >= next_no_target_log_time:
                        if raw_attack_boxes:
                            print("Red regions were found, but none matched the NPC target box constraints.")
                        else:
                            print("No attack boxes found. Re-scanning in 0.3s.")
                        next_no_target_log_time = now + choose_interval_seconds(
                            attack_config.get("status_log_interval_seconds", 1.0)
                        )
                    time.sleep(0.3)
                    continue

                target_box = choose_largest_box(attack_boxes)
                if not target_box:
                    time.sleep(0.1)
                    continue

                target_cx, target_cy = box_center(target_box)
                if not find_box_containing_point(attack_boxes, target_cx, target_cy):
                    print("Validation failed: point is not in an attack box. Re-scanning.")
                    time.sleep(0.05)
                    continue

                screen_x = bounds_px["X"] + target_cx
                screen_y = bounds_px["Y"] + target_cy
                if not (
                    bounds_px["X"] <= screen_x <= bounds_px["X"] + bounds_px["Width"]
                    and bounds_px["Y"] <= screen_y <= bounds_px["Y"] + bounds_px["Height"]
                ):
                    print("Protection: click coordinate outside window. Re-scanning.")
                    time.sleep(0.05)
                    continue

                if now < next_attack_click_time:
                    time.sleep(0.02)
                    continue

                pyautogui.click(screen_x, screen_y)
                attack_hold_until = now + choose_interval_seconds(
                    attack_config.get("engaged_hold_seconds", 1.4)
                )
                next_attack_click_time = max(
                    now + choose_interval_seconds(attack_config["click_cooldown_seconds"]),
                    attack_hold_until,
                )
                state = STATE_ATTACK
                target_missing_streak = 0
                next_no_target_log_time = 0.0

                print(
                    f"Clicked attack box at ({screen_x},{screen_y}). "
                    "Waiting for the combat panel to confirm the attack."
                )
                time.sleep(0.12)
        except pyautogui.FailSafeException:
            print("PyAutoGUI fail-safe triggered. Exiting.")
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Shutting down gracefully.")
            break
        except Exception as exc:
            print(f"Unexpected error in combat loop: {exc}")
            time.sleep(0.5)
