"""Gamepad teleop logic for MOSS, pure and cold-testable (no pygame, no dimOS).

The pad drives a differential-drive tracked base: the LEFT stick vertical axis
is forward speed, the RIGHT stick horizontal axis is yaw rate. No other axis is
read, so no lateral input can ever change a track command.

Safety behaviour (state machine in DeadmanBrake):
- commands are published only while the deadman button is held;
- on release, zeros are published for `brake_s` seconds (the brake window),
  then nothing at all: a pad at rest owns nothing;
- pressing the deadman again ends the brake window immediately.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .diffdrive import DiffDriveConfig, clamp_twist


def _finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class TeleopConfig:
    drive: DiffDriveConfig = DiffDriveConfig()
    max_yaw_rps: float = 2.0      # yaw rate at full right-stick deflection
    deadzone: float = 0.08        # stick values below this (absolute) read as 0
    boost: float = 1.0            # multiplier while the boost button is held (1.0 = off)
    brake_s: float = 0.5          # zeros published after the deadman is released
    rate_hz: float = 50.0

    def __post_init__(self) -> None:
        y = _finite("max_yaw_rps", self.max_yaw_rps)
        d = _finite("deadzone", self.deadzone)
        b = _finite("boost", self.boost)
        s = _finite("brake_s", self.brake_s)
        r = _finite("rate_hz", self.rate_hz)
        if y <= 0:
            raise ValueError("max_yaw_rps must be > 0")
        if not 0 <= d < 1:
            raise ValueError("deadzone must be in [0, 1)")
        if b < 1:
            raise ValueError("boost must be >= 1 (1.0 disables it)")
        if s < 0:
            raise ValueError("brake_s must be >= 0")
        if r <= 0:
            raise ValueError("rate_hz must be > 0")


def _deadzone(x: float, dz: float) -> float:
    """Rescale a stick axis so the output is 0 inside the deadzone and reaches ±1 at the rim."""
    a = abs(x)
    if a <= dz:
        return 0.0
    y = (a - dz) / (1.0 - dz)
    return math.copysign(min(y, 1.0), x)


def axes_to_twist(left_y: float, right_x: float, cfg: TeleopConfig, boost_held: bool = False) -> tuple[float, float]:
    """Stick axes in [-1, 1] -> (vx m/s, wz rad/s), already clamped to the track envelope.

    Pad convention: pushing the left stick UP reads negative on most pads, so
    forward is -left_y. Pushing the right stick RIGHT (positive) turns right,
    which is a negative yaw rate (counter-clockwise positive).
    """
    ly = _finite("left_y", left_y)
    rx = _finite("right_x", right_x)
    ly = max(-1.0, min(1.0, ly))
    rx = max(-1.0, min(1.0, rx))
    k = cfg.boost if boost_held else 1.0
    vx = -_deadzone(ly, cfg.deadzone) * cfg.drive.max_track_speed_mps * k
    wz = -_deadzone(rx, cfg.deadzone) * cfg.max_yaw_rps * k
    return clamp_twist(vx, wz, cfg.drive)


class DeadmanBrake:
    """Decides, each tick, what to publish: 'command', 'brake' (zeros) or 'silent'."""

    def __init__(self, brake_s: float) -> None:
        self.brake_s = _finite("brake_s", brake_s)
        self._held = False
        self._released_at: float | None = None

    def tick(self, deadman_held: bool, now_s: float) -> str:
        now_s = _finite("now_s", now_s)
        if deadman_held:
            self._held = True
            self._released_at = None
            return "command"
        if self._held:
            self._held = False
            self._released_at = now_s
        if self._released_at is not None and now_s - self._released_at <= self.brake_s:
            return "brake"
        self._released_at = None
        return "silent"
