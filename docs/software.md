# Software notes

MOSS runs on dimOS. The software here starts as a scaffold derived from vector-dimos, the external dimOS blueprint written for VECTOR (a mecanum rover on the same Jetson Orin Nano 8 GB).

What carries over: the idea of a gamepad module publishing a Twist behind a deadman, the rig/onboard split over zenoh, the recording tooling.

What is written for MOSS: `moss_dimos/teleop_logic.py` (pure: two stick axes only, forward and yaw, no lateral input exists; deadzone; deadman with a brake window of zeros; every value validated) and `moss_dimos/diffdrive.py` (differential-drive kinematics, scaling instead of clipping, invalid configs and non-finite commands refused). `moss_dimos/gamepad.py` is the thin dimOS wrapper around them. The motor layer on the microcontroller side exists: [`firmware/`](../firmware/README.md), an ESP32-S3 commissioning firmware (newline-terminated serial commands over USB-UART at 115200 baud: `arm`, `drive LEFT RIGHT`, `test left|right PERCENT`, `stop`, `status`, `zero`; disarmed at boot; a 300 ms command watchdog stops and disarms; 25 % commissioning limit; JSON telemetry every 200 ms with raw encoder ticks and battery voltage). Its command set is the Jetson–ESP32 contract for now. The Jetson-side driver that speaks it, speed control and odometry are not written yet.

Everything in `moss_dimos/` is cold-tested only until the base runs.

## Driving from a Raspberry Pi 5 (`moss_pi/`, no dimOS)

`moss_pi/` drives MOSS from a Raspberry Pi 5 through the same ESP32-S3 firmware and its serial commands, without dimOS. It reuses the pure pad logic in `moss_dimos/teleop_logic.py` (forward and yaw only, deadzone, brake window) and needs only the Python standard library plus pyserial, and pygame for a gamepad.

- `serial_bridge.py` writes `status`, `arm`, `stop`, `zero` and `drive LEFT RIGHT` (integers, -25..+25) and parses the JSON telemetry. It refuses to drive before `arm` and sends `stop` when 300 ms pass without a drive command. It also disarms on any `ERR` reply and reopens a lost port every second, sending `stop` first. `test` is left out: it is a bench command.
- `teleop.py`, keyboard or gamepad. Nothing moves until you press arm with the deadman released. Hold the deadman to drive. On release it sends `drive 0 0` for 0.5 s, then `stop`, which disarms, so each new drive needs a new arm. The stick is mapped open loop: `max_track_speed_mps` (0.6 by default) becomes 25 % PWM duty. The speed MOSS actually reaches at 25 % has not been measured.
- `telemetry_log.py` appends each telemetry line to a JSONL file as `{"wall_time_s": ..., "telemetry": {...}}`. On its own it only listens.

On the Pi, from a clone of this repository:

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[pi,test]'
python -m pytest tests                       # cold tests, no robot needed
sudo usermod -aG dialout "$USER"             # once, then log in again
ls /dev/serial/by-id/                        # find the ESP32 USB-UART adapter
python -m moss_pi.telemetry_log --port /dev/ttyUSB0 --out telemetry.jsonl
python -m moss_pi.teleop --port /dev/ttyUSB0 --keyboard      # r arm, hold w/s/a/d, space stop, q quit
python -m moss_pi.teleop --port /dev/ttyUSB0 --gamepad --log drive.jsonl   # A arm, hold L1, R1 boost
```

Use the DevKitC port wired to the USB-to-UART bridge (see [`firmware/`](../firmware/README.md)). It shows up as `/dev/ttyUSB0` or `/dev/ttyACM0`, depending on the bridge chip. A terminal reports key presses but not key releases, so with the keyboard a key counts as held for 0.6 s after its last repeat, and the rover brakes later than with a pad. Put the rover on blocks for the first run.

State: cold-tested only, against a fake serial port that replays the 20 September 2026 bench telemetry and against a Linux pseudo-terminal through pyserial. Nothing in `moss_pi/` has run on a Pi or on the rover yet.
