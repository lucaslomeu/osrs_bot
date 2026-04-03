from pathlib import Path

import cv2

from src.core.config import ensure_directory, get_debug_dir


def save_debug_image(config, config_dir: Path, filename: str, image):
    """Write a debug image when debugging is enabled."""
    if not config["debug"]["save_frames"]:
        return
    debug_dir = get_debug_dir(config, config_dir)
    ensure_directory(debug_dir)
    cv2.imwrite(str(debug_dir / filename), image)


def save_hp_debug_bundle(config, config_dir: Path, prefix: str, roi_image, text_image, mask):
    """Save the latest HP capture triplet for debugging."""
    save_debug_image(config, config_dir, f"{prefix}_roi.png", roi_image)
    save_debug_image(config, config_dir, f"{prefix}_text_roi.png", text_image)
    save_debug_image(config, config_dir, f"{prefix}_mask.png", mask)
