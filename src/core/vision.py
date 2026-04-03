import cv2
import numpy as np


def cleanup_mask(mask: np.ndarray):
    """Apply basic denoising and morphology to a binary mask."""
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.medianBlur(mask, 5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def hsv_mask(frame_bgr: np.ndarray, ranges):
    """Return a cleaned mask for the given HSV ranges over a BGR frame."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = None
    for lo, hi in ranges:
        lo_arr = np.array(lo, dtype=np.uint8)
        hi_arr = np.array(hi, dtype=np.uint8)
        partial = cv2.inRange(hsv, lo_arr, hi_arr)
        mask = partial if mask is None else (mask | partial)
    return cleanup_mask(mask)


def hsv_text_mask(frame_bgr: np.ndarray, ranges):
    """Return a digit-oriented mask using lighter morphology than target detection."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        lo_arr = np.array(lo, dtype=np.uint8)
        hi_arr = np.array(hi, dtype=np.uint8)
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo_arr, hi_arr))

    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.medianBlur(mask, 3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    return mask


def raw_hsv_mask(frame_bgr: np.ndarray, ranges):
    """Return a simple HSV mask without the heavier target-cleanup pipeline."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        lo_arr = np.array(lo, dtype=np.uint8)
        hi_arr = np.array(hi, dtype=np.uint8)
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo_arr, hi_arr))
    return mask


def find_boxes_from_mask(mask: np.ndarray):
    """Find bounding boxes for each contour in a binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, width, height = cv2.boundingRect(contour)
        cx = x + width // 2
        cy = y + height // 2
        boxes.append((x, y, width, height, area, cx, cy))
    boxes.sort(key=lambda box: box[4], reverse=True)
    return boxes


def choose_largest_box(boxes):
    """Return the largest box by area, or None."""
    if not boxes:
        return None
    return boxes[0]


def box_center(box):
    """Return the geometric center of a box."""
    x, y, width, height, *_ = box
    return x + width // 2, y + height // 2


def point_in_box(px, py, box):
    """Return True when a point lies inside a box."""
    x, y, width, height, *_ = box
    return (x <= px <= x + width) and (y <= py <= y + height)


def find_box_containing_point(boxes, px, py):
    """Return the first box containing the point, or None."""
    for box in boxes:
        if point_in_box(px, py, box):
            return box
    return None


def find_nearest_box(boxes, px, py, max_distance):
    """Return the nearest box center within max_distance, or None."""
    best_box = None
    best_distance_sq = None
    max_distance_sq = float(max_distance) * float(max_distance)

    for box in boxes:
        cx, cy = box_center(box)
        distance_sq = float((cx - px) ** 2 + (cy - py) ** 2)
        if distance_sq > max_distance_sq:
            continue
        if best_distance_sq is None or distance_sq < best_distance_sq:
            best_distance_sq = distance_sq
            best_box = box

    return best_box


def find_tracked_target_box(boxes, px, py, max_distance):
    """Track the current target by containment first, then a small nearest-box fallback."""
    containing_box = find_box_containing_point(boxes, px, py)
    if containing_box is not None:
        return containing_box
    return find_nearest_box(boxes, px, py, max_distance)


def scan_color_boxes_in_frame(frame_bgr, ranges, min_area):
    """Return detected color boxes for the given HSV ranges within a frame."""
    mask = hsv_mask(frame_bgr, ranges)
    boxes = find_boxes_from_mask(mask)
    return [box for box in boxes if box[4] >= min_area]


def crop_nonzero_mask(mask):
    """Crop a binary mask to its nonzero content."""
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        return None
    x0 = int(xs.min())
    y0 = int(ys.min())
    x1 = int(xs.max()) + 1
    y1 = int(ys.max()) + 1
    return mask[y0:y1, x0:x1]
