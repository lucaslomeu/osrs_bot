# osrs_bot

Simple macOS bot for Old School RuneScape that:

- finds pink target boxes on the RuneLite window
- clicks once to attack
- reads HP via OCR
- waits for the target to die before acquiring a new one

## Requirements

- macOS (uses Quartz APIs)
- Python 3.9+
- Tesseract OCR installed (for `pytesseract`)
  - With Homebrew: `brew install tesseract`

## Setup

Create and activate a virtualenv (optional but recommended), then install deps:

- With `uv`:
  - `uv pip install -r requirements.txt`
- Or with `pip`:
  - `pip install -r requirements.txt`

## Running

1. Open RuneLite and log into the game.
2. Make sure the game window is visible on the main screen.
3. From the project root, run:

- `python -m src.main`

The bot will start scanning for pink boxes and attacking targets automatically.
