import copy
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src import cli, combat, fletching, magic
from src.core import calibration, config as config_module, hp, input as input_module, vision, window


class MainModuleTests(unittest.TestCase):
    def make_config(self, _root: Path):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG)
        config["hp"]["template_dir"] = "hp_templates"
        config["debug"]["dir"] = "debug"
        return config

    def render_digit_template(self, digit_char: str, config):
        canvas = np.zeros((48, 32), dtype=np.uint8)
        cv2.putText(
            canvas,
            digit_char,
            (3, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            255,
            2,
            cv2.LINE_AA,
        )
        _, canvas = cv2.threshold(canvas, 10, 255, cv2.THRESH_BINARY)
        return hp.normalize_digit_image(canvas, config["hp"]["template_size"])

    def build_mask_from_digits(self, digit_chars, templates):
        pieces = [vision.crop_nonzero_mask(templates[digit_char]) for digit_char in digit_chars]
        height = max(piece.shape[0] for piece in pieces) + 4
        width = sum(piece.shape[1] for piece in pieces) + (len(pieces) - 1) * 6 + 4
        mask = np.zeros((height, width), dtype=np.uint8)

        cursor_x = 2
        for piece in pieces:
            cursor_y = (height - piece.shape[0]) // 2
            mask[cursor_y:cursor_y + piece.shape[0], cursor_x:cursor_x + piece.shape[1]] = piece
            cursor_x += piece.shape[1] + 6

        return mask

    def build_engaged_panel_image(self, config):
        image = np.zeros((220, 420, 3), dtype=np.uint8)
        roi = config["attack"]["engaged_panel"]["roi"]
        bar_roi = config["attack"]["engaged_panel"]["bar_roi"]
        bar_x = roi["left"] + bar_roi["left"] + 12
        bar_y = roi["top"] + bar_roi["top"] + 42

        cv2.rectangle(image, (bar_x, bar_y), (bar_x + 78, bar_y + 14), (0, 255, 0), -1)
        cv2.rectangle(image, (bar_x + 79, bar_y), (bar_x + 124, bar_y + 14), (0, 0, 255), -1)
        return image

    def write_templates(self, config, root: Path):
        template_dir = root / config["hp"]["template_dir"]
        template_dir.mkdir(parents=True, exist_ok=True)
        templates = {}
        for digit_char in "0123456789":
            template = self.render_digit_template(digit_char, config)
            templates[digit_char] = template
            cv2.imwrite(str(template_dir / f"{digit_char}.png"), template)
        return templates

    def test_load_config_merges_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "heal": {"eat_at_hp": 12},
                        "hp": {"template_dir": "custom_templates"},
                    }
                ),
                encoding="utf-8",
            )

            loaded = config_module.load_config(config_path)

            self.assertEqual(loaded["heal"]["eat_at_hp"], 12)
            self.assertEqual(loaded["hp"]["template_dir"], "custom_templates")
            self.assertEqual(
                loaded["fletching"]["first_click"]["jitter_x"],
                config_module.DEFAULT_CONFIG["fletching"]["first_click"]["jitter_x"],
            )
            self.assertEqual(
                loaded["attack"]["target_missing_streak"],
                config_module.DEFAULT_CONFIG["attack"]["target_missing_streak"],
            )

    def test_roi_from_window_supports_right_and_bottom_anchors(self):
        region = window.roi_from_window(
            {"X": 10, "Y": 20, "Width": 200, "Height": 100},
            {"right": 30, "bottom": 15, "width": 40, "height": 20},
        )

        self.assertEqual(region, {"left": 140, "top": 85, "width": 40, "height": 20})

    def test_validate_fletching_config_requires_coordinates(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG["fletching"])

        with self.assertRaisesRegex(ValueError, "first_click"):
            fletching.validate_fletching_config(config)

    def test_choose_window_click_point_stays_inside_window(self):
        bounds = {"X": 100, "Y": 200, "Width": 20, "Height": 15}
        point_config = {"x": 0, "y": 0, "jitter_x": 25, "jitter_y": 25}

        for _ in range(50):
            screen_x, screen_y = input_module.choose_window_click_point(bounds, point_config)
            self.assertGreaterEqual(screen_x, bounds["X"])
            self.assertLess(screen_x, bounds["X"] + bounds["Width"])
            self.assertGreaterEqual(screen_y, bounds["Y"])
            self.assertLess(screen_y, bounds["Y"] + bounds["Height"])

    def test_cli_parser_supports_fletching_subcommand(self):
        args = cli.build_parser().parse_args(["fletching"])

        self.assertEqual(args.command, "fletching")
        self.assertEqual(args.config, str(config_module.DEFAULT_CONFIG_PATH))

    def test_cli_parser_supports_magic_subcommand(self):
        args = cli.build_parser().parse_args(["magic"])

        self.assertEqual(args.command, "magic")
        self.assertEqual(args.config, str(config_module.DEFAULT_CONFIG_PATH))

    def test_cli_parser_supports_calibrate_click_subcommand(self):
        args = cli.build_parser().parse_args(["calibrate-click", "magic.click"])

        self.assertEqual(args.command, "calibrate-click")
        self.assertEqual(args.target, "magic.click")
        self.assertEqual(args.config, str(config_module.DEFAULT_CONFIG_PATH))

    def test_cli_parser_supports_auto_click_range_argument(self):
        args = cli.build_parser().parse_args(["auto-click", "1-2"])

        self.assertEqual(args.command, "auto-click")
        self.assertEqual(args.delay_range, "1-2")

    def test_validate_fletching_config_requires_move_duration(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG["fletching"])
        config["first_click"]["x"] = 10
        config["first_click"]["y"] = 10
        config["second_click"]["x"] = 20
        config["second_click"]["y"] = 20
        config.pop("move_duration_seconds")

        with self.assertRaisesRegex(ValueError, "move_duration_seconds"):
            fletching.validate_fletching_config(config)

    def test_validate_fletching_config_accepts_ratio_points(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG["fletching"])
        config["first_click"]["x_ratio"] = 0.25
        config["first_click"]["y_ratio"] = 0.50
        config["first_click"]["x"] = None
        config["first_click"]["y"] = None
        config["second_click"]["x_ratio"] = 0.75
        config["second_click"]["y_ratio"] = 0.80
        config["second_click"]["x"] = None
        config["second_click"]["y"] = None

        fletching.validate_fletching_config(config)

    def test_validate_magic_config_requires_ratios(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG["magic"])

        with self.assertRaisesRegex(ValueError, "x_ratio"):
            magic.validate_magic_config(config)

    def test_choose_window_ratio_click_point_stays_inside_window(self):
        bounds = {"X": 100, "Y": 200, "Width": 300, "Height": 200}
        point_config = {"x_ratio": 0.5, "y_ratio": 0.5, "jitter_x": 15, "jitter_y": 15}

        for _ in range(50):
            screen_x, screen_y = input_module.choose_window_ratio_click_point(bounds, point_config)
            self.assertGreaterEqual(screen_x, bounds["X"])
            self.assertLess(screen_x, bounds["X"] + bounds["Width"])
            self.assertGreaterEqual(screen_y, bounds["Y"])
            self.assertLess(screen_y, bounds["Y"] + bounds["Height"])

    def test_choose_configured_window_click_point_supports_ratio(self):
        bounds = {"X": 100, "Y": 200, "Width": 300, "Height": 200}
        point_config = {"x_ratio": 0.5, "y_ratio": 0.5, "jitter_x": 0, "jitter_y": 0}

        screen_x, screen_y = input_module.choose_configured_window_click_point(bounds, point_config)

        self.assertEqual(screen_x, 100 + round((300 - 1) * 0.5))
        self.assertEqual(screen_y, 200 + round((200 - 1) * 0.5))

    def test_get_window_relative_click_details_returns_pixels_and_ratios(self):
        details = calibration.get_window_relative_click_details(
            {"X": 100, "Y": 200, "Width": 401, "Height": 201},
            300,
            250,
        )

        self.assertEqual(details["x"], 200)
        self.assertEqual(details["y"], 50)
        self.assertAlmostEqual(details["x_ratio"], 0.5)
        self.assertAlmostEqual(details["y_ratio"], 0.25)

    def test_update_click_target_in_config_writes_magic_ratios(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps({"magic": {"click": {}}}), encoding="utf-8")

            calibration.update_click_target_in_config(
                config_path,
                "magic.click",
                {"x_ratio": 0.64513, "y_ratio": 0.731173},
            )

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["magic"]["click"]["x_ratio"], 0.64513)
            self.assertEqual(saved["magic"]["click"]["y_ratio"], 0.731173)

    def test_update_click_target_in_config_writes_fletching_ratios_and_clears_pixels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps({"fletching": {"first_click": {"x": 100, "y": 200}}}),
                encoding="utf-8",
            )

            calibration.update_click_target_in_config(
                config_path,
                "fletching.first_click",
                {"x_ratio": 0.25, "y_ratio": 0.5},
            )

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIsNone(saved["fletching"]["first_click"]["x"])
            self.assertIsNone(saved["fletching"]["first_click"]["y"])
            self.assertEqual(saved["fletching"]["first_click"]["x_ratio"], 0.25)
            self.assertEqual(saved["fletching"]["first_click"]["y_ratio"], 0.5)

    def test_calibration_saves_labeled_digit_templates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            rendered_templates = self.write_templates(config, root)
            mask = self.build_mask_from_digits("15", rendered_templates)

            template_dir = root / config["hp"]["template_dir"]
            for path in template_dir.glob("*.png"):
                path.unlink()

            success, message, saved_digits = calibration.save_digit_templates_from_label(
                mask,
                "15",
                config,
                root,
            )

            self.assertTrue(success)
            self.assertIn("Saved templates", message)
            self.assertEqual(saved_digits, ["1", "5"])
            self.assertTrue((template_dir / "1.png").exists())
            self.assertTrue((template_dir / "5.png").exists())

    def test_recognize_hp_value_from_mask_matches_templates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            expected_templates = self.write_templates(config, root)
            template_dir = root / config["hp"]["template_dir"]
            for path in template_dir.glob("*.png"):
                path.unlink()

            for digit_char in "0123456789":
                calibration.save_digit_templates_from_label(
                    self.build_mask_from_digits(digit_char, expected_templates),
                    digit_char,
                    config,
                    root,
                )

            loaded_templates, missing = hp.load_hp_templates(config, root)
            mask = self.build_mask_from_digits("15", expected_templates)

            value, details = hp.recognize_hp_value_from_mask(mask, loaded_templates, config)

            self.assertEqual(missing, [])
            self.assertEqual(value, 15)
            self.assertEqual(details["digit_text"], "15")
            self.assertEqual(details["reason"], "ok")

    def test_recognize_hp_value_rejects_low_confidence_noise(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            config["hp"]["digit_match_threshold"] = 0.95
            self.write_templates(config, root)
            loaded_templates, _ = hp.load_hp_templates(config, root)

            noise = np.zeros((20, 20), dtype=np.uint8)
            cv2.rectangle(noise, (2, 2), (17, 17), 255, -1)
            value, details = hp.recognize_hp_value_from_mask(noise, loaded_templates, config)

            self.assertIsNone(value)
            self.assertIn(details["reason"], {"low_confidence", "no_digits"})

    def test_heal_gate_requires_new_hp_value(self):
        self.assertFalse(combat.should_attempt_heal(None, 15, False, 10.0, 0.0))
        self.assertFalse(combat.should_attempt_heal(15, 15, True, 10.0, 0.0))
        self.assertFalse(combat.should_attempt_heal(15, 15, False, 0.5, 1.0))
        self.assertTrue(combat.should_attempt_heal(15, 15, False, 10.0, 0.0))

        self.assertFalse(combat.should_unlock_heal_wait(True, 15, 15))
        self.assertTrue(combat.should_unlock_heal_wait(True, 15, 14))

    def test_find_tracked_target_box_prefers_containing_then_nearest(self):
        boxes = [
            (10, 10, 20, 20, 400, 20, 20),
            (60, 10, 20, 20, 400, 70, 20),
        ]

        containing = vision.find_tracked_target_box(boxes, 18, 18, 30)
        nearest = vision.find_tracked_target_box(boxes, 52, 18, 30)
        missing = vision.find_tracked_target_box(boxes, 120, 120, 20)

        self.assertEqual(containing, boxes[0])
        self.assertEqual(nearest, boxes[1])
        self.assertIsNone(missing)

    def test_should_log_status_when_snapshot_changes_or_interval_expires(self):
        snapshot = ("ATTACK", 11, "11", "ok", False)

        self.assertTrue(combat.should_log_status(10.0, snapshot, None, 11.0))
        self.assertFalse(combat.should_log_status(10.0, snapshot, snapshot, 11.0))
        self.assertTrue(combat.should_log_status(12.0, snapshot, snapshot, 11.0))

    def test_filter_attack_boxes_rejects_large_and_skinny_regions(self):
        attack_config = copy.deepcopy(config_module.DEFAULT_CONFIG["attack"])
        boxes = [
            (276, 447, 201, 167, 18474.5, 376, 530),
            (566, 520, 115, 95, 7316.5, 623, 567),
            (254, 328, 85, 71, 4979.0, 296, 363),
            (512, 820, 18, 155, 2591.0, 521, 897),
            (898, 355, 99, 22, 2050.0, 947, 366),
        ]

        filtered = combat.filter_attack_boxes(boxes, attack_config)

        self.assertEqual(filtered, [boxes[1], boxes[2]])

    def test_detect_engaged_target_panel_from_health_bar(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG)
        image = self.build_engaged_panel_image(config)

        visible, details = combat.detect_engaged_target_panel(image, config)

        self.assertTrue(visible)
        self.assertIsNotNone(details["best_box"])
        self.assertGreaterEqual(details["best_box"][2], config["attack"]["engaged_panel"]["min_width"])

    def test_detect_engaged_target_panel_returns_false_when_absent(self):
        config = copy.deepcopy(config_module.DEFAULT_CONFIG)
        image = np.zeros((220, 420, 3), dtype=np.uint8)

        visible, details = combat.detect_engaged_target_panel(image, config)

        self.assertFalse(visible)
        self.assertIsNone(details["best_box"])


if __name__ == "__main__":
    unittest.main()
