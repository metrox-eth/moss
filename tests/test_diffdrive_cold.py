"""Cold tests: known inputs -> known outputs, in physical units."""
import math

from moss_dimos.diffdrive import DiffDriveConfig, tracks_to_twist, twist_to_tracks

CFG = DiffDriveConfig(track_width_m=0.30, max_track_speed_mps=0.6)


def test_straight_ahead_both_tracks_equal():
    assert twist_to_tracks(0.4, 0.0, CFG) == (0.4, 0.4)


def test_spin_in_place_opposite_tracks():
    left, right = twist_to_tracks(0.0, 2.0, CFG)  # 2 rad/s, half width 0.15 -> 0.3 m/s
    assert math.isclose(left, -0.3) and math.isclose(right, 0.3)


def test_roundtrip_73_percent_of_a_turn():
    vx, wz = 0.25, 0.73
    left, right = twist_to_tracks(vx, wz, CFG)
    back_vx, back_wz = tracks_to_twist(left, right, CFG)
    assert math.isclose(back_vx, vx) and math.isclose(back_wz, wz)


def test_over_limit_is_scaled_not_clipped_keeps_ratio():
    left, right = twist_to_tracks(1.0, 2.0, CFG)  # raw: 0.7 / 1.3 -> peak 1.3 > 0.6
    assert math.isclose(max(abs(left), abs(right)), 0.6)
    assert math.isclose(right / left, 1.3 / 0.7)


def test_strafe_is_ignored():
    assert twist_to_tracks(0.2, 0.0, CFG, vy=0.9) == twist_to_tracks(0.2, 0.0, CFG)
