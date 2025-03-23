import time
import os
from utils.vision import find_and_click

def mine_ore(ore_type: str):
    image_path = os.path.join("images", f"{ore_type}.png")

    print(f"[INFO] Looking for {ore_type}...")

    success = find_and_click(image_path, confidence=0.8)

    if success:
        print("[INFO] Mining {ore_type}...")
        time.sleep(5)
    else:
        print("[WARN] No {ore_type} found...")
    return success
