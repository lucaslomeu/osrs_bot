import numpy as np
from Quartz import (
    CGDataProviderCopyData,
    CGDisplayBounds,
    CGDisplayPixelsWide,
    CGImageGetBytesPerRow,
    CGImageGetDataProvider,
    CGImageGetHeight,
    CGImageGetWidth,
    CGMainDisplayID,
    CGRectNull,
    CGWindowListCopyWindowInfo,
    CGWindowListCreateImage,
    kCGNullWindowID,
    kCGWindowImageBoundsIgnoreFraming,
    kCGWindowImageNominalResolution,
    kCGWindowListOptionAll,
    kCGWindowListOptionIncludingWindow,
)


def get_display_scale():
    """Return the macOS display scale for the main display."""
    display_id = CGMainDisplayID()
    bounds = CGDisplayBounds(display_id)
    points_width = bounds.size.width
    pixels_width = CGDisplayPixelsWide(display_id)
    if not points_width:
        return 1.0
    return float(pixels_width) / float(points_width)


def find_window(owner_contains: str, title_contains: str = ""):
    """Find the largest matching window whose owner/title contains the given strings."""
    windows = CGWindowListCopyWindowInfo(
        kCGWindowListOptionAll,
        kCGNullWindowID,
    )

    owner_contains = owner_contains.lower()
    title_contains = title_contains.lower()

    best = None
    best_area = 0
    for window in windows:
        owner = (window.get("kCGWindowOwnerName") or "").lower()
        title = (window.get("kCGWindowName") or "").lower()
        bounds = window.get("kCGWindowBounds")
        if not bounds:
            continue

        if owner_contains in owner and (not title_contains or title_contains in title):
            width = bounds.get("Width", 0)
            height = bounds.get("Height", 0)
            if width < 300 or height < 300:
                continue

            area = width * height
            if area > best_area:
                best_area = area
                best = (bounds, window)

    return best if best else (None, None)


def scale_bounds(bounds, scale=1.0):
    """Scale window bounds from points to pixels."""
    return {
        "X": int(bounds["X"] * scale),
        "Y": int(bounds["Y"] * scale),
        "Width": int(bounds["Width"] * scale),
        "Height": int(bounds["Height"] * scale),
    }


def roi_from_window(bounds, roi_rel, scale=1.0):
    """Return an absolute ROI from window bounds and a relative ROI definition."""
    wx = bounds["X"] * scale
    wy = bounds["Y"] * scale
    ww = bounds["Width"] * scale
    wh = bounds["Height"] * scale

    width = roi_rel["width"] * scale
    height = roi_rel["height"] * scale
    if "left" in roi_rel:
        x = wx + roi_rel["left"] * scale
    elif "right" in roi_rel:
        x = wx + ww - width - (roi_rel["right"] * scale)
    else:
        raise KeyError("ROI must define either 'left' or 'right'.")

    if "top" in roi_rel:
        y = wy + roi_rel["top"] * scale
    elif "bottom" in roi_rel:
        y = wy + wh - height - (roi_rel["bottom"] * scale)
    else:
        raise KeyError("ROI must define either 'top' or 'bottom'.")

    x = max(wx, min(x, wx + ww - width))
    y = max(wy, min(y, wy + wh - height))

    return {
        "left": int(x),
        "top": int(y),
        "width": int(width),
        "height": int(height),
    }


def capture_window_image(window_info):
    """Capture the full RuneLite window image even when it is occluded by another app."""
    window_id = window_info["kCGWindowNumber"]
    image_ref = CGWindowListCreateImage(
        CGRectNull,
        kCGWindowListOptionIncludingWindow,
        window_id,
        kCGWindowImageBoundsIgnoreFraming | kCGWindowImageNominalResolution,
    )
    width = CGImageGetWidth(image_ref)
    height = CGImageGetHeight(image_ref)
    bytes_per_row = CGImageGetBytesPerRow(image_ref)
    provider = CGImageGetDataProvider(image_ref)
    data = CGDataProviderCopyData(provider)

    image = np.frombuffer(data, dtype=np.uint8)
    image = image.reshape((height, bytes_per_row // 4, 4))[:, :width, :4]
    return image[:, :, :3]


def crop_window_roi(window_image, roi_rel):
    """Crop a ROI from a full window image using the same relative ROI definition as clicks."""
    local_bounds = {
        "X": 0,
        "Y": 0,
        "Width": window_image.shape[1],
        "Height": window_image.shape[0],
    }
    region = roi_from_window(local_bounds, roi_rel, scale=1.0)
    cropped = window_image[
        region["top"]:region["top"] + region["height"],
        region["left"]:region["left"] + region["width"],
    ]
    return cropped, region


def clamp_region(region, image_shape):
    """Clamp a region dictionary to an image shape."""
    height, width = image_shape[:2]
    left = max(0, min(int(region["left"]), width - 1))
    top = max(0, min(int(region["top"]), height - 1))
    right = max(left + 1, min(int(region["left"] + region["width"]), width))
    bottom = max(top + 1, min(int(region["top"] + region["height"]), height))
    return {
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
    }
