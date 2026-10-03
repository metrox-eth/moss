# Software

Three layers. The microcontroller drives the motors. dimOS, on the Jetson or the Pi, does teleop and navigation. The policies come later, from pooled data.

**The motor firmware drove the prototype. The computer side is tested against a fake serial port only.**

## Motor firmware, ESP32-S3

[`firmware/`](firmware/). Newline-terminated commands over USB serial at 115200 baud:

| Command | What it does |
|---|---|
| `status` | one telemetry line |
| `arm` | ready to drive, for 10 s if no drive comes |
| `drive L R` | track speeds, −25 to +25 percent; must be repeated, 300 ms without one stops and disarms |
| `test left 10` | one motor for one second, bench only |
| `stop` | stops and disarms |
| `zero` | resets the encoder counts (disarmed only) |

Telemetry every 200 ms as JSON: mode, raw encoder ticks, battery voltage. Disarmed at boot, nothing moves by itself. The 25 % limit is the commissioning limit; it stays until speed control exists. No speed loop, no odometry in metres yet.

The board reads battery voltage through an INA219. It does not measure motor current: the shunt is not in the motor line.

## Teleop and navigation: dimOS, `moss_dimos/`

MOSS runs [dimOS](https://github.com/dimensionalOS) by Dimensional, on the Jetson or on the Pi: a gamepad module publishing a Twist behind a deadman, differential-drive kinematics, then navigation and the pick. Speed control and odometry come next.

## Bench tool, `moss_pi/`

Talks to the firmware from any computer over USB, to arm, drive and log telemetry during commissioning. Python standard library plus pyserial, and pygame for a pad.

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[pi,test]'
python -m pytest tests                       # no robot needed
sudo usermod -aG dialout "$USER"             # once, then log in again
ls /dev/serial/by-id/                        # find the USB-UART adapter
python -m moss_pi.teleop --port /dev/ttyUSB0 --keyboard     # r arm, hold w/s/a/d, space stop, q quit
python -m moss_pi.teleop --port /dev/ttyUSB0 --gamepad      # A arm, hold L1 to drive, R1 boost
python -m moss_pi.telemetry_log --port /dev/ttyUSB0 --out telemetry.jsonl
```

Nothing moves until you arm with the deadman released. Hold the deadman to drive; release and it brakes, then disarms. The stick is open loop: full stick is 25 % duty. Put the rover on blocks for the first run.

## Data and policies

Demonstrations are recorded in the LeRobot format with the same camera names on every rover, so datasets pool without rework. The rules are in [docs/data.md](docs/data.md). The simulator (MuJoCo body, three recorded pickup missions) is in [moss-jev](https://github.com/metrox-eth/moss-jev).

## Tests

```
python -m pytest tests
```

Cold tests only: a fake serial port replaying a real bench session, and a Linux pseudo-terminal. The firmware's host logic test is `firmware/tests/control_test.cpp`, any C++17 compiler.
