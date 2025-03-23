import time
import pyautogui
from utils.vision import find_and_click

print("Starting OSRS Bot in 3 seconds...")
time.sleep(3)


# Move the mouse to a specific location
pyautogui.moveTo(500, 500, duration=1)

# Click the left mouse button
pyautogui.click()