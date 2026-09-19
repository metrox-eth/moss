# Software notes

MOSS runs on dimOS. The software here starts as a scaffold derived from vector-dimos, the external dimOS blueprint written for VECTOR (a mecanum rover on the same Jetson Orin Nano 8 GB).

What carries over: the idea of a gamepad module publishing a Twist behind a deadman, the rig/onboard split over zenoh, the recording tooling.

What is written for MOSS: `moss_dimos/teleop_logic.py` (pure: two stick axes only, forward and yaw, no lateral input exists; deadzone; deadman with a brake window of zeros; every value validated) and `moss_dimos/diffdrive.py` (differential-drive kinematics, scaling instead of clipping, invalid configs and non-finite commands refused). `moss_dimos/gamepad.py` is the thin dimOS wrapper around them. The motor layer on the microcontroller side exists: [`firmware/`](../firmware/README.md), an ESP32-S3 commissioning firmware (newline-terminated serial commands over USB-UART at 115200 baud: `arm`, `drive LEFT RIGHT`, `test left|right PERCENT`, `stop`, `status`, `zero`; disarmed at boot; a 300 ms command watchdog stops and disarms; 25 % commissioning limit; JSON telemetry every 200 ms with raw encoder ticks and battery voltage). Its command set is the Jetson–ESP32 contract for now. The Jetson-side driver that speaks it, speed control and odometry are not written yet.

Everything in `moss_dimos/` is cold-tested only until the base runs.
