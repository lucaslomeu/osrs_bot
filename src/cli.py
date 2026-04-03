import argparse
import sys
from pathlib import Path

from src.auto_click import parse_click_delay_range, run_auto_click
from src.combat import run_combat_bot
from src.core.calibration import calibrate_click_position, calibrate_hp_templates
from src.core.config import DEFAULT_CONFIG_PATH, load_config
from src.core.hp import ensure_hp_templates_ready, run_hp_monitor
from src.fletching import run_fletching_bot
from src.magic import run_magic_bot


def build_parser():
    """Build the top-level CLI parser with subcommands."""
    parser = argparse.ArgumentParser(prog="osrs-bot")
    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the JSON config file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("combat", parents=[config_parent], help="Run the combat bot.")
    subparsers.add_parser("fletching", parents=[config_parent], help="Run the fletching bot.")
    subparsers.add_parser("magic", parents=[config_parent], help="Run the magic enchant bot.")
    subparsers.add_parser("hp", parents=[config_parent], help="Only print the calibrated current HP result.")
    subparsers.add_parser(
        "calibrate-hp",
        parents=[config_parent],
        help="Capture digit templates for the current RuneLite layout.",
    )
    calibrate_click_parser = subparsers.add_parser(
        "calibrate-click",
        parents=[config_parent],
        help="Capture the current mouse position as RuneLite-relative ratios.",
    )
    calibrate_click_parser.add_argument(
        "target",
        choices=["magic.click", "fletching.first_click", "fletching.second_click"],
        help="Config target to calibrate.",
    )
    auto_click_parser = subparsers.add_parser("auto-click", help="Run the standalone auto-click loop.")
    auto_click_parser.add_argument(
        "delay_range",
        nargs="?",
        help="Optional click delay range formatted as 'min-max', for example '1-2'.",
    )
    return parser


def load_runtime_config(config_path_raw):
    """Load config and return both the merged config and its directory."""
    config_path = Path(config_path_raw).expanduser().resolve()
    config = load_config(config_path)
    return config, config_path.parent


def run(argv=None):
    """CLI entrypoint for loading config and dispatching subcommands."""
    try:
        args = build_parser().parse_args(argv)

        if args.command == "auto-click":
            delay_range = parse_click_delay_range(args.delay_range)
            return run_auto_click(delay_range=delay_range)

        config, config_dir = load_runtime_config(args.config)

        if args.command == "calibrate-hp":
            calibrate_hp_templates(config, config_dir)
            return 0

        if args.command == "calibrate-click":
            calibrate_click_position(config, config_path=Path(args.config).expanduser().resolve(), target_label=args.target)
            return 0

        if args.command == "fletching":
            run_fletching_bot(config)
            return 0

        if args.command == "magic":
            run_magic_bot(config)
            return 0

        templates = ensure_hp_templates_ready(config, config_dir)
        if args.command == "hp":
            run_hp_monitor(config, config_dir, templates)
            return 0

        if args.command == "combat":
            run_combat_bot(config, config_dir, templates)
            return 0

        raise ValueError(f"Unsupported command: {args.command}")
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping.")
        return 1
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(exc)
        return 1


def main():
    raise SystemExit(run())


def combat_entry():
    raise SystemExit(run(["combat", *sys.argv[1:]]))


def fletching_entry():
    raise SystemExit(run(["fletching", *sys.argv[1:]]))


def hp_entry():
    raise SystemExit(run(["hp", *sys.argv[1:]]))


def calibrate_hp_entry():
    raise SystemExit(run(["calibrate-hp", *sys.argv[1:]]))


def magic_entry():
    raise SystemExit(run(["magic", *sys.argv[1:]]))


def calibrate_click_entry():
    raise SystemExit(run(["calibrate-click", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
