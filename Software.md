# Software

The stack is dimOS. The microcontroller drives the motors; dimOS, on the Jetson or the Pi, does teleop, recording, navigation and manipulation. The policies come later, from pooled data.

**The motor firmware drove the prototype, and since 10 October the rover is driven on the floor from a gamepad through dimOS (vector-dimos `moss-gamepad`, below).**

## Motor firmware, ESP32-S3

[`firmware/`](firmware/). Current board: Adafruit QT Py ESP32-S3 on its screw-terminal carrier, firmware `firmware/MOSS_QTPY_MDD3A/` (native USB; one build for the Cytron MDD3A, one for the MDD10A). The DevKitC snapshot `firmware/MOSS_ESP32S3/` is the V0.3 bench firmware, kept as history. Newline-terminated commands over USB serial at 115200 baud:

| Command | What it does |
|---|---|
| `status` | one telemetry line |
| `arm` | ready to drive, for 10 s if no drive comes |
| `drive L R` | track speeds, −100 to +100 percent; must be repeated, 300 ms without one stops and disarms |
| `ramp UP DOWN` | milliseconds per percent, rise and fall; default 30 / 15 |
| `test left 10` | one motor for one second, bench only |
| `stop` | stops and disarms |
| `zero` | resets the encoder counts (disarmed only) |

Telemetry every 200 ms as JSON: firmware and driver names, mode, applied and target percent, raw encoder ticks, battery voltage. Disarmed at boot, nothing moves by itself. The 25 % commissioning limit was lifted after the first drive on the floor (10 October): full stick is 100 % PWM, the host caps lower when it wants to (`MOSS_MAX_PCT`). No speed loop, no odometry in metres yet.

The board reads battery voltage through an INA219. It does not measure motor current: the shunt is not in the motor line.

## Teleop and navigation: dimOS

MOSS runs [dimOS](https://github.com/dimensionalOS) by Dimensional, on the Jetson or on the Pi. The base that drove on 10 October is the `moss-gamepad` blueprint of [vector-dimos](https://github.com/metrox-eth/vector-dimos): a gamepad module publishing a Twist behind a deadman, a tracked-base adapter that turns the twist into track percent and keeps the firmware's deadman fed, tank steering (past half turn stick the inner track reverses), a launcher with gates (pad present, board present, firmware disarmed, battery above its floor). `moss_dimos/` in this repository is the earlier skeleton of the same idea, cold-tested only. Navigation and the pick come next, then speed control and odometry.

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

Demonstrations are recorded with the same camera names on every rover, so datasets pool without rework. The rules are in [docs/data.md](docs/data.md). The simulator (MuJoCo body, three recorded pickup missions) is in [moss-jev](https://github.com/metrox-eth/moss-jev).

## Tests

```
python -m pytest tests
```

Cold tests only: a fake serial port replaying a real bench session, and a Linux pseudo-terminal. The firmware's host logic test is `firmware/tests/control_test.cpp`, any C++17 compiler.
