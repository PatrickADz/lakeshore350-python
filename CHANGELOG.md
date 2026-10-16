# Changelog

## v1.2.0

- Added heater/control loop methods (loop 1/2): `get_setpoint`, `set_setpoint`,
  `get_heater_range`, `set_heater_range`, `get_pid`, `set_pid`,
  `get_output_mode`, `set_output_mode`, `get_ramp`, `set_ramp`,
  `read_heater_output`, `read_heater_status`.

## v1.1.0

- Added `set_input_config()` and related setters (`set_input_type`,
  `set_input_curve`, `set_filter`, `set_input_name`, `set_temperature_limit`)
  and `copy_input_config()`.

## v1.0.0

- Initial release: connection handling, temperature reads, input
  configuration reads, sensor status.
