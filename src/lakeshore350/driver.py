"""
(C) 2025 by PatrickADz.
Lake Shore Model 350 Temperature Controller driver.

Communicates with the instrument over TCP/IP using Lake Shore commands
and IEEE-488.2 common commands.

Transport : TCP/IP socket
Port      : 7777 (factory default)
Terminator: \\n

Version 1.2 July 2026
"""

import logging
import socket
import time

from .exceptions import LakeShore350Error

logger = logging.getLogger(__name__)


class LakeShore350:
    """Driver for the Lake Shore Model 350 Temperature Controller."""

    SENSOR_TYPE_MAP = {
        0: "Disabled",
        1: "Diode",
        2: "Thermocouple",
        3: "RTD",
        4: "Thermistor",
        5: "Capacitance",
    }
    SENSOR_TYPE_REVERSE_MAP = {v: k for k, v in SENSOR_TYPE_MAP.items()}

    UNIT_MAP = {0: "K", 1: "C", 2: "F"}
    UNIT_REVERSE_MAP = {v: k for k, v in UNIT_MAP.items()}

    CHANNELS = ("A", "B", "C", "D")
    LOOPS = (1, 2)

    OUTMODE_MAP = {
        0: "Off",
        1: "Closed Loop PID",
        2: "Zone",
        3: "Open Loop",
        4: "Monitor Out",
        5: "Warmup Supply",
    }
    OUTMODE_REVERSE_MAP = {v: k for k, v in OUTMODE_MAP.items()}

    def __init__(self, ip, port=7777, timeout=5):
        if not ip:
            raise ValueError("Invalid IP address")

        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None

        self.connect()

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        try:
            logger.info("Connecting to Lake Shore 350 @ %s:%s", self.ip, self.port)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
        except OSError as e:
            raise LakeShore350Error(f"Connection failed: {e}") from e

        idn = self.get_idn()
        logger.info("Connection established: %s", idn)

    def disconnect(self):
        if self.sock:
            logger.info("Closing connection with Lake Shore 350")
            self.sock.close()
            self.sock = None

    def is_connected(self):
        """Returns True if the socket is open and the instrument responds to *IDN?."""
        if self.sock is None:
            return False
        try:
            self.get_idn()
            return True
        except LakeShore350Error:
            return False

    # ------------------------------------------------------------------
    # Low level I/O
    # ------------------------------------------------------------------
    def _write(self, command):
        try:
            self.sock.sendall((command + "\n").encode())
        except OSError as e:
            raise LakeShore350Error(f"Write failed ({command!r}): {e}") from e

    def _read(self):
        try:
            data = self.sock.recv(1024).decode().strip()
        except OSError as e:
            raise LakeShore350Error(f"Read failed: {e}") from e
        if not data:
            raise LakeShore350Error("Empty response from instrument (connection may be closed)")
        return data

    def _query(self, command):
        self._write(command)
        return self._read()

    def get_idn(self):
        """Returns the instrument identification string (*IDN?)."""
        return self._query("*IDN?")

    def reset(self):
        """IEEE-488.2 reset."""
        self._write("*RST")
        time.sleep(0.2)

    # ------------------------------------------------------------------
    # Temperature readings
    # ------------------------------------------------------------------
    def read_temperature_K(self, channel):
        """Reads temperature in Kelvin from the given channel (A-D)."""
        self._validate_channel(channel)
        return float(self._query(f"KRDG? {channel}"))

    def read_temperature_C(self, channel):
        """Reads temperature in Celsius from the given channel (A-D)."""
        self._validate_channel(channel)
        return float(self._query(f"CRDG? {channel}"))

    def read_all_channels(self, unit="K"):
        """Returns a dict {channel: reading} for all channels, in the given unit (K or C)."""
        cmd = "KRDG?" if unit.upper() == "K" else "CRDG?"
        return {ch: float(self._query(f"{cmd} {ch}")) for ch in self.CHANNELS}

    def sensor_status(self, channel):
        """Returns sensor status code: 0=OK, 1=Open, 2=Short."""
        self._validate_channel(channel)
        return int(self._query(f"RDGST? {channel}"))

    # ------------------------------------------------------------------
    # Input configuration - read
    # ------------------------------------------------------------------
    def get_input_config(self, channel):
        """
        Reads the full configuration of an input channel (A-D).

        Returns a dict with: sensor_type, range, curve, filter, input_name,
        temperature_limit, preferred_unit.
        """
        self._validate_channel(channel)

        intype = [int(x) for x in self._query(f"INTYPE? {channel}").split(",")]
        sensor_type_code, range_code, unit_code = intype[0], intype[2], intype[3]

        curve = int(self._query(f"INCRV? {channel}"))

        filter_parts = self._query(f"FILTER? {channel}").split(",")
        filter_cfg = {
            "enabled": bool(int(filter_parts[0])),
            "points": int(filter_parts[1]),
            "window": float(filter_parts[2]),
        }

        input_name = self._query(f"INNAME? {channel}")
        temp_limit = float(self._query(f"TLIMIT? {channel}"))

        return {
            "channel": channel,
            "sensor_type": self.SENSOR_TYPE_MAP.get(sensor_type_code, "Unknown"),
            "range": range_code,
            "curve": curve,
            "filter": filter_cfg,
            "input_name": input_name,
            "temperature_limit": temp_limit,
            "preferred_unit": self.UNIT_MAP.get(unit_code, "Unknown"),
        }

    # ------------------------------------------------------------------
    # Input configuration - write
    # ------------------------------------------------------------------
    def set_input_type(self, channel, sensor_type, range_code, unit="K"):
        self._validate_channel(channel)
        sensor_code = self._normalize_sensor_type(sensor_type)
        unit_code = self._normalize_unit(unit)
        self._write(f"INTYPE {channel},{sensor_code},0,{int(range_code)},{unit_code}")

    def set_input_curve(self, channel, curve):
        self._validate_channel(channel)
        self._write(f"INCRV {channel},{int(curve)}")

    def set_filter(self, channel, enabled, points, window):
        self._validate_channel(channel)
        flag = 1 if enabled else 0
        self._write(f"FILTER {channel},{flag},{int(points)},{float(window)}")

    def set_input_name(self, channel, name):
        self._validate_channel(channel)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Input name must be a non-empty string")
        self._write(f"INNAME {channel},{name.strip()}")

    def set_temperature_limit(self, channel, temp_limit):
        self._validate_channel(channel)
        self._write(f"TLIMIT {channel},{float(temp_limit)}")

    def set_input_config(
        self,
        channel,
        sensor_type=None,
        range_code=None,
        curve=None,
        filter_enabled=None,
        filter_points=None,
        filter_window=None,
        input_name=None,
        temperature_limit=None,
        preferred_unit=None,
    ):
        """Sets one or more input channel parameters. Unset parameters are left untouched."""
        self._validate_channel(channel)

        config = None
        if any(v is None for v in (sensor_type, range_code, preferred_unit)):
            config = self.get_input_config(channel)
            sensor_type = sensor_type or config["sensor_type"]
            range_code = range_code if range_code is not None else config["range"]
            preferred_unit = preferred_unit or config["preferred_unit"]

        self.set_input_type(channel, sensor_type, range_code, preferred_unit)

        if curve is not None:
            self.set_input_curve(channel, curve)

        if filter_enabled is not None or filter_points is not None or filter_window is not None:
            config = config or self.get_input_config(channel)
            filter_enabled = config["filter"]["enabled"] if filter_enabled is None else filter_enabled
            filter_points = config["filter"]["points"] if filter_points is None else filter_points
            filter_window = config["filter"]["window"] if filter_window is None else filter_window
            self.set_filter(channel, filter_enabled, filter_points, filter_window)

        if input_name is not None:
            self.set_input_name(channel, input_name)

        if temperature_limit is not None:
            self.set_temperature_limit(channel, temperature_limit)

        return self.get_input_config(channel)

    def copy_input_config(self, source_channel, target_channel):
        """Copies the full input configuration from one channel to another."""
        self._validate_channel(source_channel)
        self._validate_channel(target_channel)
        if source_channel == target_channel:
            raise ValueError("Source and target channels must be different")

        src = self.get_input_config(source_channel)
        return self.set_input_config(
            target_channel,
            sensor_type=src["sensor_type"],
            range_code=src["range"],
            curve=src["curve"],
            filter_enabled=src["filter"]["enabled"],
            filter_points=src["filter"]["points"],
            filter_window=src["filter"]["window"],
            input_name=src["input_name"],
            temperature_limit=src["temperature_limit"],
            preferred_unit=src["preferred_unit"],
        )

    # ------------------------------------------------------------------
    # Heater / control loop configuration (Model 350 as a controller,
    # not just a monitor). Loop is 1 or 2.
    #
    # NOTE: These commands act on real hardware and can drive a heater.
    # Always check get_setpoint()/get_heater_range() before changing
    # anything, and never set a setpoint above the input channel's
    # configured temperature_limit.
    # ------------------------------------------------------------------
    def get_setpoint(self, loop):
        """Reads the control setpoint of the given loop (1 or 2), in the loop's configured unit."""
        self._validate_loop(loop)
        return float(self._query(f"SETP? {loop}"))

    def set_setpoint(self, loop, value):
        """Sets the control setpoint of the given loop (1 or 2)."""
        self._validate_loop(loop)
        self._write(f"SETP {loop},{float(value)}")

    def get_heater_range(self, loop):
        """Reads the heater range of the given loop. 0 = off; 1-5 = increasing power ranges."""
        self._validate_loop(loop)
        return int(self._query(f"RANGE? {loop}"))

    def set_heater_range(self, loop, range_code):
        """
        Sets the heater range of the given loop. 0 = off (always safe).
        Valid non-zero range codes depend on the loop (loop 1 typically
        supports 1-5, loop 2 depends on installed output option) - check
        the Model 350 manual before selecting anything above 0.
        """
        self._validate_loop(loop)
        self._write(f"RANGE {loop},{int(range_code)}")

    def get_pid(self, loop):
        """Returns a dict with the P, I, D parameters currently set for the given loop."""
        self._validate_loop(loop)
        p, i, d = (float(x) for x in self._query(f"PID? {loop}").split(","))
        return {"P": p, "I": i, "D": d}

    def set_pid(self, loop, p, i, d):
        """Sets the P, I, D parameters for the given loop."""
        self._validate_loop(loop)
        self._write(f"PID {loop},{float(p)},{float(i)},{float(d)}")

    def get_output_mode(self, loop):
        """Returns a dict with mode, input_channel and powerup_enable for the given loop."""
        self._validate_loop(loop)
        mode_code, input_channel, powerup = self._query(f"OUTMODE? {loop}").split(",")
        return {
            "mode": self.OUTMODE_MAP.get(int(mode_code), "Unknown"),
            "input_channel": input_channel,
            "powerup_enable": bool(int(powerup)),
        }

    def set_output_mode(self, loop, mode, input_channel, powerup_enable=False):
        """
        Configures the given loop: control mode (see OUTMODE_MAP), which
        input channel (A-D) feeds it, and whether it resumes on power-up.
        """
        self._validate_loop(loop)
        self._validate_channel(input_channel)
        mode_code = self._normalize_outmode(mode)
        flag = 1 if powerup_enable else 0
        self._write(f"OUTMODE {loop},{mode_code},{input_channel},{flag}")

    def get_ramp(self, loop):
        """Returns a dict with ramp 'enabled' and 'rate' (K/min) for the given loop."""
        self._validate_loop(loop)
        enabled, rate = self._query(f"RAMP? {loop}").split(",")
        return {"enabled": bool(int(enabled)), "rate": float(rate)}

    def set_ramp(self, loop, enabled, rate):
        """Enables/disables setpoint ramping for the given loop, at `rate` K/min."""
        self._validate_loop(loop)
        flag = 1 if enabled else 0
        self._write(f"RAMP {loop},{flag},{float(rate)}")

    def read_heater_output(self, loop):
        """Reads the current heater output of the given loop, in percent of range."""
        self._validate_loop(loop)
        return float(self._query(f"HTR? {loop}"))

    def read_heater_status(self, loop):
        """
        Reads the heater error status of the given loop:
        0 = no error, 1 = open loop, 2 = short.
        """
        self._validate_loop(loop)
        return int(self._query(f"HTRST? {loop}"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _normalize_sensor_type(self, sensor_type):
        if isinstance(sensor_type, int):
            if sensor_type not in self.SENSOR_TYPE_MAP:
                raise ValueError("Invalid sensor type code")
            return sensor_type
        if isinstance(sensor_type, str):
            sensor_type = sensor_type.strip()
            if sensor_type.isdigit():
                return int(sensor_type)
            if sensor_type not in self.SENSOR_TYPE_REVERSE_MAP:
                raise ValueError("Invalid sensor type name")
            return self.SENSOR_TYPE_REVERSE_MAP[sensor_type]
        raise ValueError("Sensor type must be an int or a valid string")

    def _normalize_unit(self, unit):
        if isinstance(unit, int):
            if unit not in self.UNIT_MAP:
                raise ValueError("Invalid unit code")
            return unit
        if isinstance(unit, str):
            unit = unit.strip().upper()
            if unit.isdigit():
                unit_code = int(unit)
                if unit_code not in self.UNIT_MAP:
                    raise ValueError("Invalid unit code")
                return unit_code
            if unit not in self.UNIT_REVERSE_MAP:
                raise ValueError("Invalid unit")
            return self.UNIT_REVERSE_MAP[unit]
        raise ValueError("Unit must be an int or string")

    def _normalize_outmode(self, mode):
        if isinstance(mode, int):
            if mode not in self.OUTMODE_MAP:
                raise ValueError("Invalid output mode code")
            return mode
        if isinstance(mode, str):
            mode = mode.strip()
            if mode.isdigit():
                return int(mode)
            if mode not in self.OUTMODE_REVERSE_MAP:
                raise ValueError("Invalid output mode name")
            return self.OUTMODE_REVERSE_MAP[mode]
        raise ValueError("Output mode must be an int or a valid string")

    @classmethod
    def _validate_channel(cls, channel):
        if channel not in cls.CHANNELS:
            raise ValueError(f"Invalid channel {channel!r}. Use one of {cls.CHANNELS}.")

    @classmethod
    def _validate_loop(cls, loop):
        if loop not in cls.LOOPS:
            raise ValueError(f"Invalid loop {loop!r}. Use one of {cls.LOOPS}.")
