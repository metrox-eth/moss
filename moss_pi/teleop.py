"""Keyboard or gamepad teleop for MOSS on a Raspberry Pi, through SerialBridge.

Reuses `moss_dimos.teleop_logic` (pure, no dimOS import): two inputs only,
forward and yaw; deadzone; deadman with a brake window.

Sequence, identical for keyboard and pad:
1. nothing moves until the arm key/button is pressed with the deadman released;
2. while the deadman is held, `drive L R` is sent every loop (default 50 Hz);
3. on release, `drive 0 0` for the brake window (default 0.5 s), then `stop`;
4. `stop` disarms the firmware, so each new drive needs a new arm.
The bridge adds its own deadman (300 ms without drive -> stop), and the
firmware its own (300 ms without drive -> stop and disarm).

Duty mapping: track speeds from `twist_to_tracks` are scaled so that
`max_track_speed_mps` maps to 25 % PWM duty. This is open loop: the firmware
has no speed control, and the speed MOSS actually reaches at 25 % duty is not
measured. The metres per second here are a scale, not a promise.

    python -m moss_pi.teleop --port /dev/ttyUSB0 --keyboard
    python -m moss_pi.teleop --port /dev/ttyUSB0 --gamepad --log drive.jsonl
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

from moss_dimos.diffdrive import twist_to_tracks
from moss_dimos.teleop_logic import DeadmanBrake, TeleopConfig, axes_to_twist

from .serial_bridge import MAX_PERCENT, SerialBridge, open_serial

# Standard dual-stick pad, pygame numbering (same as moss_dimos/gamepad.py).
AXIS_LEFT_Y = 1
AXIS_RIGHT_X = 2
BUTTON_ARM = 0       # A / cross
BUTTON_DEADMAN = 4   # L1
BUTTON_BOOST = 5     # R1


def tracks_to_percent(left_mps: float, right_mps: float, max_track_speed_mps: float,
                      max_pct: int = MAX_PERCENT) -> tuple[int, int]:
    """Track speeds in m/s -> integer duty percent for `drive`, max speed -> max_pct.

    Rounds half away from zero and clamps to [-max_pct, max_pct].
    """
    def one(v: float) -> int:
        if not math.isfinite(v):
            raise ValueError(f"track speed must be finite, got {v!r}")
        p = v / max_track_speed_mps * max_pct
        p = math.copysign(math.floor(abs(p) + 0.5), p)
        return int(max(-max_pct, min(max_pct, p)))
    return one(left_mps), one(right_mps)


class TeleopSession:
    """Turns one sample of the inputs into at most one bridge call. Pure apart from the bridge."""

    def __init__(self, bridge: SerialBridge, cfg: TeleopConfig | None = None) -> None:
        self.bridge = bridge
        self.cfg = cfg or TeleopConfig()
        self._brake = DeadmanBrake(self.cfg.brake_s)
        self._arm_prev = False
        self._driving = False     # a drive was sent since the last stop

    def step(self, now_s: float, arm_pressed: bool, deadman_held: bool,
             left_y: float = 0.0, right_x: float = 0.0, boost: bool = False) -> str:
        """Returns what was done: 'arm', 'drive L R', 'brake', 'stop', 'not_armed' or 'idle'."""
        arm_edge = arm_pressed and not self._arm_prev
        self._arm_prev = arm_pressed
        if arm_edge and not deadman_held and not self._driving:
            self.bridge.arm()
            return "arm"

        state = self._brake.tick(deadman_held, now_s)
        if state == "command":
            if not self.bridge.armed:
                return "not_armed"
            vx, wz = axes_to_twist(left_y, right_x, self.cfg, boost_held=boost)
            left, right = tracks_to_percent(*twist_to_tracks(vx, wz, self.cfg.drive),
                                            self.cfg.drive.max_track_speed_mps)
            if self.bridge.drive(left, right):
                self._driving = True
                return f"drive {left} {right}"
            return "not_armed"
        if state == "brake" and self._driving:
            self.bridge.drive(0, 0)
            return "brake"
        if state == "silent" and self._driving:
            self._driving = False
            self.bridge.stop()
            return "stop"
        return "idle"

    def emergency_stop(self) -> None:
        self._driving = False
        self.bridge.stop()


class KeyboardAxes:
    """Terminal keys -> (arm, deadman, left_y, right_x).

    A terminal reports key presses, not releases: a direction key counts as held
    for `hold_s` after its last repeat. `hold_s` must cover the keyboard's
    auto-repeat delay (often 0.5 s), so a keyboard brakes later than a pad.

    w/s forward/back, a/d turn left/right, r arm, space stop now, q quit.
    """

    def __init__(self, speed: float = 0.5, hold_s: float = 0.6) -> None:
        if not 0 < speed <= 1:
            raise ValueError("speed must be in (0, 1]")
        self.speed, self.hold_s = speed, hold_s
        self._seen: dict[str, float] = {}
        self._arm = False
        self.stop_requested = False
        self.quit_requested = False

    def feed(self, key: str, now_s: float) -> None:
        k = key.lower()
        if k in "wasd" and len(k) == 1:
            self._seen[k] = now_s
        elif k == "r":
            self._arm = True
        elif k == " ":
            self._seen.clear()
            self.stop_requested = True
        elif k == "q":
            self._seen.clear()
            self.quit_requested = True

    def sample(self, now_s: float) -> tuple[bool, bool, float, float]:
        live = {k for k, t in self._seen.items() if now_s - t <= self.hold_s}
        arm, self._arm = self._arm, False
        # Stick convention of teleop_logic: forward is left_y < 0, right turn is right_x > 0.
        ly = self.speed * ((("s" in live) - ("w" in live)))
        rx = self.speed * ((("d" in live) - ("a" in live)))
        return arm, bool(live), float(ly), float(rx)


def _run_keyboard(session: TeleopSession, bridge: SerialBridge, speed: float) -> None:
    import select
    import termios
    import tty

    keys = KeyboardAxes(speed=speed)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    period = 1.0 / session.cfg.rate_hz
    print("r arm | hold w/s/a/d to drive | space stop | q quit", end="\r\n")
    try:
        tty.setcbreak(fd)
        while not keys.quit_requested:
            while select.select([sys.stdin], [], [], 0)[0]:
                keys.feed(os.read(fd, 1).decode(errors="ignore"), time.monotonic())
            if keys.stop_requested:
                keys.stop_requested = False
                session.emergency_stop()
            arm, held, ly, rx = keys.sample(time.monotonic())
            _report(session.step(time.monotonic(), arm, held, ly, rx))
            bridge.tick()
            time.sleep(period)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def _run_gamepad(session: TeleopSession, bridge: SerialBridge) -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame  # optional dependency: pip install 'moss-dimos[pi]'

    pygame.init()
    pygame.joystick.init()
    period = 1.0 / session.cfg.rate_hz
    pad = None
    print("A/cross arm | hold L1 + sticks to drive | R1 boost | Ctrl-C quit")
    while True:
        if pad is None:
            pygame.joystick.quit(); pygame.joystick.init()
            if pygame.joystick.get_count() == 0:
                bridge.tick(); time.sleep(0.5); continue
            pad = pygame.joystick.Joystick(0); pad.init()
            print(f"gamepad connected: {pad.get_name()}")
        pygame.event.pump()
        try:
            arm = bool(pad.get_button(BUTTON_ARM))
            held = bool(pad.get_button(BUTTON_DEADMAN))
            boost = bool(pad.get_button(BUTTON_BOOST))
            ly, rx = pad.get_axis(AXIS_LEFT_Y), pad.get_axis(AXIS_RIGHT_X)
        except pygame.error:
            print("gamepad lost: stop")
            session.emergency_stop()
            pad = None
            continue
        _report(session.step(time.monotonic(), arm, held, ly, rx, boost))
        bridge.tick()
        time.sleep(period)


_last_report = ""


def _report(action: str) -> None:
    global _last_report
    kind = action.split()[0]
    if kind != _last_report:  # one line per change, not one per loop
        print(action, end="\r\n")
    _last_report = kind


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Drive MOSS from a Pi through the ESP32-S3 firmware.")
    ap.add_argument("--port", required=True, help="serial device, e.g. /dev/ttyUSB0")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--keyboard", action="store_true")
    mode.add_argument("--gamepad", action="store_true")
    ap.add_argument("--key-speed", type=float, default=0.5, help="keyboard stick deflection, 0..1 (default 0.5)")
    ap.add_argument("--log", help="also append telemetry to this JSONL file")
    args = ap.parse_args(argv)

    bridge = SerialBridge(lambda: open_serial(args.port))
    log = None
    if args.log:
        from .telemetry_log import TelemetryLog
        log = TelemetryLog(args.log)
        bridge.add_listener(log.on_line)
    bridge.add_listener(lambda line, parsed: print(line, end="\r\n") if line.startswith("ERR") else None)
    session = TeleopSession(bridge)
    try:
        if args.keyboard:
            _run_keyboard(session, bridge, args.key_speed)
        else:
            _run_gamepad(session, bridge)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()  # sends a last stop
        if log:
            log.close()


if __name__ == "__main__":
    main()
