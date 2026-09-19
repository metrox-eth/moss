# Bench traces, 20 September 2026

Raw JSON captured from the ESP32-S3 telemetry during the first motor and encoder tests. Context and limits: `docs/build_log.md`, entry 2026-09-20.

- `motor_ramp_100pct.json`: both motors, 4 s ramp up, 2 s at 100 % PWM duty, 4 s ramp down, one cycle per direction, unloaded on the bench. Temporary firmware; the 25 % limit was restored afterwards.
- `ina_bypassed_NOT_motor_current.json`: INA219 readings taken while the motor current bypassed the module's shunt. The `current_mA` values are not motor consumption. Kept for the bus voltage only.
