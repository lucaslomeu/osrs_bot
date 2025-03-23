import time
from utils.actions import mine_ore

def choose_skill():
    print("Choose a skill to train:")
    print("1. Mining")

    option = input("Enter your choice: ")
    return option.strip()


def choose_ore():
    ores = {
        "1": "Copper",
        "2": "Tin",
        "3": "Iron",
        "4": "Coal",
        "5": "Mithril",
        "6": "Adamant",
        "7": "Rune",
        "8": "Gold",
        "9": "Silver"
    }

    print("\nChoose an ore to mine:")
    for key, value in ores.items():
        print(f"{key}. {value}")

    option = input("Enter your choice: ").strip()
    return ores.get(option)

skill = choose_skill()

if skill == "1":
    ore_type = choose_ore()

    if ore_type:
        print(f"\n[INFO] Starting OSRS Bot to mine {ore_type} in 3 seconds...")
        time.sleep(3)

        while True:
            try:
                if not mine_ore(ore_type):
                    print(f"[WARN] No {ore_type} found... wait respawn")
                    time.sleep(5)

            except KeyboardInterrupt:
                print("\n[INFO] Exiting OSRS Bot...")
                break
    else:
        print("[WARN] Invalid ore type...")
else:
    print("[WARN] Invalid skill...")
        



