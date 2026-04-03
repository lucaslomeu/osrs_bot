import threading
import unittest
from unittest import mock

from src import auto_click


class AutoClickTests(unittest.TestCase):
    def test_parse_click_delay_range_returns_defaults_when_missing(self):
        self.assertEqual(
            auto_click.parse_click_delay_range(None),
            auto_click.CLICK_DELAY_RANGE_SECONDS,
        )

    def test_parse_click_delay_range_parses_cli_format(self):
        self.assertEqual(auto_click.parse_click_delay_range("1-2"), (1.0, 2.0))
        self.assertEqual(auto_click.parse_click_delay_range("0.5-1.25"), (0.5, 1.25))

    def test_parse_click_delay_range_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "format"):
            auto_click.parse_click_delay_range("1")

        with self.assertRaisesRegex(ValueError, "format"):
            auto_click.parse_click_delay_range("a-b")

        with self.assertRaisesRegex(ValueError, "negative"):
            auto_click.parse_click_delay_range("-1-2")

        with self.assertRaisesRegex(ValueError, "min <="):
            auto_click.parse_click_delay_range("3-2")

    def test_choose_click_delay_uses_requested_range(self):
        with mock.patch("src.auto_click.random.uniform", return_value=1.37) as uniform_mock:
            delay = auto_click.choose_click_delay((1.0, 2.0))

        self.assertEqual(delay, 1.37)
        uniform_mock.assert_called_once_with(1.0, 2.0)

    def test_interruptible_sleep_returns_true_when_duration_is_zero(self):
        stop_event = threading.Event()

        completed = auto_click.interruptible_sleep(stop_event, 0.0)

        self.assertTrue(completed)

    def test_interruptible_sleep_returns_false_when_already_stopped(self):
        stop_event = threading.Event()
        stop_event.set()

        completed = auto_click.interruptible_sleep(stop_event, 0.5)

        self.assertFalse(completed)

    def test_run_auto_click_clicks_current_mouse_position_once(self):
        class FakeMonitor:
            def __init__(self, stop_event):
                self.stop_event = stop_event
                self.started = False
                self.stopped = False

            def start(self):
                self.started = True

            def stop(self):
                self.stopped = True

        sleep_calls = []

        def fake_sleep(stop_event, duration, poll_interval=auto_click.POLL_INTERVAL_SECONDS):
            sleep_calls.append((duration, poll_interval))
            if len(sleep_calls) == 1:
                return True
            stop_event.set()
            return False

        with mock.patch("src.auto_click.EscKeyMonitor", FakeMonitor), \
                mock.patch("src.auto_click.interruptible_sleep", side_effect=fake_sleep), \
                mock.patch("src.auto_click.choose_click_delay", return_value=1.25) as delay_mock, \
                mock.patch("src.auto_click.pyautogui.position", return_value=(321, 654)) as position_mock, \
                mock.patch("src.auto_click.pyautogui.click") as click_mock:
            exit_code = auto_click.run_auto_click()

        self.assertEqual(exit_code, 0)
        position_mock.assert_called_once_with()
        click_mock.assert_called_once_with(x=321, y=654)
        delay_mock.assert_called_once_with(auto_click.CLICK_DELAY_RANGE_SECONDS)
        self.assertEqual(len(sleep_calls), 2)
        self.assertEqual(sleep_calls[0][0], auto_click.START_DELAY_SECONDS)
        self.assertEqual(sleep_calls[1][0], 1.25)

    def test_run_auto_click_returns_error_when_monitor_cannot_start(self):
        class FailingMonitor:
            def __init__(self, _stop_event):
                pass

            def start(self):
                raise RuntimeError("permission denied")

            def stop(self):
                pass

        with mock.patch("src.auto_click.EscKeyMonitor", FailingMonitor):
            exit_code = auto_click.run_auto_click()

        self.assertEqual(exit_code, 1)
