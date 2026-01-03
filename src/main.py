import time
import numpy as np
import cv2
import mss

from .config import (
    EVERY_SECONDS,
    RED1_HSV_LO, RED1_HSV_HI,
    RED2_HSV_LO, RED2_HSV_HI,
    # opcional:
    ROI, USE_ROI
)
from .vision import find_red_boxes_from_mask, hsv_mask, draw_debug


def capture_screen(monitor_index=1):
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]  # 1 = principal
        shot = sct.grab(monitor)
        frame = np.array(shot)[:, :, :3]  # BGRA -> BGR
        return frame


def crop_roi(frame, roi):
    x, y, w, h = roi
    return frame[y:y+h, x:x+w].copy()


def main():
    last_run = 0.0

    while True:
        now = time.time()
        if now - last_run < EVERY_SECONDS:
            time.sleep(0.05)
            continue
        last_run = now

        frame = capture_screen(monitor_index=1)

        # opcional: restringe a análise a uma região fixa
        offset_x = 0
        offset_y = 0
        if USE_ROI:
            offset_x, offset_y, w, h = ROI
            frame = crop_roi(frame, ROI)

        mask = hsv_mask(frame, ranges=[
            (RED1_HSV_LO, RED1_HSV_HI),
            (RED2_HSV_LO, RED2_HSV_HI),
        ])

        cv2.imshow("mask_red", mask)
        cv2.waitKey(1)


        boxes = find_red_boxes_from_mask(mask)

        print(f"[INFO] Encontrados {len(boxes)} quadrados vermelhos")

        # se estiver usando ROI, ajusta as coordenadas para referência global/da tela
        for i, (_, _, w, h, area, cx, cy) in enumerate(boxes[:10], start=1):
            gx = cx + offset_x
            gy = cy + offset_y
            print(f"  #{i}: center_roi=({cx},{cy}) center_screen=({gx},{gy}) size=({w}x{h}) area={int(area)}")

        dbg = draw_debug(frame, boxes)
        cv2.imshow("debug", dbg)
        cv2.waitKey(1)


if __name__ == "__main__":
    main()
