# lakeshore350-python

Python driver for the Lake Shore Model 350 Temperature Controller, communicating over TCP/IP.

Developed for laboratory cryogenic instrumentation work (heterodyne receiver testing, cryostat monitoring), where reliable remote control and data acquisition from Python is needed for integration into larger acquisition/control systems.

## Features

- Read temperature (K) from any input channel (A-D)
- Read/write full input channel configuration (sensor type, curve, filter, name, temperature limit)
- Copy configuration between channels
- Heater/control loop support (setpoint, heater range, PID, output mode, ramp, heater output/status)
- Example scripts: live monitor with selectable channels and optional CSV logging + plotting, interactive test menu, channel config editor

## Installation

```bash
git clone https://github.com/PatrickADz/lakeshore350-python.git
cd lakeshore350-python
pip install -e .

# optional, only needed for the plotting example
pip install -e ".[plot]"
```

## Quick start

```python
from lakeshore350 import LakeShore350

with LakeShore350("192.168.1.100") as ls:
    print(ls.get_idn())
    print(ls.read_temperature_K("A"))
    print(ls.get_input_config("A"))
```

## Example scripts

The `examples/` folder contains ready-to-run scripts. Configuration for all of
them is resolved as: **CLI argument > `config.ini` > built-in default** — set
`config.ini` up once for your routine lab setup, then override anything ad
hoc from the command line.

```bash
cd examples
cp ../config.example.ini config.ini
# edit config.ini: set your instrument's real IP, preferred unit, channel names, etc.
```

**Live monitor** (CSV log + optional live plot):

```bash
python live_monitor.py                              # uses config.ini
python live_monitor.py --ip 192.168.1.50 --no-plot   # override IP, headless
python live_monitor.py --channels A,B --unit C        # override channels/unit
python live_monitor.py --no-save                      # monitor live, don't write CSV
python live_monitor.py --help                         # see all options
```

CSV logging is on by default (`--no-save` to disable) and independent from
plotting (`--plot`/`--no-plot`) - so you can log headlessly, plot without
saving, or both.

**Interactive test menu** (quick bench checks - ID, single/all channel reads,
input config, control loop status):

```bash
python interactive_menu.py
```

**Copy channel configuration:**

```bash
python copy_channel_config.py A D
python copy_channel_config.py A D --ip 192.168.1.50
```

**Interactively view/edit a channel configuration:**

```bash
python configure_channel.py A
python configure_channel.py            # prompts for the channel
```

Shows the current sensor type, range, curve, filter, name and temperature
limit, lets you pick which fields to change and shows valid options for each,
then asks for confirmation before applying.

> `config.ini` is gitignored — only `config.example.ini` is tracked, so your
> real instrument IP never ends up in version control.

## Running tests

Tests use a mocked socket, so no physical instrument is required:

```bash
pip install -e .
python tests/test_driver.py
```

## Repository structure

```
lakeshore350-python/
├── src/lakeshore350/       # the driver (importable package)
│   ├── driver.py
│   └── exceptions.py
├── examples/               # runnable example scripts
│   ├── labconfig.py        # config.ini + argparse merging helper
│   ├── live_monitor.py
│   ├── interactive_menu.py
│   ├── copy_channel_config.py
│   └── configure_channel.py
├── tests/
│   └── test_driver.py
├── config.example.ini
├── CHANGELOG.md
└── pyproject.toml
```

## Notes

- Tested against firmware used at CePIA for cryostat and receiver temperature monitoring.
- Not affiliated with or endorsed by Lake Shore Cryotronics, Inc. "LakeShore" and "Model 350" are used here only to describe compatibility.

## License

MIT — see [LICENSE](LICENSE).
