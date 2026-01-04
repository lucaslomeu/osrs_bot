from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)

def find_window(owner_contains: str, title_contains: str = ""):
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
            area = width * height

            # ignore janelinhas minúsculas
            if width < 200 or height < 200:
                continue

            if area > best_area:
                best_area = area
                best = (bounds, w)

    return best if best else (None, None)

if __name__ == "__main__":
    bounds = find_window("runelite")  # ex: "chrome", "visual studio", etc.
    print(bounds)
