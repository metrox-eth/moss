"""Differential-drive kinematics for MOSS (tracked base, two motors).

Pure functions, no hardware, no dimOS import: cold-testable anywhere.

Convention: vx forward in m/s, wz counter-clockwise in rad/s, track_width in m
(distance between the two track centrelines). Left/right speeds in m/s at the
track. vy is accepted and ignored: a tracked rover cannot strafe.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiffDriveConfig:
    track_width_m: float = 0.30
    max_track_speed_mps: float = 0.6


def twist_to_tracks(vx: float, wz: float, cfg: DiffDriveConfig, vy: float = 0.0) -> tuple[float, float]:
    """Twist -> (left, right) track speeds in m/s, scaled to stay within the limit.

    Scaling (not clipping) keeps the turn radius when a command is too fast:
    a full-speed forward plus a turn slows both tracks together instead of
    flattening the turn.
    """
    del vy  # no strafe on tracks
    half = 0.5 * cfg.track_width_m
    left = vx - wz * half
    right = vx + wz * half
    peak = max(abs(left), abs(right))
    if peak > cfg.max_track_speed_mps > 0:
        k = cfg.max_track_speed_mps / peak
        left, right = left * k, right * k
    return left, right


def tracks_to_twist(left: float, right: float, cfg: DiffDriveConfig) -> tuple[float, float]:
    """(left, right) track speeds -> (vx, wz). Inverse of twist_to_tracks when unscaled."""
    vx = 0.5 * (left + right)
    wz = (right - left) / cfg.track_width_m
    return vx, wz
