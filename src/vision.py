import cv2
import numpy as np
from .config import MIN_AREA

### meu im0port aqui ###
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)

import re
import mss
import pytesseract


####### MEU CODIGO ABAIXO #######

ROI = {"left": 190, "top": 40, "width": 380, "height": 120}

ROI_RELATIVE = {
    "left": 0,   # 10px da borda esquerda da janela
    "top": 35,    # 10px do topo da janela
    "width": 140,
    "height": 60
}

def crop_margin(img, m=12):
    h, w = img.shape[:2]
    return img[m:h-m, m:w-m]


def preprocess(img_bgr: np.ndarray) -> np.ndarray:
    img_bgr = crop_margin(img_bgr, m=12)

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # upscale forte
    gray = cv2.resize(gray, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)

    # leve blur pra reduzir serrilhado
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # binariza (invertido costuma ser melhor em HUD)
    th = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 8
    )

    # "engorda" o contorno pra preencher as letras
    k = np.ones((2, 2), np.uint8)
    th = cv2.dilate(th, k, iterations=1)

    # fecha buracos internos
    k2 = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k2, iterations=1)

    # remove pontinhos (opcional, mas ajuda)
    th = cv2.medianBlur(th, 3)

    return th

def ocr_text(img_bin: np.ndarray) -> str:
    config = "--oem 3 --psm 6"  # psm 6: bloco de texto
    txt = pytesseract.image_to_string(img_bin, lang="por+eng", config=config)
    return txt.strip()


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

            # IGNORA JANELAS PEQUENAS (seu caso: 45x24)
            if width < 300 or height < 300:
                continue

            area = width * height
            if area > best_area:
                best_area = area
                best = (bounds, w)

    return best if best else (None, None)

def roi_from_window(bounds, roi_rel, scale=1.0):
    wx = bounds["X"] * scale
    wy = bounds["Y"] * scale
    ww = bounds["Width"] * scale
    wh = bounds["Height"] * scale

    w = roi_rel["width"] * scale
    h = roi_rel["height"] * scale

    x = wx + roi_rel["left"] * scale
    y = wy + roi_rel["top"] * scale

    # clamp pra garantir que fica dentro da janela
    x = max(wx, min(x, wx + ww - w))
    y = max(wy, min(y, wy + wh - h))

    return {
        "left": int(x),
        "top": int(y),
        "width": int(w),
        "height": int(h),
    }



def crop_hp_band(img_bgr):
    h, w = img_bgr.shape[:2]
    # pega só a parte de baixo (ajuste o 0.55/0.60 conforme necessário)
    return img_bgr[int(h * 0.55):, :]

def parse_hp(txt, default_max=25):
    txt = txt.strip()

    # caso normal
    m = re.search(r"(\d{1,3})/(\d{1,3})", txt)
    if m:
        return int(m.group(1)), int(m.group(2))

    # se veio só o max (ex: "25") -> assume 0/25
    if re.fullmatch(r"\d{1,3}", txt):
        val = int(txt)
        if val == default_max:
            return 0, default_max

        # se veio "1" quando era "10/25" e o 0 sumiu, dá pra tentar:
        # mas só aplique se você aceitar esse comportamento:
        if val < default_max:
            # não dá pra saber se era "val/25" ou "val0/25"
            # então NÃO inventamos aqui; retorna None
            return None

    # se veio algo tipo "1025" (sumiu o /) -> tenta dividir
    digits = re.sub(r"\D", "", txt)
    if len(digits) == 4 and digits.endswith(f"{default_max:02d}"):
        # ex: 1025 -> 10/25
        return int(digits[:2]), default_max
    if len(digits) == 3 and digits.endswith(str(default_max)):
        # ex: 025 -> 0/25
        return int(digits[:-2]), default_max

    return None


def extract_white_text(img_bgr, thr=175):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=6.0, fy=6.0, interpolation=cv2.INTER_CUBIC)

    _, mask = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)

    # em vez de dilate forte, use OPEN leve pra remover "pontas" que viram dígitos
    mask = cv2.medianBlur(mask, 3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2,2), np.uint8), iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), iterations=1)

    return mask

def ocr_hp_from_mask(mask):
    # NÃO faz resize aqui
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


def main():
    with mss.mss() as sct:
        bounds, win = find_window("runelite")  # pode também passar title_contains="lomeuu"
        if not bounds:
            raise RuntimeError("Janela grande não encontrada")

        # print("WIN:", win.get("kCGWindowOwnerName"), win.get("kCGWindowName"), win.get("kCGWindowNumber"))
        # print("BOUNDS:", bounds)

        # garante que é a janela certa
        assert bounds["Width"] >= 300 and bounds["Height"] >= 300
        
        # print("MONITORS:", sct.monitors)

        ROI = roi_from_window(bounds, ROI_RELATIVE)
        shot = sct.grab(ROI)
        img = np.array(shot)[:, :, :3]
        img_bin = preprocess(img)
        text = ocr_text(img_bin)

        hp_band = crop_hp_band(img)
        cv2.imwrite("/tmp/hp_band.png", hp_band)

        # tente 2 thresholds: um mais alto e um mais baixo (pra pegar o 0)
        best = None
        best_txt = ""

        for thr in (185, 175, 165):
            mask = extract_white_text(hp_band, thr=thr)
            cv2.imwrite(f"/tmp/hp_white_{thr}.png", mask)

            hp_txt = ocr_hp_from_mask(mask)
            hp = parse_hp(hp_txt, default_max=25)

            if hp:
                best = hp
                best_txt = hp_txt
                break

        print("HP OCR:", repr(best_txt))
        if best:
            print("HP:", best)
        else:
            print("HP não detectado")


        # Exemplo: extrair um número/posição
        m = re.search(r"(-?\d+)\s*,\s*(-?\d+)", text)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            print("Posição detectada:", x, y)
            # chame sua função aqui
        else:
            print("Não achei padrão esperado.")

if __name__ == "__main__":
    main()