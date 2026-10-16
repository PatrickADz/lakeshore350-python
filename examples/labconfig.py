"""
Shared config-loading helper for the example scripts.

Resolution order for every setting: CLI argument > config.ini > built-in
default.
"""

import configparser
import os

DEFAULTS = {
    "ip": "192.168.1.100",
    "port": 7777,
    "timeout": 5,
    "unit": "K",
    "sample_period": 1.0,
    "channels": "A,B,C,D",
    "output_dir": "./data",
    "plot": True,
    "save": True,
}

CHANNEL_NAME_DEFAULTS = {"A": "Sensor A", "B": "Sensor B", "C": "Sensor C", "D": "Sensor D"}


def load_config(path="config.ini"):
    """
    Reads config.ini if present and returns a flat dict of settings plus a
    separate dict of channel display names. Missing file or missing keys
    silently fall back to DEFAULTS, so the scripts always run out of the box.
    """
    settings = dict(DEFAULTS)
    channel_names = dict(CHANNEL_NAME_DEFAULTS)

    if os.path.exists(path):
        parser = configparser.ConfigParser()
        parser.read(path)

        if parser.has_section("instrument"):
            settings["ip"] = parser.get("instrument", "ip", fallback=settings["ip"])
            settings["port"] = parser.getint("instrument", "port", fallback=settings["port"])
            settings["timeout"] = parser.getint("instrument", "timeout", fallback=settings["timeout"])

        if parser.has_section("acquisition"):
            settings["unit"] = parser.get("acquisition", "unit", fallback=settings["unit"])
            settings["sample_period"] = parser.getfloat(
                "acquisition", "sample_period", fallback=settings["sample_period"]
            )
            settings["channels"] = parser.get("acquisition", "channels", fallback=settings["channels"])

        if parser.has_section("output"):
            settings["output_dir"] = parser.get("output", "output_dir", fallback=settings["output_dir"])
            settings["plot"] = parser.getboolean("output", "plot", fallback=settings["plot"])
            settings["save"] = parser.getboolean("output", "save", fallback=settings["save"])

        if parser.has_section("channel_names"):
            for ch in ("A", "B", "C", "D"):
                channel_names[ch] = parser.get("channel_names", ch, fallback=channel_names[ch])

    return settings, channel_names


def add_common_args(parser):
    """Adds the standard set of overridable CLI arguments to an argparse parser."""
    parser.add_argument("--config", default="config.ini", help="Path to config.ini (default: %(default)s)")
    parser.add_argument("--ip", help="Instrument IP address (overrides config.ini)")
    parser.add_argument("--port", type=int, help="TCP port (default from config.ini or 7777)")
    parser.add_argument("--unit", choices=["K", "C"], help="Temperature unit")
    parser.add_argument("--channels", help="Comma-separated channel list, e.g. A,B,C,D")
    parser.add_argument("--sample-period", type=float, help="Seconds between samples")
    parser.add_argument("--output-dir", help="Folder to save CSV/PNG output")
    plot_group = parser.add_mutually_exclusive_group()
    plot_group.add_argument("--plot", dest="plot", action="store_true", default=None, help="Show live plot")
    plot_group.add_argument("--no-plot", dest="plot", action="store_false", help="Disable live plot")
    save_group = parser.add_mutually_exclusive_group()
    save_group.add_argument("--save", dest="save", action="store_true", default=None, help="Save CSV log (default: on)")
    save_group.add_argument("--no-save", dest="save", action="store_false", help="Don't save CSV log")
    return parser


def resolve_args(args, path_override=None):
    """Merges parsed CLI args on top of config.ini + defaults."""
    settings, channel_names = load_config(path_override or args.config)

    if args.ip is not None:
        settings["ip"] = args.ip
    if args.port is not None:
        settings["port"] = args.port
    if args.unit is not None:
        settings["unit"] = args.unit
    if args.channels is not None:
        settings["channels"] = args.channels
    if args.sample_period is not None:
        settings["sample_period"] = args.sample_period
    if args.output_dir is not None:
        settings["output_dir"] = args.output_dir
    if args.plot is not None:
        settings["plot"] = args.plot
    if args.save is not None:
        settings["save"] = args.save

    settings["channels"] = [c.strip().upper() for c in settings["channels"].split(",") if c.strip()]
    return settings, channel_names
