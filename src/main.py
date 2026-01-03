import time
import numpy as np
import cv2
import mss
import pyautogui

from .config import (
    EVERY_SECONDS,
    RED1_HSV_LO, RED1_HSV_HI,
    RED2_HSV_LO, RED2_HSV_HI,
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


def click_point(x, y):
    pyautogui.moveTo(x, y, duration=0.05)
    pyautogui.click()


def main():
    while True:
        frame_full = capture_screen(monitor_index=1)

        # offsets para clique (se usar ROI)
        offset_x = 0
        offset_y = 0
        frame = frame_full

        if USE_ROI:
            offset_x, offset_y, w, h = ROI
            frame = crop_roi(frame_full, ROI)

        mask = hsv_mask(frame, ranges=[
            (RED1_HSV_LO, RED1_HSV_HI),
            (RED2_HSV_LO, RED2_HSV_HI),
        ])

        boxes = find_red_boxes_from_mask(mask)

        # Debug (opcional)
        cv2.imshow("mask_red", mask)
        dbg = draw_debug(frame, boxes)
        cv2.imshow("debug", dbg)
        cv2.waitKey(1)

        if boxes:
            # pega o maior (já vem ordenado por área)
            x, y, w, h, area, cx, cy = boxes[0]

            # converte para coordenadas de tela se estiver usando ROI
            click_x = cx + offset_x
            click_y = cy + offset_y

            print(f"[INFO] Clique no maior alvo: area={int(area)} pos=({click_x},{click_y})")
            click_point(click_x, click_y)

            # depois de clicar, aguarda 20s antes de procurar de novo
            time.sleep(EVERY_SECONDS)
        else:
            print("[INFO] Nenhum quadrado vermelho encontrado. Tentando de novo em 1s...")
            time.sleep(1)


if __name__ == "__main__":
    main()
