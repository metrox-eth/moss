"""Cold tests of moss_pi.teleop: arm step, deadman, brake on release, duty mapping, keyboard hold."""
import math
import subprocess
import sys

import pytest

from fake_serial import FakeClock, PortFactory
from moss_dimos.diffdrive import DiffDriveConfig
from moss_dimos.teleop_logic import TeleopConfig
from moss_pi.serial_bridge import SerialBridge
from moss_pi.teleop import KeyboardAxes, TeleopSession, tracks_to_percent

CFG = TeleopConfig(drive=DiffDriveConfig(track_width_m=0.30, max_track_speed_mps=0.6),
                   max_yaw_rps=2.0, deadzone=0.08, brake_s=0.5, rate_hz=50.0)


def make():
    clock, ports = FakeClock(), PortFactory()
    bridge = SerialBridge(ports, clock=clock)
    bridge.tick()
    ports.port.written.clear()
    return TeleopSession(bridge, CFG), bridge, ports, clock


def run(session, bridge, clock, t0, t1, **inputs):
    """Step session and bridge every 20 ms over [t0, t1)."""
    actions = []
    for i in range(round((t1 - t0) / 0.02)):
        clock.t = t0 + i * 0.02
        actions.append(session.step(clock.t, **inputs))
        bridge.tick()
    return actions


# ---------------------------------------------------------------- duty mapping

def test_full_speed_maps_to_25_percent_and_0_24_mps_to_10():
    assert tracks_to_percent(0.6, 0.6, 0.6) == (25, 25)
    assert tracks_to_percent(0.24, -0.24, 0.6) == (10, -10)


def test_rounding_is_half_away_from_zero_and_clamped():
    assert tracks_to_percent(0.012, -0.012, 0.6) == (1, -1)   # 0.5 % -> 1
    assert tracks_to_percent(9.0, -9.0, 0.6) == (25, -25)
    with pytest.raises(ValueError):
        tracks_to_percent(math.nan, 0.0, 0.6)


# ---------------------------------------------------------------- session

def test_deadman_without_arm_sends_no_drive():
    session, bridge, ports, clock = make()
    actions = run(session, bridge, clock, 0.0, 1.0, arm_pressed=False, deadman_held=True, left_y=-1.0)
    assert set(actions) == {"not_armed"}
    assert not any(w.startswith(b"drive") for w in ports.port.written)


def test_arm_is_refused_while_the_deadman_is_held():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=True, left_y=-1.0)
    assert b"arm\n" not in ports.port.written


def test_full_forward_after_arm_is_drive_25_25():
    session, bridge, ports, clock = make()
    assert session.step(0.0, arm_pressed=True, deadman_held=False) == "arm"
    assert session.step(0.02, arm_pressed=False, deadman_held=True, left_y=-1.0) == "drive 25 25"
    assert ports.port.written == [b"arm\n", b"drive 25 25\n"]


def test_half_forward_after_deadzone_is_drive_13_13():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    # (0.54 - 0.08) / 0.92 = 0.5 of 0.6 m/s = 0.3 m/s -> 12.5 % -> 13
    assert session.step(0.02, arm_pressed=False, deadman_held=True, left_y=-0.54) == "drive 13 13"


def test_right_stick_right_turns_right_left_track_forward():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    # 2 rad/s * 0.15 m = 0.3 m/s per track -> 12.5 % -> 13, left forward, right back
    assert session.step(0.02, arm_pressed=False, deadman_held=True, right_x=1.0) == "drive 13 -13"


def test_release_brakes_with_zeros_for_0_5_s_then_stops_once():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    run(session, bridge, clock, 0.02, 1.02, arm_pressed=False, deadman_held=True, left_y=-1.0)
    ports.port.written.clear()
    actions = run(session, bridge, clock, 1.02, 2.02, arm_pressed=False, deadman_held=False)
    assert actions[0] == "brake"
    brake = [w for w in ports.port.written if w == b"drive 0 0\n"]
    assert 24 <= len(brake) <= 26                            # 0.5 s at 50 Hz
    assert ports.port.written[len(brake)] == b"stop\n"
    assert ports.port.written.count(b"stop\n") == 1          # the bridge deadman adds none
    assert not any(w.startswith(b"drive") and w != b"drive 0 0\n" for w in ports.port.written)
    assert not bridge.armed


def test_new_drive_after_release_needs_a_new_arm():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    run(session, bridge, clock, 0.02, 0.2, arm_pressed=False, deadman_held=True, left_y=-1.0)
    run(session, bridge, clock, 0.2, 1.0, arm_pressed=False, deadman_held=False)
    assert run(session, bridge, clock, 1.0, 1.1, arm_pressed=False, deadman_held=True, left_y=-1.0)[0] == "not_armed"


def test_a_stalled_loop_is_caught_by_the_bridge_deadman():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    session.step(0.02, arm_pressed=False, deadman_held=True, left_y=-1.0)
    ports.port.written.clear()
    clock.t = 0.32                  # the teleop loop hangs; only the bridge thread ticks
    bridge.tick()
    assert ports.port.written == [b"stop\n"]


def test_emergency_stop_writes_stop_and_disarms():
    session, bridge, ports, clock = make()
    session.step(0.0, arm_pressed=True, deadman_held=False)
    session.step(0.02, arm_pressed=False, deadman_held=True, left_y=-1.0)
    session.emergency_stop()
    assert ports.port.written[-1] == b"stop\n" and not bridge.armed


# ---------------------------------------------------------------- keyboard

def test_keyboard_w_is_forward_at_the_chosen_deflection_and_expires():
    keys = KeyboardAxes(speed=0.5, hold_s=0.6)
    keys.feed("w", 0.0)
    assert keys.sample(0.1) == (False, True, -0.5, 0.0)
    assert keys.sample(0.61) == (False, False, 0.0, 0.0)


def test_keyboard_d_turns_right_and_r_arms_once():
    keys = KeyboardAxes(speed=0.5)
    keys.feed("d", 0.0); keys.feed("r", 0.0)
    assert keys.sample(0.0) == (True, True, 0.0, 0.5)
    assert keys.sample(0.02)[0] is False


def test_keyboard_space_clears_everything_and_requests_stop():
    keys = KeyboardAxes()
    keys.feed("w", 0.0); keys.feed(" ", 0.1)
    assert keys.stop_requested and keys.sample(0.1)[1] is False


# ---------------------------------------------------------------- no dimOS

def test_moss_pi_imports_without_dimos_pyserial_or_pygame():
    code = ("import sys, moss_pi.serial_bridge, moss_pi.teleop, moss_pi.telemetry_log; "
            "bad = [m for m in ('dimos', 'serial', 'pygame', 'numpy') if m in sys.modules]; "
            "assert not bad, bad")
    subprocess.run([sys.executable, "-c", code], check=True)
