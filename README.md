# osrs_bot

A small macOS bot toolkit for Old School RuneScape, split by activity.

## Requirements

- macOS (uses Quartz APIs)
- Python 3.9+

## Setup

Install dependencies:

- `pip install -r requirements.txt`

## Configuration

- All settings live in `config.json`
- `fletching.first_click` and `fletching.second_click` accept either `x/y` or `x_ratio/y_ratio`
- `magic.click` uses `x_ratio/y_ratio`
- If your RuneLite layout changes, recalibrate the click points and HP templates

## HP Calibration

Before using `combat`, calibrate HP:

- `./.venv/bin/python3 -m src.cli calibrate-hp`

Templates are saved in `data/hp_templates`.

## Running

Main commands:

- `./.venv/bin/python3 -m src.cli combat`
- `./.venv/bin/python3 -m src.cli fletching`
- `./.venv/bin/python3 -m src.cli magic`
- `./.venv/bin/python3 -m src.cli hp`
- `./.venv/bin/python3 -m src.cli auto-click`

Custom config:

- `./.venv/bin/python3 -m src.cli combat --config /path/to/config.json`

Click calibration:

- `./.venv/bin/python3 -m src.cli calibrate-click magic.click`
- `./.venv/bin/python3 -m src.cli calibrate-click fletching.first_click`
- `./.venv/bin/python3 -m src.cli calibrate-click fletching.second_click`

Move the mouse over the desired point inside RuneLite and press Enter. The command updates `config.json` automatically.
