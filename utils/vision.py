import pyautogui
import time

def find_and_click(img_path, delay=5, confidence=0.7):
    startTime = time.time()

    while time.time() - startTime < delay:
        position = pyautogui.locateCenterOnScreen(img_path, confidence=confidence)
        if position:
            pyautogui.moveTo(position.x, position.y, duration=0.3)
            pyautogui.click()
            return True
        return False
    
