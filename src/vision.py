import cv2
import numpy as np
from .config import MIN_AREA


def cleanup_mask(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.medianBlur(mask, 5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def hsv_mask(frame_bgr: np.ndarray, ranges):
    """
    ranges: lista de tuplas [(lo, hi), (lo2, hi2), ...]
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = None
    for lo, hi in ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else (mask | m)
    return cleanup_mask(mask)


def find_red_boxes_from_mask(mask: np.ndarray):
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


def draw_debug(frame_bgr: np.ndarray, boxes, max_boxes=20):
    dbg = frame_bgr.copy()
    for (x, y, w, h, area, cx, cy) in boxes[:max_boxes]:
        cv2.rectangle(dbg, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(dbg, (cx, cy), 3, (0, 255, 255), -1)
        cv2.putText(
            dbg, f"{int(area)}", (x, max(0, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )
    return dbg
