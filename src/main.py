import cv2
import numpy as np
import re
import mss
import pytesseract
import pyautogui
import time
import random

from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
)

# Minimum contour area for a pink box to be considered a valid target
MIN_AREA = 200

# ------------------------
# CONFIGURATION
# ------------------------

PINK_RANGES = [
    ((145, 120, 120), (170, 255, 255)),
]

ROI_RELATIVE = {
    "left": 0,
    "top": 35,
    "width": 140,
    "height": 60,
}

# State machine states
STATE_ACQUIRE = "ACQUIRE"      # searching for a target and (if valid) clicking once
STATE_ATTACK = "ATTACK"        # currently attacking: never click
STATE_POST_DEAD = "POST_DEAD"  # HP confirmed as 0: wait a bit, then go back to ACQUIRE

# Robustness thresholds
HP_ZERO_STREAK_TO_CONFIRM = 3   # consecutive HP reads at 0 to confirm target is dead
HP_ALIVE_STREAK_TO_CONFIRM = 1  # consecutive HP reads > 0 to confirm target is alive
OCR_NONE_TOLERANCE = 8          # consecutive None HP reads before re-acquiring target

POST_DEAD_WAIT = (1.2, 2.5)     # delay after confirmed death before searching another target
CLICK_COOLDOWN = (0.15, 0.35)   # cooldown to avoid double-clicking by accident

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


def find_pink_boxes_from_mask(mask: np.ndarray):
    """Find bounding boxes for pink regions in the given binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w // 2
        cy = y + h // 2
        boxes.append((x, y, w, h, area, cx, cy))

    boxes.sort(key=lambda b: b[4], reverse=True)
    return boxes


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


def roi_from_window(bounds, roi_rel, scale=1.0):
    """Return an absolute ROI dict from window bounds and a relative ROI config."""
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
            return 0, default_max
        if val < default_max:
            return None

    digits = re.sub(r"\D", "", txt)
    if len(digits) == 4 and digits.endswith(f"{default_max:02d}"):
        return int(digits[:2]), default_max
    if len(digits) == 3 and digits.endswith(str(default_max)):
        return int(digits[:-2]), default_max

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


def read_hp(sct, bounds, default_max=25):
    """Capture the HP region from the given window bounds and return (hp_value, raw_text)."""
    ROI_HP = roi_from_window(bounds, ROI_RELATIVE)
    shot_hp = sct.grab(ROI_HP)
    img_hp = np.array(shot_hp)[:, :, :3]
    hp_band = crop_hp_band(img_hp)

    best_hp = None
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

    current_hp = best_hp[0] if best_hp else None
    return current_hp, best_txt


# ------------------------
# TARGET SCAN
# ------------------------

def scan_pink_boxes(sct, bounds):
    """Capture the game window and return all detected pink target boxes."""
    monitor = {"top": bounds["Y"], "left": bounds["X"], "width": bounds["Width"], "height": bounds["Height"]}
    full_shot = sct.grab(monitor)
    full_img = np.array(full_shot)[:, :, :3]

    pink_mask = hsv_mask(full_img, PINK_RANGES)
    pink_boxes = find_pink_boxes_from_mask(pink_mask)
    return pink_boxes


def choose_target(pink_boxes, target_index):
    """Pick a target box from the list using a circular index strategy."""
    if not pink_boxes:
        return None, 0
    if target_index >= len(pink_boxes):
        target_index = 0
    return pink_boxes[target_index], target_index


# ------------------------
# MAIN LOOP
# ------------------------

def main():
    """Main bot loop: acquire pink targets, attack once, then monitor HP until death."""
    target_index = 0
    state = STATE_ACQUIRE

    zero_streak = 0
    alive_streak = 0
    none_streak = 0

    next_click_time = 0.0
    post_dead_until = 0.0

    # guard: coordenadas do alvo atual (em coords RELATIVAS ao monitor da janela)
    current_target_rel = None  # (cx, cy)

    with mss.mss() as sct:
        while True:
            bounds, win = find_window("runelite")
            if not bounds:
                print("RuneLite window not found. Retrying in 5s.")
                time.sleep(5)
                continue

            # 1) Read HP first (decides state transitions without clicking)
            hp, hp_txt = read_hp(sct, bounds, default_max=25)

            # Atualiza streaks de forma robusta:
            # - hp == 0   -> fortalece "morreu"
            # - hp > 0    -> fortalece "vivo"
            # - hp is None -> perdemos a barra; zera estados de vivo/morto
            if hp is None:
                none_streak += 1
                zero_streak = 0
                alive_streak = 0
            else:
                none_streak = 0
                if hp == 0:
                    zero_streak += 1
                    alive_streak = 0
                else:
                    alive_streak += 1
                    zero_streak = 0

            hp_is_zero = (zero_streak >= HP_ZERO_STREAK_TO_CONFIRM)
            hp_is_alive = (alive_streak >= HP_ALIVE_STREAK_TO_CONFIRM)

            now = time.time()
            print(f"[{state}] HP: {hp} (txt='{hp_txt}') zero_streak={zero_streak} alive_streak={alive_streak} none_streak={none_streak}")

            # 2) POST_DEAD state: wait and do nothing
            if state == STATE_POST_DEAD:
                if now < post_dead_until:
                    time.sleep(0.05)
                    continue
                # Waiting period is over -> go back to ACQUIRE and search for a new target
                state = STATE_ACQUIRE
                current_target_rel = None
                # zera contadores para evitar “grudar” em hp=0 antigo
                zero_streak = 0
                alive_streak = 0
                none_streak = 0
                continue

            # 3) Scan pink boxes only for states that need them
            pink_boxes = None
            if state in (STATE_ATTACK, STATE_ACQUIRE):
                pink_boxes = scan_pink_boxes(sct, bounds)

            # 4) STATE_ATTACK: never click while in ATTACK state
            if state == STATE_ATTACK:
                # If HP==0 is confirmed, go into POST_DEAD waiting state
                if hp_is_zero:
                    post_dead_until = now + random.uniform(*POST_DEAD_WAIT)
                    state = STATE_POST_DEAD
                    print(f"HP=0 confirmed. Waiting {post_dead_until-now:.2f}s before searching next target.")
                    continue

                # If OCR is uncertain for too long, or target left the pink box, re-acquire without clicking
                if none_streak >= OCR_NONE_TOLERANCE:
                    print("HP OCR uncertain for too long. Re-acquiring target without clicking.")
                    state = STATE_ACQUIRE
                    current_target_rel = None
                    time.sleep(0.1)
                    continue

                if current_target_rel is not None:
                    cx, cy = current_target_rel
                    if not find_box_containing_point(pink_boxes, cx, cy):
                        print("Current target no longer in pink box. Re-acquiring without clicking.")
                        state = STATE_ACQUIRE
                        current_target_rel = None
                        time.sleep(0.05)
                        continue

                # Still attacking -> do not click
                time.sleep(0.08)
                continue

            # 5) STATE_ACQUIRE: choose a target and click once (only inside a pink box)
            if state == STATE_ACQUIRE:
                if not pink_boxes:
                    print("No pink boxes found. Re-scanning in 0.3s.")
                    time.sleep(0.3)
                    continue

                # If HP still looks alive (HP>0 confirmed), something is already engaged.
                # Avoid mis-clicking again while a target is alive.
                if hp_is_alive:
                    print("HP still alive (engaged). Switching to ATTACK without clicking.")
                    state = STATE_ATTACK
                    time.sleep(0.05)
                    continue

                target_box, target_index = choose_target(pink_boxes, target_index)
                if not target_box:
                    time.sleep(0.1)
                    continue

                x, y, w, h, _, cx, cy = target_box

                # Strong validation: the click point MUST be inside some pink box from the current scan
                if not find_box_containing_point(pink_boxes, cx, cy):
                    print("Validation failed: point is not in a pink box. Re-scanning.")
                    time.sleep(0.05)
                    continue

                screen_x = bounds["X"] + cx
                screen_y = bounds["Y"] + cy

                # Extra guard: never click outside the game window
                if not (bounds["X"] <= screen_x <= bounds["X"] + bounds["Width"] and
                        bounds["Y"] <= screen_y <= bounds["Y"] + bounds["Height"]):
                    print("Protection: click coordinate outside window. Re-scanning.")
                    time.sleep(0.05)
                    continue

                # Cooldown to avoid accidental spam clicks
                if now < next_click_time:
                    time.sleep(0.02)
                    continue

                # Single click to start the attack
                pyautogui.click(screen_x, screen_y)
                next_click_time = now + random.uniform(*CLICK_COOLDOWN)

                current_target_rel = (cx, cy)
                state = STATE_ATTACK

                print(f"Clicked pink box at ({screen_x},{screen_y}). Now in ATTACK state (no further clicks).")
                time.sleep(0.12)
                continue


if __name__ == "__main__":
    main()
