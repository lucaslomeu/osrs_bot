# Bot Separation Design

## Goals

- split each bot mode into its own module
- isolate shared infrastructure into a dedicated folder
- replace flag-based execution with a clean command-based CLI
- support simple commands such as `uv run combat` and `uv run fletching`

## Structure

- `src/cli.py`: top-level command dispatch
- `src/combat.py`: combat loop and combat-specific helpers
- `src/fletching.py`: fletching loop and validation
- `src/core/config.py`: defaults, config loading, path resolution
- `src/core/window.py`: RuneLite window lookup, capture, ROI helpers
- `src/core/hp.py`: HP capture, recognition, monitoring
- `src/core/calibration.py`: HP template calibration flow
- `src/core/vision.py`: mask and contour utilities
- `src/core/input.py`: mouse movement and click helpers
- `src/core/timing.py`: randomized interval helpers
- `src/core/debug.py`: debug frame persistence

## CLI

- `uv run combat`
- `uv run fletching`
- `uv run hp`
- `uv run calibrate-hp`
- `uv run auto-click`

The project also keeps a unified CLI through `python -m src.cli <command>`.

## Risks

- moving combat and HP functions across modules can break imports or subtle runtime behavior
- packaging needs a `pyproject.toml` so `uv run <script>` resolves local entrypoints
- test imports must move away from the old monolithic `src.main`

## Validation

- update tests to cover the new module boundaries
- run the unit test suite after refactoring
- verify CLI parsing and the generated `uv` commands
