import cv2
import numpy as np
import os
import random
import re
import time

import mss
import pyautogui
import pytesseract

from Quartz import (
    CGDisplayBounds,
    CGDisplayPixelsWide,
    CGMainDisplayID,
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
)

# Minimum contour area for a color box to be considered a valid target
MIN_AREA = 200

# ------------------------
# CONFIGURATION
# ------------------------

# Attack (target) color: red
ATTACK_COLOR_RANGES = [
    ((0, 120, 120), (10, 255, 255)),
    ((170, 120, 120), (180, 255, 255)),
]

# Heal color: cyan / light blue (configure in RuneLite)
HEAL_COLOR_RANGES = [
    ((85, 120, 120), (100, 255, 255)),
]

# HP overlay ROI (top/left)
ROI_HP_OVERLAY = {
    "left": 0,
    "top": 35,
    "width": 140,
    "height": 60,
}

# Heal inventory ROI (bottom/right) - adjust after first run
ROI_HEAL_INVENTORY = {
    "left": 520,
    "top": 270,
    "width": 200,
    "height": 260,
}

# State machine states
STATE_ACQUIRE = "ACQUIRE"      # searching for a target and (if valid) clicking once
STATE_ATTACK = "ATTACK"        # currently attacking: never click

# Robustness thresholds
HP_LOW_PCT = 0.25               # heal when HP <= 25%
HP_LOW_STREAK = 2               # consecutive low HP reads required to heal
HP_LAST_VALID_TTL = 1.5         # seconds to reuse last valid HP after OCR failure
TARGET_MISSING_STREAK = 2       # consecutive misses before re-acquiring target

ATTACK_CLICK_COOLDOWN = (0.15, 0.35)  # cooldown to avoid double-clicking by accident
HEAL_CLICK_COOLDOWN = (1.0, 1.5)      # cooldown to avoid spam healing

DEBUG_SAVE_FRAMES = False
DEBUG_DIR = "debug_frames"

# Safer PyAutoGUI defaults
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


# ------------------------
# MASK / BOX UTILITIES
# ------------------------

def cleanup_mask(mask: np.ndarray) -> np.ndarray:
    """Apply basic denoising and morphological operations to a binary mask."""
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.medianBlur(mask, 5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def hsv_mask(frame_bgr: np.ndarray, ranges):
    """Return a cleaned mask for the given HSV ranges over the BGR frame."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = None
    for lo, hi in ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else (mask | m)
    return cleanup_mask(mask)


def find_boxes_from_mask(mask: np.ndarray):
    """Find bounding boxes for regions in the given binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []

    for cnt in contours:
        area = cv2.contourArea(cnt)

        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w // 2
        cy = y + h // 2
        boxes.append((x, y, w, h, area, cx, cy))

    boxes.sort(key=lambda b: b[4], reverse=True)
    return boxes


def choose_largest_box(boxes):
    """Return the largest box by area, or None."""
    if not boxes:
        return None
    return boxes[0]


def point_in_box(px, py, box):
    """Return True if the point (px, py) lies inside the given box."""
    x, y, w, h, *_ = box
    return (x <= px <= x + w) and (y <= py <= y + h)


def find_box_containing_point(boxes, px, py):
    """Return the first box in which the point (px, py) lies, or None."""
    for b in boxes:
        if point_in_box(px, py, b):
            return b
    return None


# ------------------------
# WINDOW / ROI
# ------------------------

def get_display_scale():
    """Return the macOS display scale (pixels per point) for the main display."""
    display_id = CGMainDisplayID()
    bounds = CGDisplayBounds(display_id)
    points_width = bounds.size.width
    pixels_width = CGDisplayPixelsWide(display_id)
    if not points_width:
        return 1.0
    return float(pixels_width) / float(points_width)


def find_window(owner_contains: str, title_contains: str = ""):
    """Find the largest on-screen window whose owner/title contains the given strings."""
    windows = CGWindowListCopyWindowInfo(
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )

    owner_contains = owner_contains.lower()
    title_contains = title_contains.lower()

    best = None
    best_area = 0

    for w in windows:
        owner = (w.get("kCGWindowOwnerName") or "").lower()
        title = (w.get("kCGWindowName") or "").lower()
        bounds = w.get("kCGWindowBounds")
        if not bounds:
            continue

        if owner_contains in owner and (not title_contains or title_contains in title):
            width = bounds.get("Width", 0)
            height = bounds.get("Height", 0)

            # Ignore very small windows (tooltips, etc.)
            if width < 300 or height < 300:
                continue

            area = width * height
            if area > best_area:
                best_area = area
                best = (bounds, w)

    return best if best else (None, None)


def scale_bounds(bounds, scale=1.0):
    """Scale window bounds from points to pixels."""
    return {
        "X": int(bounds["X"] * scale),
        "Y": int(bounds["Y"] * scale),
        "Width": int(bounds["Width"] * scale),
        "Height": int(bounds["Height"] * scale),
    }


def bounds_to_region(bounds):
    """Convert window bounds to an mss region dict."""
    return {
        "left": int(bounds["X"]),
        "top": int(bounds["Y"]),
        "width": int(bounds["Width"]),
        "height": int(bounds["Height"]),
    }


def roi_from_window(bounds, roi_rel, scale=1.0):
    """
    Return an absolute ROI dict from window bounds and a relative ROI config.

    Parameters
    ----------
    bounds : dict
        A dictionary describing the window position and size, typically with
        keys "X", "Y", "Width" and "Height" in screen coordinates.
    roi_rel : dict
        A dictionary describing the ROI relative to the window, with keys
        "left", "top", "width" and "height" expressed in the same coordinate
        system as `bounds`.
    scale : float, optional
        A global scaling factor applied to both the window bounds and the
        relative ROI. This is useful when the coordinates returned by the
        window system are in a different scale than the capture or processing
        coordinate space (for example on HiDPI / retina displays or when
        working with downscaled screenshots). The default of 1.0 means
        "no scaling", which is appropriate when all coordinates are already
        in the same pixel space.
    """
    wx = bounds["X"] * scale
    wy = bounds["Y"] * scale
    ww = bounds["Width"] * scale
    wh = bounds["Height"] * scale

    w = roi_rel["width"] * scale
    h = roi_rel["height"] * scale

    x = wx + roi_rel["left"] * scale
    y = wy + roi_rel["top"] * scale

    # clamp
    x = max(wx, min(x, wx + ww - w))
    y = max(wy, min(y, wy + wh - h))

    return {
        "left": int(x),
        "top": int(y),
        "width": int(w),
        "height": int(h),
    }


# ------------------------
# HP OCR
# ------------------------

# Vertical position where HP text starts (55% down from the top of the image).
HP_BAND_VERTICAL_OFFSET = 0.55


def crop_hp_band(img_bgr):
    """Crop the lower band of the image where the HP text is expected to be."""
    h, w = img_bgr.shape[:2]
    return img_bgr[int(h * HP_BAND_VERTICAL_OFFSET):, :]


def parse_hp(txt, default_max=25):
    """Parse an HP string of the form 'cur/max' or fallbacks, returning (cur, max) or None."""
    txt = txt.strip()

    m = re.search(r"(\d{1,3})/(\d{1,3})", txt)
    if m:
        return int(m.group(1)), int(m.group(2))

    if re.fullmatch(r"\d{1,3}", txt):
        val = int(txt)
        if val == default_max:
            return default_max, default_max
        if val < default_max:
            return None

    digits = re.sub(r"\D", "", txt)
    if len(digits) == 4 and digits.endswith(f"{default_max:02d}"):
        return int(digits[:2]), default_max
    if len(digits) == 3 and digits.endswith(str(default_max)):
        return int(digits[:-len(str(default_max))]), default_max

    return None


def extract_white_text(img_bgr, thr=175):
    """Extract a binary mask of bright text-like regions from the input BGR image."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=6.0, fy=6.0, interpolation=cv2.INTER_CUBIC)

    _, mask = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)

    mask = cv2.medianBlur(mask, 3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2,2), np.uint8), iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), iterations=1)

    return mask


def ocr_hp_from_mask(mask):
    """Run Tesseract OCR on the mask and return a cleaned HP text candidate."""
    cfg = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/"
    data = pytesseract.image_to_data(
        mask, lang="eng", config=cfg, output_type=pytesseract.Output.DICT
    )

    tokens = []
    for t in data["text"]:
        t = re.sub(r"[^0-9/]", "", t)
        if t:
            tokens.append(t)

    txt = "".join(tokens)
    txt = re.sub(r"[^0-9/]", "", txt)
    return txt


def read_hp(sct, bounds, scale=1.0, default_max=25):
    """Capture the HP region from the given window bounds and return (cur_hp, max_hp, raw_text)."""
    ROI_HP = roi_from_window(bounds, ROI_HP_OVERLAY, scale=scale)
    shot_hp = sct.grab(ROI_HP)
    img_hp = np.array(shot_hp)[:, :, :3]
    hp_band = crop_hp_band(img_hp)

    best_hp = None  # tuple (cur, max)
    best_txt = ""
    for thr in (185, 175, 165):
        mask = extract_white_text(hp_band, thr=thr)
        hp_txt = ocr_hp_from_mask(mask)
        hp = parse_hp(hp_txt, default_max=default_max)
        if hp:
            best_hp = hp
            best_txt = hp_txt
            break
        best_txt = hp_txt

    if best_hp:
        return best_hp[0], best_hp[1], best_txt
    return None, None, best_txt


# ------------------------
# COLOR SCAN
# ------------------------

def scan_color_boxes_in_region(sct, region, ranges, min_area=MIN_AREA):
    """Capture a region and return all detected color boxes for given HSV ranges."""
    shot = sct.grab(region)
    img = np.array(shot)[:, :, :3]
    mask = hsv_mask(img, ranges)
    boxes = find_boxes_from_mask(mask)
    if min_area is not None:
        boxes = [b for b in boxes if b[4] >= min_area]
    return boxes


# ------------------------
# MAIN LOOP
# ------------------------

def main():
    """Main bot loop: acquire red targets, attack once, and heal by color when HP is low."""
    state = STATE_ACQUIRE

    hp_low_streak = 0
    target_missing_streak = 0

    next_attack_click_time = 0.0
    next_heal_click_time = 0.0

    last_valid_hp = None
    last_valid_max = None
    last_valid_ts = 0.0

    # guard: current target coordinates (in coords RELATIVE to the window's monitor)
    current_target_rel = None  # (cx, cy)

    with mss.mss() as sct:
        scale = get_display_scale()
        while True:
            try:
                bounds, _ = find_window("runelite")
                if not bounds:
                    print("RuneLite window not found. Retrying in 5s.")
                    time.sleep(5)
                    continue

                bounds_px = scale_bounds(bounds, scale)
                window_region = bounds_to_region(bounds_px)

                now = time.time()

                # 1) Read HP first (decides heal attempts)
                hp_cur, hp_max, hp_txt = read_hp(sct, bounds, scale=scale, default_max=25)
                hp_missing = (hp_cur is None or hp_max is None)
                if DEBUG_SAVE_FRAMES and hp_missing:
                    os.makedirs(DEBUG_DIR, exist_ok=True)
                    hp_roi = roi_from_window(bounds, ROI_HP_OVERLAY, scale=scale)
                    cv2.imwrite(
                        os.path.join(DEBUG_DIR, f"hp_missing_{int(now)}.png"),
                        np.array(sct.grab(hp_roi))[:, :, :3],
                    )
                if hp_cur is not None and hp_max is not None:
                    last_valid_hp = hp_cur
                    last_valid_max = hp_max
                    last_valid_ts = now
                else:
                    if last_valid_hp is not None and now - last_valid_ts <= HP_LAST_VALID_TTL:
                        hp_cur = last_valid_hp
                        hp_max = last_valid_max
                    else:
                        hp_cur = None
                        hp_max = None

                if hp_cur is not None and hp_max:
                    if hp_cur / hp_max <= HP_LOW_PCT:
                        hp_low_streak += 1
                    else:
                        hp_low_streak = 0
                else:
                    hp_low_streak = 0

                hp_is_low = (hp_low_streak >= HP_LOW_STREAK)

                print(
                    f"[{state}] HP: {hp_cur}/{hp_max} (txt='{hp_txt}') "
                    f"low_streak={hp_low_streak}"
                )

                # 2) Heal attempt (higher priority than attack clicks)
                if hp_is_low and now >= next_heal_click_time:
                    heal_roi = roi_from_window(bounds, ROI_HEAL_INVENTORY, scale=scale)
                    heal_boxes = scan_color_boxes_in_region(
                        sct, heal_roi, HEAL_COLOR_RANGES, min_area=MIN_AREA
                    )
                    heal_box = choose_largest_box(heal_boxes)
                    if heal_box:
                        hx, hy, hw, hh, _, hcx, hcy = heal_box
                        screen_x = heal_roi["left"] + hcx
                        screen_y = heal_roi["top"] + hcy

                        # guard: ensure click is inside window bounds
                        if (
                            bounds_px["X"] <= screen_x <= bounds_px["X"] + bounds_px["Width"]
                            and bounds_px["Y"] <= screen_y <= bounds_px["Y"] + bounds_px["Height"]
                        ):
                            pyautogui.click(screen_x, screen_y)
                            next_heal_click_time = now + random.uniform(*HEAL_CLICK_COOLDOWN)
                            print(f"Heal click at ({screen_x},{screen_y}).")
                            if DEBUG_SAVE_FRAMES:
                                os.makedirs(DEBUG_DIR, exist_ok=True)
                                cv2.imwrite(
                                    os.path.join(DEBUG_DIR, f"heal_{int(now)}.png"),
                                    np.array(sct.grab(heal_roi))[:, :, :3],
                                )

                # 3) Scan attack color boxes across the entire window
                attack_boxes = scan_color_boxes_in_region(
                    sct, window_region, ATTACK_COLOR_RANGES, min_area=MIN_AREA
                )

                # 4) STATE_ATTACK: never click while in ATTACK state
                if state == STATE_ATTACK:
                    if current_target_rel is not None:
                        cx, cy = current_target_rel
                        if find_box_containing_point(attack_boxes, cx, cy):
                            target_missing_streak = 0
                        else:
                            target_missing_streak += 1

                    if target_missing_streak >= TARGET_MISSING_STREAK:
                        print("Target missing. Re-acquiring.")
                        state = STATE_ACQUIRE
                        current_target_rel = None
                        target_missing_streak = 0
                        time.sleep(0.05)
                        continue

                    # Still attacking -> do not click
                    time.sleep(0.08)
                    continue

                # 5) STATE_ACQUIRE: choose a target and click once (only inside a red box)
                if state == STATE_ACQUIRE:
                    if not attack_boxes:
                        print("No attack boxes found. Re-scanning in 0.3s.")
                        time.sleep(0.3)
                        continue

                    target_box = choose_largest_box(attack_boxes)
                    if not target_box:
                        time.sleep(0.1)
                        continue

                    x, y, w, h, _, cx, cy = target_box

                    # Strong validation: the click point MUST be inside some attack box
                    if not find_box_containing_point(attack_boxes, cx, cy):
                        print("Validation failed: point is not in an attack box. Re-scanning.")
                        time.sleep(0.05)
                        continue

                    screen_x = bounds_px["X"] + cx
                    screen_y = bounds_px["Y"] + cy

                    # Extra guard: never click outside the game window
                    if not (
                        bounds_px["X"] <= screen_x <= bounds_px["X"] + bounds_px["Width"]
                        and bounds_px["Y"] <= screen_y <= bounds_px["Y"] + bounds_px["Height"]
                    ):
                        print("Protection: click coordinate outside window. Re-scanning.")
                        time.sleep(0.05)
                        continue

                    # Cooldown to avoid accidental spam clicks
                    if now < next_attack_click_time:
                        time.sleep(0.02)
                        continue

                    # Single click to start the attack
                    pyautogui.click(screen_x, screen_y)
                    next_attack_click_time = now + random.uniform(*ATTACK_CLICK_COOLDOWN)

                    current_target_rel = (cx, cy)
                    state = STATE_ATTACK

                    print(
                        f"Clicked attack box at ({screen_x},{screen_y}). "
                        "Now in ATTACK state (no further clicks)."
                    )
                    time.sleep(0.12)
                    continue
            except pyautogui.FailSafeException:
                print("PyAutoGUI fail-safe triggered. Exiting.")
                break
            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down gracefully.")
                break
            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                time.sleep(0.5)
                continue


if __name__ == "__main__":
    main()
