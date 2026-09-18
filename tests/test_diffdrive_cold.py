"""Cold tests: known inputs -> known outputs, in physical units; invalid inputs are refused."""
import math

import pytest

from moss_dimos.diffdrive import DiffDriveConfig, clamp_twist, tracks_to_twist, twist_to_tracks

CFG = DiffDriveConfig(track_width_m=0.30, max_track_speed_mps=0.6)


def test_straight_ahead_both_tracks_equal():
    assert twist_to_tracks(0.4, 0.0, CFG) == (0.4, 0.4)


def test_spin_in_place_opposite_tracks():
    left, right = twist_to_tracks(0.0, 2.0, CFG)  # 2 rad/s, half width 0.15 -> 0.3 m/s
    assert math.isclose(left, -0.3) and math.isclose(right, 0.3)


def test_roundtrip_73_percent_of_a_turn():
    vx, wz = 0.25, 0.73
    back_vx, back_wz = tracks_to_twist(*twist_to_tracks(vx, wz, CFG), CFG)
    assert math.isclose(back_vx, vx) and math.isclose(back_wz, wz)


def test_over_limit_is_scaled_not_clipped_keeps_ratio():
    left, right = twist_to_tracks(1.0, 2.0, CFG)  # raw: 0.7 / 1.3 -> peak 1.3 > 0.6
    assert math.isclose(max(abs(left), abs(right)), 0.6)
    assert math.isclose(right / left, 1.3 / 0.7)


def test_clamp_twist_full_forward_hits_the_limit_exactly():
    assert clamp_twist(5.0, 0.0, CFG) == (0.6, 0.0)


@pytest.mark.parametrize("width,speed", [(0.0, 0.6), (-0.3, 0.6), (0.3, 0.0), (0.3, -1.0),
                                         (float("nan"), 0.6), (0.3, float("inf"))])
def test_invalid_config_is_refused(width, speed):
    with pytest.raises(ValueError):
        DiffDriveConfig(track_width_m=width, max_track_speed_mps=speed)


@pytest.mark.parametrize("vx,wz", [(float("nan"), 0.0), (0.0, float("nan")), (float("inf"), 0.0), (0.1, float("-inf"))])
def test_non_finite_command_is_refused_never_a_motor_command(vx, wz):
    with pytest.raises(ValueError):
        twist_to_tracks(vx, wz, CFG)
