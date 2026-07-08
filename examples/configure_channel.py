"""
Interactive channel configuration tool for the Lake Shore 350.

Reads the current configuration of a channel, shows which fields can be
changed and their valid options, and lets you edit one or more fields
before applying them.

Example:
    python configure_channel.py A
    python configure_channel.py A --ip 192.168.1.50
    python configure_channel.py            # will prompt for the channel
"""

import argparse
import os
import sys

from labconfig import add_common_args, resolve_args

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lakeshore350 import LakeShore350, LakeShore350Error  # noqa: E402


def ask_channel():
    while True:
        ch = input("Channel to configure (A/B/C/D): ").strip().upper()
        if ch in LakeShore350.CHANNELS:
            return ch
        print("Invalid channel, try again.")


def print_config(cfg):
    print(f"\nCurrent configuration - Channel {cfg['channel']}")
    print("-" * 40)
    print(f"  1) Sensor type       : {cfg['sensor_type']}")
    print(f"  2) Range code        : {cfg['range']}")
    print(f"  3) Preferred unit    : {cfg['preferred_unit']}")
    print(f"  4) Curve number      : {cfg['curve']}")
    print(f"  5) Filter enabled    : {cfg['filter']['enabled']}")
    print(f"  6) Filter points     : {cfg['filter']['points']}")
    print(f"  7) Filter window (s) : {cfg['filter']['window']}")
    print(f"  8) Input name        : {cfg['input_name']}")
    print(f"  9) Temperature limit : {cfg['temperature_limit']} K")
    print("-" * 40)


def ask_int(prompt, valid=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if valid is not None and value not in valid:
            print(f"Please enter one of: {sorted(valid)}")
            continue
        return value


def ask_float(prompt):
    while True:
        raw = input(prompt).strip()
        try:
            return float(raw)
        except ValueError:
            print("Please enter a number.")


def ask_yes_no(prompt):
    while True:
        raw = input(prompt + " [y/n]: ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer y or n.")


def edit_field(field_num, cfg, updates):
    if field_num == 1:
        print("Sensor types:", ", ".join(f"{k}={v}" for k, v in LakeShore350.SENSOR_TYPE_MAP.items()))
        updates["sensor_type"] = ask_int("New sensor type code: ", valid=LakeShore350.SENSOR_TYPE_MAP)
    elif field_num == 2:
        print("Range code meaning depends on the sensor type - see the Model 350 manual, table 5-6/5-7.")
        updates["range_code"] = ask_int("New range code: ")
    elif field_num == 3:
        print("Units:", ", ".join(f"{k}={v}" for k, v in LakeShore350.UNIT_MAP.items()))
        code = ask_int("New unit code: ", valid=LakeShore350.UNIT_MAP)
        updates["preferred_unit"] = LakeShore350.UNIT_MAP[code]
    elif field_num == 4:
        updates["curve"] = ask_int("New curve number (0 = none, or curve index, see CRVHDR?): ")
    elif field_num == 5:
        updates["filter_enabled"] = ask_yes_no("Enable filter?")
    elif field_num == 6:
        updates["filter_points"] = ask_int("Number of filter points (2-64): ", valid=range(2, 65))
    elif field_num == 7:
        updates["filter_window"] = ask_float("Filter window, % of full scale (1-10): ")
    elif field_num == 8:
        updates["input_name"] = input("New input name (max 15 chars): ").strip()[:15]
    elif field_num == 9:
        updates["temperature_limit"] = ask_float("New temperature limit, 0 = no limit (K): ")
    else:
        print("Not a valid option.")


def main():
    parser = argparse.ArgumentParser(
        description="Interactively view and edit a Lake Shore 350 input channel configuration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("channel", nargs="?", choices=list(LakeShore350.CHANNELS), help="Channel to configure")
    add_common_args(parser)
    args = parser.parse_args()

    settings, _ = resolve_args(args)

    try:
        ls = LakeShore350(settings["ip"], port=settings["port"], timeout=settings["timeout"])
    except LakeShore350Error as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    with ls:
        print(f"Connected: {ls.get_idn()}")
        channel = args.channel or ask_channel()

        cfg = ls.get_input_config(channel)
        print_config(cfg)

        updates = {}
        while True:
            raw = input(
                "\nEnter field number(s) to change (comma-separated), "
                "'r' to refresh view, or Enter to finish: "
            ).strip()
            if raw == "":
                break
            if raw.lower() == "r":
                print_config(ls.get_input_config(channel))
                continue
            try:
                fields = [int(x) for x in raw.split(",")]
            except ValueError:
                print("Please enter numbers separated by commas (e.g. 4,9).")
                continue
            for f in fields:
                edit_field(f, cfg, updates)

        if not updates:
            print("No changes made.")
            return

        print("\nPending changes:")
        for k, v in updates.items():
            print(f"  {k}: {v}")
        if not ask_yes_no("Apply these changes?"):
            print("Cancelled, no changes applied.")
            return

        new_cfg = ls.set_input_config(channel, **updates)
        print_config(new_cfg)
        print("Changes applied.")


if __name__ == "__main__":
    main()
