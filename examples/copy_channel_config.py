"""
Copies the full input configuration from one channel to another.

Example:
    python copy_channel_config.py A D
    python copy_channel_config.py A D --ip 192.168.1.50
"""

import argparse
import os
import sys

from labconfig import add_common_args, resolve_args

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lakeshore350 import LakeShore350, LakeShore350Error  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Copy Lake Shore 350 channel configuration.")
    parser.add_argument("source", choices=["A", "B", "C", "D"], help="Source channel")
    parser.add_argument("target", choices=["A", "B", "C", "D"], help="Target channel")
    add_common_args(parser)
    args = parser.parse_args()

    settings, _ = resolve_args(args)

    try:
        ls = LakeShore350(settings["ip"], port=settings["port"], timeout=settings["timeout"])
    except LakeShore350Error as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    with ls:
        print(f"Copying channel {args.source} configuration to channel {args.target}...")
        new_cfg = ls.copy_input_config(args.source, args.target)
        print(f"\nNew configuration for channel {args.target}:")
        for key, value in new_cfg.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
