"""
Live temperature monitor for the Lake Shore 350.

Reads the selected channels at a fixed sample period, writes a timestamped
CSV log, and (optionally) shows a live plot. On exit, saves a PNG snapshot
of the plot.

Configuration is resolved as: CLI args > config.ini > built-in defaults.
See config.example.ini for all available settings.

Examples
--------
Run with everything from config.ini:
    python live_monitor.py

Override just the IP and disable the plot (e.g. for a headless logging run):
    python live_monitor.py --ip 192.168.1.50 --no-plot

Monitor live without writing any CSV file:
    python live_monitor.py --no-save

Use a different config file, only channels A and B, Celsius:
    python live_monitor.py --config my_cryostat.ini --channels A,B --unit C
"""

import argparse
import csv
import os
import sys
from datetime import datetime

from labconfig import add_common_args, resolve_args

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lakeshore350_driver import LakeShore350  # noqa: E402
from exceptions import LakeShore350Error  # noqa: E402


class NullWriter:
    """Drop-in replacement for csv.writer when --no-save is used."""

    def writerow(self, row):
        pass


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Live temperature monitor for the Lake Shore 350.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_args(parser)
    return parser


def main():
    args = build_arg_parser().parse_args()
    settings, channel_names = resolve_args(args)
    channels = settings["channels"]

    try:
        ls = LakeShore350(settings["ip"], port=settings["port"], timeout=settings["timeout"])
    except LakeShore350Error as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    with ls:
        idn = ls.get_idn()
        print(f"Connected: {idn}")

        configs = {ch: ls.get_input_config(ch) for ch in channels}
        for ch in channels:
            print(f"  Channel {ch} ({channel_names.get(ch, ch)}): {configs[ch]['sensor_type']}")

        if settings["save"]:
            os.makedirs(settings["output_dir"], exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(settings["output_dir"], f"ls350_log_{stamp}.csv")
            png_path = csv_path.replace(".csv", ".png")
            f = open(csv_path, "w", newline="")
            writer = csv.writer(f)
            f.write("# Lake Shore 350 data log\n")
            f.write(f"# Start time: {datetime.now()}\n")
            f.write(f"# Instrument ID: {idn}\n")
            for ch in channels:
                f.write(f"# Channel {ch} ({channel_names.get(ch, ch)}): {configs[ch]}\n")
            writer.writerow(
                ["timestamp"] + [f"Sensor_{ch}_{settings['unit']}" for ch in channels] + [f"status_{ch}" for ch in channels]
            )
            f.flush()
        else:
            f, writer, csv_path, png_path = None, NullWriter(), None, None
            print("CSV logging disabled (--no-save). Nothing will be written to disk.")

        times, temps = [], {ch: [] for ch in channels}

        try:
            if settings["plot"]:
                _run_with_plot(ls, channels, channel_names, settings, writer, f, times, temps, png_path)
            else:
                _run_headless(ls, channels, settings, writer, f)
        finally:
            if f is not None:
                f.close()

    if settings["save"]:
        print(f"CSV saved to: {csv_path}")
        if settings["plot"]:
            print(f"Plot saved to: {png_path}")


def _read_row(ls, channels, unit):
    now = datetime.now()
    readings, statuses = [], []
    for ch in channels:
        try:
            value = ls.read_temperature_K(ch) if unit == "K" else ls.read_temperature_C(ch)
            status = ls.sensor_status(ch)
        except LakeShore350Error as e:
            print(f"Read error on channel {ch}: {e}")
            value, status = float("nan"), -1
        readings.append(value)
        statuses.append(status)
    return now, readings, statuses


def _run_headless(ls, channels, settings, writer, f):
    import time

    print("Logging (headless, Ctrl+C to stop)...")
    try:
        while True:
            now, readings, statuses = _read_row(ls, channels, settings["unit"])
            writer.writerow([now.isoformat(timespec="milliseconds")] + readings + statuses)
            if f is not None:
                f.flush()
            time.sleep(settings["sample_period"])
    except KeyboardInterrupt:
        print("\nStopped by user.")


def _run_with_plot(ls, channels, channel_names, settings, writer, f, times, temps, png_path):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.animation import FuncAnimation

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.suptitle("Lake Shore 350 - Live Monitor", fontweight="bold")
    lines = {ch: ax.plot([], [], label=f"{ch}: {channel_names.get(ch, ch)}")[0] for ch in channels}
    ax.set_xlabel("Time")
    ax.set_ylabel(f"Temperature ({settings['unit']})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    values_text = ax.text(
        0.98, 0.97,
        "",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9),
        family="monospace",
    )

    def update(_frame):
        now, readings, statuses = _read_row(ls, channels, settings["unit"])
        times.append(now)
        for ch, val in zip(channels, readings):
            temps[ch].append(val)
        writer.writerow([now.isoformat(timespec="milliseconds")] + readings + statuses)
        if f is not None:
            f.flush()

        for ch in channels:
            lines[ch].set_data(times, temps[ch])
        ax.relim()
        ax.autoscale_view()
        fig.autofmt_xdate(rotation=30, ha="right")

        values_str = "\n".join(
            f"{ch}: {val:8.3f} {settings['unit']}" if val == val else f"{ch}: {'N/A':>8}"
            for ch, val in zip(channels, readings)
        )
        values_text.set_text(values_str)

        return list(lines.values()) + [values_text]

    ani = FuncAnimation(fig, update, interval=int(settings["sample_period"] * 1000), blit=False)  # noqa: F841

    def on_close(_event):
        if png_path is not None:
            fig.savefig(png_path, dpi=150, bbox_inches="tight")

    fig.canvas.mpl_connect("close_event", on_close)
    print("Close the plot window to stop and save.")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
