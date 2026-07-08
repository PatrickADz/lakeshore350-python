# Changelog

## v1.2.0

- Added heater/control loop methods (loop 1/2): `get_setpoint`, `set_setpoint`,
  `get_heater_range`, `set_heater_range`, `get_pid`, `set_pid`,
  `get_output_mode`, `set_output_mode`, `get_ramp`, `set_ramp`,
  `read_heater_output`, `read_heater_status`.
- These make the driver usable for temperature *control*, not just monitoring.
  Not exercised in production at CePIA yet (monitoring-only use case), but
  implemented and tested against the Model 350 SCPI command set for future use.

## v1.1.0

- Added `set_input_config()` and related setters (`set_input_type`,
  `set_input_curve`, `set_filter`, `set_input_name`, `set_temperature_limit`)
  and `copy_input_config()`.

## v1.0.0

- Initial release: connection handling, temperature reads, input
  configuration reads, sensor status.
