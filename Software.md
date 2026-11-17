# Software

The microcontroller drives the motors. Everything above it runs on [dimOS](https://github.com/dimensionalOS/dimos) by Dimensional, on the robot's computer: teleop, the lidar map, navigation, exploration and recording. The code for that is in this repository, in `moss_dimos/` and `tools/`.

Connect the hardware first using the [illustrated wiring guide](docs/build/WIRING.md). It includes the motor-driver connections, encoders, INA219, servo adapter and audio.

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
| `clearstop` | v5: clears the latched track stop only after the NC button loop closes; remains disarmed |
| `zero` | resets the encoder counts (disarmed only) |

Telemetry every 200 ms as JSON: firmware and driver names, mode, applied and target percent, raw encoder ticks, battery voltage. Disarmed at boot, nothing moves by itself. Full stick is 100 % PWM; the host caps lower when it wants to (`MOSS_MAX_PCT`). The firmware is open loop: there is no speed loop, and odometry in metres needs the encoder calibration in [docs/base.md](docs/base.md).

The board reads battery voltage through an INA219. It does not measure motor current: the shunt is not in the motor line.

**Two-wire stop button, v5 firmware:** connect the button's NC contact between SCK (GPIO 36) and GND before installing `qtpy-mdd3a-v5`. An open loop stops and latches the tracks; releasing the button cannot restart them. Telemetry adds `stop_open` and `stop_latched`. This is a software track stop, not a power cutoff or an arm stop. Stop the host stack and centre the controls before sending `clearstop`, then check and restart deliberately. [Connection and recovery procedure](docs/build/WIRING.md#5-connect-the-two-wire-track-stop-button).

To reflash the QT Py, from the root of the checkout: build the images with `arduino-cli compile --fqbn esp32:esp32:adafruit_qtpy_esp32s3_nopsram:CDCOnBoot=cdc --export-binaries firmware/MOSS_QTPY_MDD3A` (they land in `firmware/MOSS_QTPY_MDD3A/build/`), add esptool to the venv with the `firmware` extra (`uv pip install --python .venv/bin/python -e '.[firmware]'`), then run `firmware/MOSS_QTPY_MDD3A/bench/flash_qtpy.sh`. The bench scripts are described in [its README](firmware/MOSS_QTPY_MDD3A/bench/README.md).

## What is in `moss_dimos/`

| Module | Role |
|---|---|
| `moss_adapter.py`, `moss_mock.py` | the tracked-base adapter (twist to track percent, keepalive inside the firmware's 300 ms deadman) and a fake firmware for runs without motors |
| `gamepad.py` | the pad: twist from the sticks (no deadman by default), slew-limited, sized to the base |
| `c1_serial.py`, `rplidar_c1.py` | the RPLidar C1 driver and its dimOS module |
| `lidar_odometry.py` | the pose, from the lidar (kiss-icp) |
| `costmap2d.py` | the 2D map the planner and the cockpit read |
| `recovering_planner.py`, `explorer2.py` | A* to a goal with a way out of tight spots, and frontier exploration |
| `memory.py` | the recorder: the whole run in one SQLite file |
| `robot_profile.py` | MOSS's geometry and device paths, each overridable by a `MOSS_*` variable |
| `blueprints.py` | the four dimOS blueprints: `moss-base`, `moss-gamepad`, `moss-nav`, `moss-explore` |

`tools/` holds the flight check (`moss_preflight.py`), the launchers (`moss-fly.sh`, `moss-teleop.sh`), the exploration switch (`explore_ctl.py`) and the cockpit (`moss_cockpit.py` and its page).

## Install on the robot

Python 3.12 in a venv at the root of the checkout (the launchers look for `.venv/`), made with [uv](https://docs.astral.sh/uv/), which also fetches Python 3.12 where the system ships an older one (JetPack 6 on a Jetson, Raspberry Pi OS). Then dimOS from git, then this package:

```
uv venv --python 3.12 .venv
DIMOS_ALLOW_MISSING_COCKPIT=1 uv pip install --python .venv/bin/python \
    "dimos @ git+https://github.com/dimensionalOS/dimos.git@a7d19f76158b01739b26e7a17390f89764aaef83"
uv pip install --python .venv/bin/python -e '.[nav,gamepad,camera]'   # kiss-icp for the lidar odometry, pygame for the pad, pyrealsense2 for the RealSense
sudo usermod -aG dialout "$USER"             # once, then log in again
```

dimOS is installed at the commit this package runs against. `DIMOS_ALLOW_MISSING_COCKPIT=1` builds it without its web UI, which is not in its git tree and which MOSS does not use (the cockpit below is its own page). dimOS main has since moved the planner and the explorer this package imports, so a newer commit must pass `benches/run_all.sh` first.

No RealSense: leave `camera` out and run with `MOSS_CAMERA=0`. On a Jetson the PyPI `pyrealsense2` wheel installs but does not import (it needs a newer glibc than JetPack 6 has): leave `camera` out and install `pyrealsense2-extended`, or a librealsense built for the board with its Python bindings. Either way, copy librealsense's `config/99-realsense-libusb.rules` to `/etc/udev/rules.d/` and run `sudo udevadm control --reload-rules && sudo udevadm trigger`, so the camera opens without root.

On a computer where dimOS sits on wheels built for that board, install this package with `uv pip install --python .venv/bin/python -e . --no-deps` so those wheels stay, and add `kiss-icp==1.3.0`, `pygame` and `pyserial` by hand (and the RealSense module above). A venv made with `python3.12 -m venv .venv` works the same way, with `.venv/bin/pip install` in place of `uv pip install --python .venv/bin/python`. The editable install registers the blueprints as `moss-dimos.moss-base`, `moss-dimos.moss-gamepad`, `moss-dimos.moss-nav` and `moss-dimos.moss-explore`; run it again after adding a blueprint.

### First run: system settings

dimOS's bus (LCM) needs multicast on the loopback interface, a `224.0.0.0/4` route on it, and 64 MB socket buffers (`net.core.rmem_max`, `net.core.rmem_default`). None of it survives a reboot. dimOS checks them at each launch and sets what is missing with sudo, so either the robot's user has passwordless sudo, or `tools/lcm-loopback.service` applies them at boot (install line in [docs/cockpit.md](docs/cockpit.md#the-cockpit-as-a-service)). Without either, a launch stops on a `CalledProcessError` from `sudo ip ...`.

### Speaker on the Jetson's I2S

The rover's speaker is a MAX98357A I2S amplifier on the Jetson's 40-pin header, I2S2: BCLK on pin 12, LRCLK on pin 35, DIN on pin 40 (the Jetson's data out), 5 V and ground. The header has no function enabled by default; `sudo /opt/nvidia/jetson-io/config-by-function.py -o dt 1="i2s2"` writes a device-tree overlay and a boot entry for it, and the board reboots. Then the I2S2 controls of the `APE` sound card (`amixer -c APE controls | grep -i i2s2`): codec frame mode `i2s`, codec master mode `cbs-cfs`, playback bit format `16`, sample rate `44100`, playback channels `2`, kept across reboots with `sudo alsactl store`. As done on the Orin Nano devkit under JetPack 6; `paplay assets/sounds/hello_01.wav` is the test.

PulseAudio: make the card the default sink (`pactl set-default-sink alsa_output.platform-sound.analog-stereo`, then `pactl set-sink-volume @DEFAULT_SINK@ 100%`) and keep the sink from suspending between cues, which clicks on this amplifier, with a `~/.config/pulse/default.pa` of two lines: `.include /etc/pulse/default.pa` and `unload-module module-suspend-on-idle`. The sound module (`moss_dimos/sounds.py`, [docs/cockpit.md](docs/cockpit.md)) plays into that session: a stack launched from a login shell or over ssh as the robot's user finds it, the boot service's stack does not and stays silent.

## Run

```
tools/moss-fly.sh check               # flight check only, nothing launched
tools/moss-fly.sh map                 # gates, then moss-nav: lidar map, pad teleop, recording
tools/moss-fly.sh explore             # gates, then moss-explore: map, planner, explorer, NOT armed
EXPLORE=1 tools/moss-fly.sh explore   # ... and arm exploration once the stack is proven
tools/moss-fly.sh stop                # stop exploration, then the stack
MOCK=1 tools/moss-fly.sh map          # fake motor board, no motor; the lidar must still be plugged
tools/moss-teleop.sh                  # the pad only: gates, then moss-gamepad
```

Pad on the dimOS path: left stick forward and back, right stick to turn, R2 boost; centre the sticks and the tracks stop. To drive as soon as the rover is powered, install `tools/moss-teleop.service` (its header has the three lines): it retries the launcher at boot until the pad and the board are there. No deadman by default (`MOSS_PAD_DEADMAN=r1` in `robot.env` brings the held R1 back).

Every gate refuses rather than guesses, with the fix on the same line: a stack already up, a missing board, a port held by another program, a mute firmware, a battery at the BMS floor, a lidar that does not spin. Nothing moves by itself: in `map` only the pad drives; in `explore` the planner moves on a goal or once exploration is armed. The firmware stops the tracks 300 ms after the last command, whatever happens above it.

The flight check, `tools/moss_preflight.py`, is read-only: stack, ports, firmware, lidar spin, RealSense, wrist camera, pad, system, software and the state directory, one line each, exit 1 on any failure. The launcher runs it before every launch and saves it for the cockpit. A missing pad is a warning; `MOSS_REQUIRE_PAD=1` makes it a failure. With `MOSS_CAMERA=0` the RealSense line is skipped.

## The cockpit

`tools/moss-fly.sh cockpit` starts a small web server on the robot, port 8904, and prints its address. One page: the flight check, battery and track outputs, the live map with the lidar scan and the path (tap to send a goal), the two cameras, launch and stop buttons, episode markers and the log. The manual, the endpoints and the service install are in [docs/cockpit.md](docs/cockpit.md).

## Recording and calibration

Each run is recorded into one SQLite file, `~/.local/state/moss/recordings/moss.db` (`MOSS_STATE_DIR` moves it): pose, map, lidar, both cameras, commands, base telemetry and episode markers. The previous run is kept beside it. Details and how to read it back: [docs/cockpit.md](docs/cockpit.md#recording).

The geometry and the base numbers are placeholders until measured; each has a `MOSS_*` environment variable. The base's three ([docs/base.md](docs/base.md)) turn a twist into track percent and encoder ticks into metres; the rest (lidar height, footprint, clearances) is in [docs/cockpit.md](docs/cockpit.md#the-robot-profile).

## Bench tool without dimOS, `moss_pi/`

Talks to the firmware from any computer over USB, to arm and drive during commissioning. Python standard library plus pyserial, and pygame for a pad. It was written for the earlier DevKitC board and its USB-UART: it opens the port with DTR low, and the current QT Py firmware sends nothing to a host that holds DTR low, so on the QT Py it gets no telemetry and no replies. On the current board, drive with `tools/moss-teleop.sh` instead.

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[pi,test]'
sudo usermod -aG dialout "$USER"             # once, then log in again
PORT=$(ls /dev/serial/by-id/*QT_Py*)         # the motor board (the CP2102N one is the lidar, never this)
python -m moss_pi.teleop --port "$PORT" --keyboard     # r arm, hold w/s/a/d, space stop, q quit
python -m moss_pi.teleop --port "$PORT" --gamepad      # SDL button 0 arms, hold 4 to drive, 5 boost
python -m moss_pi.telemetry_log --port "$PORT" --out telemetry.jsonl
```

This path reads raw SDL buttons: 0 arms, 4 is the deadman, 5 is boost. That is A, L1 and R1 on an Xbox-layout pad. On the MOSS pad R1 is button 7, so this numbering does not match it: use the dimOS path with that pad, and on any other pad check which physical button is 4 before driving. Nothing moves until you arm with the deadman released. Hold the deadman to drive; release and it brakes, then disarms. The stick is open loop: full stick is 25 % duty. Put the rover on blocks for the first run.

## Data and policies

Demonstrations are recorded with the same camera names on every rover, so datasets pool without rework. The rules are in [docs/data.md](docs/data.md). The simulator (MuJoCo body, three recorded pickup missions) is in [moss-jev](https://github.com/metrox-eth/moss-jev).

## Tests and benches

```
python -m pytest tests                       # no robot, no dimOS
benches/run_all.sh .venv/bin/python          # every bench, one PASSED/FAILED line each (the robot's venv)
```

`tests/` is pytest: a fake serial port replaying a real bench session, a Linux pseudo-terminal, the pure pad and drive logic. `benches/` are scripts, one per module or tool, each feeding known values and reading back known values (metres, degrees, bytes on a named channel); run one with `PYTHONPATH=. .venv/bin/python benches/bench_<name>.py`. Most benches need dimOS, so run them in the robot's venv. Six also run without it and skip the sections that need it, with a line that says so: `bench_robot_profile_cold`, `bench_moss_adapter_cold`, `bench_explorer2_cold`, `bench_moss_preflight_cold`, `bench_moss_fly_gates_cold` and `bench_moss_cockpit_cold`. `run_all.sh` leaves out the live bench, `bench_lcm_latest_live`, unless `LIVE=1` is set: it needs LCM multicast on the machine. The firmware's host logic test is `firmware/tests/control_test.cpp`, any C++17 compiler.
