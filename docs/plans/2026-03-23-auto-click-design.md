# Auto Click Design

## Goal

Add a separate Python script that starts clicking after a fixed 5 second delay, keeps clicking at the mouse's current position with a random delay between 1 and 2 seconds, and stops as soon as the user presses `Esc`.

## Architecture

The feature lives in a new standalone module, `src/auto_click.py`, so it does not interfere with the existing bot modes in `src/main.py`. The script reuses the project's existing macOS stack:

- `pyautogui` for reading the current mouse position and issuing clicks
- `Quartz` event tap APIs for detecting `Esc` globally on macOS

## Components

- `EscKeyMonitor`: runs a Quartz event tap on a background thread and raises a shared stop event when `Esc` is pressed
- `interruptible_sleep`: waits in small slices so the script can stop quickly during the initial delay or between clicks
- `run_auto_click`: coordinates startup messaging, the 5 second delay, the click loop, and graceful shutdown

## Data Flow

1. Start the `Esc` monitor.
2. Wait 5 seconds so the user can place the mouse.
3. Read the current pointer position and click there.
4. Pick a random delay in the `[1.0, 2.0]` range.
5. Repeat until the shared stop event is set by `Esc`, `Ctrl+C`, or a PyAutoGUI fail-safe.

## Error Handling

- If the Quartz event tap cannot be created, exit with a clear message asking for macOS Accessibility and Input Monitoring permissions.
- If PyAutoGUI fail-safe triggers, stop the loop cleanly.
- If the user interrupts the process with `Ctrl+C`, return a non-zero exit code and print a friendly shutdown message.

## Testing

Unit tests cover the pure timing helpers and the high-level loop behavior with mocked mouse, delay, and monitor dependencies. The global key hook itself is not integration-tested because it depends on macOS permissions and a live event stream.
