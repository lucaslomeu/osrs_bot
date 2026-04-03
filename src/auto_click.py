import random
import re
import threading
import time

import pyautogui
from Quartz import (
    CGEventGetIntegerValueField,
    CGEventTapCreate,
    CGEventTapEnable,
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    kCFRunLoopCommonModes,
    kCGEventKeyDown,
    kCGEventTapDisabledByTimeout,
    kCGEventTapDisabledByUserInput,
    kCGEventTapOptionListenOnly,
    kCGHeadInsertEventTap,
    kCGKeyboardEventKeycode,
    kCGSessionEventTap,
)

START_DELAY_SECONDS = 10.0
CLICK_DELAY_RANGE_SECONDS = (1.0, 2.0)
ESC_KEYCODE = 53
POLL_INTERVAL_SECONDS = 0.05

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


def parse_click_delay_range(raw_value):
    """Parse a CLI delay range formatted like '1-2'."""
    if raw_value is None:
        return CLICK_DELAY_RANGE_SECONDS

    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*", raw_value)
    if match is None:
        raise ValueError("Auto-click delay range must use the format 'min-max', for example '1-2'.")

    try:
        minimum = float(match.group(1))
        maximum = float(match.group(2))
    except ValueError as exc:
        raise ValueError("Auto-click delay range must contain numeric values, for example '1-2'.") from exc

    if minimum < 0 or maximum < 0:
        raise ValueError("Auto-click delay range cannot contain negative values.")
    if minimum > maximum:
        raise ValueError("Auto-click delay range requires min <= max.")

    return minimum, maximum


def choose_click_delay(delay_range=CLICK_DELAY_RANGE_SECONDS):
    """Return the randomized delay before the next click."""
    return random.uniform(*delay_range)


def interruptible_sleep(stop_event, duration, poll_interval=POLL_INTERVAL_SECONDS):
    """Sleep until the timeout expires or a stop event is raised."""
    remaining = max(0.0, duration)
    deadline = time.monotonic() + remaining

    while not stop_event.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        stop_event.wait(min(poll_interval, remaining))

    return False


class EscKeyMonitor:
    """Monitor the global keyboard stream and stop on Esc."""

    def __init__(self, stop_event):
        self.stop_event = stop_event
        self._thread = None
        self._run_loop = None
        self._event_tap = None
        self._run_loop_source = None
        self._ready = threading.Event()
        self._error = None

    def start(self):
        """Start the macOS key monitor in a background thread."""
        self._thread = threading.Thread(target=self._run, name="esc-key-monitor", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)

        if self._error is not None:
            raise self._error
        if not self._ready.is_set():
            raise RuntimeError("Timed out while starting the Esc key monitor.")

    def stop(self):
        """Stop the monitor thread and event loop."""
        self.stop_event.set()
        if self._run_loop is not None:
            CFRunLoopStop(self._run_loop)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _handle_event(self, _proxy, event_type, event, _refcon):
        if event_type in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
            if self._event_tap is not None:
                CGEventTapEnable(self._event_tap, True)
            return event

        if event_type == kCGEventKeyDown:
            keycode = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
            if keycode == ESC_KEYCODE:
                print("\nEsc detected. Stopping auto click.")
                self.stop_event.set()
                if self._run_loop is not None:
                    CFRunLoopStop(self._run_loop)

        return event

    def _run(self):
        event_mask = 1 << kCGEventKeyDown
        self._event_tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            event_mask,
            self._handle_event,
            None,
        )

        if self._event_tap is None:
            self._error = RuntimeError(
                "Unable to monitor Esc globally. Allow Accessibility and Input Monitoring "
                "for your terminal or Python app in macOS System Settings, then try again."
            )
            self._ready.set()
            return

        self._run_loop_source = CFMachPortCreateRunLoopSource(None, self._event_tap, 0)
        self._run_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._run_loop, self._run_loop_source, kCFRunLoopCommonModes)
        CGEventTapEnable(self._event_tap, True)
        self._ready.set()
        CFRunLoopRun()


def run_auto_click(start_delay=START_DELAY_SECONDS, delay_range=CLICK_DELAY_RANGE_SECONDS):
    """Run the standalone auto click loop."""
    stop_event = threading.Event()
    monitor = EscKeyMonitor(stop_event)

    try:
        monitor.start()
        print(f"Auto click starts in {start_delay:.0f} seconds.")
        print("Leave the mouse on the target and press Esc to stop.")

        if not interruptible_sleep(stop_event, start_delay):
            return 0

        click_count = 0
        while not stop_event.is_set():
            try:
                mouse_x, mouse_y = pyautogui.position()
                pyautogui.click(x=mouse_x, y=mouse_y)
            except pyautogui.FailSafeException:
                print("PyAutoGUI fail-safe triggered. Stopping auto click.")
                stop_event.set()
                break

            click_count += 1
            print(f"Click {click_count} at ({mouse_x}, {mouse_y}).")

            delay_seconds = choose_click_delay(delay_range)
            print(f"Waiting {delay_seconds:.2f}s before the next click.")
            if not interruptible_sleep(stop_event, delay_seconds):
                break

        return 0
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Stopping auto click.")
        return 130
    except RuntimeError as exc:
        print(exc)
        return 1
    finally:
        monitor.stop()


def main():
    raise SystemExit(run_auto_click())


if __name__ == "__main__":
    main()
