"""Cold tests of the pad logic: strafe cannot exist, forward reaches the limit, deadman/brake timing."""
import math

import pytest

from moss_dimos.diffdrive import DiffDriveConfig
from moss_dimos.teleop_logic import DeadmanBrake, TeleopConfig, axes_to_twist

CFG = TeleopConfig(drive=DiffDriveConfig(track_width_m=0.30, max_track_speed_mps=0.6), max_yaw_rps=2.0, deadzone=0.08, brake_s=0.5)


def test_full_forward_gives_max_track_speed_on_both_tracks():
    vx, wz = axes_to_twist(-1.0, 0.0, CFG)  # stick up reads -1
    assert math.isclose(vx, 0.6) and wz == 0.0


def test_the_pad_has_no_lateral_input_at_all():
    # The API takes two axes only: there is nothing a third axis could change.
    import inspect
    params = list(inspect.signature(axes_to_twist).parameters)
    assert params[:2] == ["left_y", "right_x"] and "left_x" not in params and "vy" not in params


def test_deadzone_reads_as_zero_and_rescales_to_the_rim():
    assert axes_to_twist(-0.05, 0.03, CFG) == (0.0, 0.0)
    vx, _ = axes_to_twist(-0.54, 0.0, CFG)  # (0.54-0.08)/(0.92) = 0.5 of the limit
    assert math.isclose(vx, 0.3)


def test_right_stick_right_turns_right_negative_yaw():
    _, wz = axes_to_twist(0.0, 1.0, CFG)
    assert wz < 0 and math.isclose(abs(wz), 2.0)


def test_full_forward_plus_full_turn_is_scaled_not_flattened():
    vx, wz = axes_to_twist(-1.0, -1.0, CFG)   # raw 0.6 m/s + 2 rad/s -> outer track 0.9 > 0.6
    assert math.isclose(max(abs(vx - 0.15 * wz), abs(vx + 0.15 * wz)), 0.6)
    assert math.isclose(wz / vx, 2.0 / 0.6)     # turn radius kept


def test_boost_multiplies_but_never_exceeds_the_track_limit():
    boosted = TeleopConfig(drive=CFG.drive, boost=1.5)
    vx, _ = axes_to_twist(-1.0, 0.0, boosted, boost_held=True)
    assert math.isclose(vx, 0.6)


@pytest.mark.parametrize("ly,rx", [(float("nan"), 0.0), (0.0, float("inf"))])
def test_non_finite_axis_is_refused(ly, rx):
    with pytest.raises(ValueError):
        axes_to_twist(ly, rx, CFG)


@pytest.mark.parametrize("kw", [dict(max_yaw_rps=0), dict(deadzone=1.0), dict(boost=0.5), dict(brake_s=-1), dict(rate_hz=0)])
def test_invalid_teleop_config_is_refused(kw):
    with pytest.raises(ValueError):
        TeleopConfig(**kw)


def test_deadman_brake_window_then_silence():
    b = DeadmanBrake(0.5)
    assert b.tick(True, 10.0) == "command"
    assert b.tick(False, 10.1) == "brake"      # release observed at 10.1: the window runs from here
    assert b.tick(False, 10.6) == "brake"      # inclusive end of the window
    assert b.tick(False, 10.61) == "silent"
    assert b.tick(False, 20.0) == "silent"


def test_deadman_pressed_again_cancels_the_brake_window():
    b = DeadmanBrake(1.0)
    b.tick(True, 0.0); assert b.tick(False, 0.1) == "brake"
    assert b.tick(True, 0.2) == "command"
    assert b.tick(False, 0.3) == "brake"       # a fresh window starts from the new release


def test_a_pad_at_rest_never_publishes():
    b = DeadmanBrake(0.5)
    assert all(b.tick(False, t) == "silent" for t in (0.0, 0.1, 5.0))
