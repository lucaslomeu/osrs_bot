import pyautogui
import time

def find_and_click(image_path, delay=5, confidence=0.7):
    startTime = time.time()

    while time.time() - startTime < delay:
        position = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)

        if position:
            pyautogui.moveTo(position.x, position.y, duration=0.3)
            pyautogui.click()
            return True
        
        time.sleep(0.1 + 0.2 * time.time() % 1)
        return False
    
