"""
Interactive test menu for the Lake Shore 350 - quick bench checks without
writing a one-off script each time.

Opens a single connection and keeps it open across menu selections (faster
than reconnecting per command). Read-only by design: no setpoints or heater
ranges are changed here. Use configure_channel.py to edit input configuration.

Example:
    python interactive_menu.py
    python interactive_menu.py --ip 192.168.1.50
"""

import argparse
import os
import sys

from labconfig import add_common_args, resolve_args

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lakeshore350 import LakeShore350, LakeShore350Error  # noqa: E402


MENU = """
===== Lake Shore 350 - Test Menu =====
1) Show instrument ID
2) Read temperature from one channel
3) Read all channels
4) Show input configuration
5) Show control loop status (setpoint, range, output %)
0) Exit
=======================================
"""


def ask_channel():
    while True:
        ch = input("Select channel (A/B/C/D): ").strip().upper()
        if ch in LakeShore350.CHANNELS:
            return ch
        print("Invalid channel.")


def ask_loop():
    while True:
        raw = input("Select loop (1/2): ").strip()
        if raw in ("1", "2"):
            return int(raw)
        print("Invalid loop.")


def main():
    parser = argparse.ArgumentParser(description="Interactive test menu for the Lake Shore 350.")
    add_common_args(parser)
    args = parser.parse_args()
    settings, _ = resolve_args(args)

    try:
        ls = LakeShore350(settings["ip"], port=settings["port"], timeout=settings["timeout"])
    except LakeShore350Error as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    with ls:
        while True:
            print(MENU)
            choice = input("Select option: ").strip()

            if choice == "1":
                print(f"\nInstrument ID: {ls.get_idn()}")

            elif choice == "2":
                ch = ask_channel()
                try:
                    print(f"Channel {ch}: {ls.read_temperature_K(ch):.3f} K")
                except LakeShore350Error as e:
                    print(f"Error reading channel {ch}: {e}")

            elif choice == "3":
                try:
                    for ch, val in ls.read_all_channels(unit="K").items():
                        print(f"  {ch}: {val:.3f} K")
                except LakeShore350Error as e:
                    print(f"Error reading channels: {e}")

            elif choice == "4":
                ch = ask_channel()
                try:
                    for k, v in ls.get_input_config(ch).items():
                        print(f"  {k}: {v}")
                except LakeShore350Error as e:
                    print(f"Error reading configuration: {e}")

            elif choice == "5":
                loop = ask_loop()
                try:
                    print(f"  Setpoint      : {ls.get_setpoint(loop)}")
                    print(f"  Heater range  : {ls.get_heater_range(loop)}")
                    print(f"  Heater output : {ls.read_heater_output(loop)} %")
                    print(f"  Output mode   : {ls.get_output_mode(loop)}")
                except LakeShore350Error as e:
                    print(f"Error reading control loop: {e}")

            elif choice == "0":
                print("Exiting...")
                break

            else:
                print("Invalid option.")

    print("Disconnected from Lake Shore 350.")


if __name__ == "__main__":
    main()
