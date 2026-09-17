"""Gamepad teleop for MOSS - derived from vector-dimos/gamepad.py (Apache-2.0).

MOSS is a differential-drive tracked rover: the strafe axis (vy) published here is
ignored downstream by moss_dimos.diffdrive. Everything else (deadman, brake window,
hot-plug, headless SDL) is the VECTOR behaviour, unchanged and cold-tested there.
Not yet run on MOSS hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time
from typing import Any

# SDL picks its drivers at import time, so this has to run before "import
# pygame" (which happens lazily in the worker thread below). setdefault, not
# assignment: an operator who exports SDL_VIDEODRIVER=x11 keeps their display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # no banner in daemon logs

from dimos.core.core import rpc
from dimos.core.module import Module
from dimos.core.stream import Out
from dimos.msgs.geometry_msgs.Twist import Twist
from dimos.msgs.geometry_msgs.Vector3 import Vector3
from dimos.utils.logging_config import setup_logger

logger = setup_logger()

DEFAULT_LINEAR_SPEED = 0.6    # m/s at full stick
DEFAULT_ANGULAR_SPEED = 1.2   # rad/s at full stick
DEFAULT_DEADZONE = 0.32
DEFAULT_RATE_HZ = 50.0
DEFAULT_BOOST = 2.0
RESCAN_PERIOD_S = 2.0         # how often we re-scan SDL for a pad

# SDL axis indices on a standard dual-stick pad (DS4/DS5, Xbox, 8BitDo).
AXIS_LEFT_X = 0
AXIS_LEFT_Y = 1
AXIS_RIGHT_X = 2   # MEASURED 27/08 15h21: right-stick X sweeps axis 2 full travel on this pad/mode (axis 3 is its vertical leakage - the random rotation)
AXIS_R2 = 5


@dataclass(frozen=True)
class TeleopConfig:
    """Speed envelope for :func:`axes_to_twist` - no pygame, no module."""

    linear_speed: float = DEFAULT_LINEAR_SPEED
    angular_speed: float = DEFAULT_ANGULAR_SPEED
    deadzone: float = DEFAULT_DEADZONE
    boost_multiplier: float = DEFAULT_BOOST


def apply_deadzone(value: float, deadzone: float) -> float:
    """Hard deadzone: below the threshold the axis reads zero.

    No rescaling of the remaining travel - a stick just past the deadzone
    gives a small command, which is what you want for fine positioning.
    """
    return 0.0 if abs(value) < deadzone else value


# Absolute ceilings, applied LAST, regardless of config or boost. Born of the
# 27/08 13h42 runaway: a fresh xboxdrv delivered full-deflection uninitialised
# axes straight into tele_cmd_vel (priority channel, no guard anywhere) and
# the rover left at 1200 W. No teleop output may ever exceed these.
CLAMP_LINEAR_MS = 0.45
SLEW_LINEAR_MS2 = 0.6     # max change of linear command per second: full stick
                          # reaches the ceiling in ~0.75 s instead of one step -
                          # the mecanum wheelspin fix, on top of the 400 ms ZLAC
                          # ramps the adapter writes (the era tuning)
CLAMP_ANGULAR_RADS = 0.8
# Mecanum wheels ADD the commands: rim speed = |vx| + |vy| + (Lx+Ly)|wz|.
# Felt on the very first piloted lap (2026-08-27): mixing stick and rotation
# made the rover suddenly take off - each axis was under its own clamp while the
# wheels ran near double. Envelope = the fastest single-stick feel (0.45).
MECANUM_LEVER_M = 0.50    # Lx+Ly: half wheelbase 0.27 + half track 0.23 (54x46 cm chassis)
WHEEL_ENVELOPE_MS = 0.45  # max rim speed however the sticks are mixed
DEADMAN_BUTTON = 7        # MEASURED 2026-08-27: the chosen deadman button was pressed 21x -> index 7 (shanwan pad, Android mode). Held = commands allowed; released = zeros, always
BRAKE_S = 0.5             # how long the zeros keep flowing after the deadman is
                          # released - then TOTAL SILENCE until it is held again.
                          # dimOS's MovementManager reads ANY tele_cmd_vel message,
                          # zeros included, as "a human is driving": it cancels the
                          # nav goal and mutes nav_cmd_vel for tele_cooldown_sec
                          # (1.0 s). A pad at rest publishing 50 Hz of zeros
                          # therefore killed exploration for good (28/08 audit).
                          # 0.5 s < 1.0 s: the brake is seen, then autonomy gets
                          # the bus back and the two coexist.
# NOTE (2026-08-27): when this pad's radio dies mid-drive (sleep, battery -
# observed on a piloted lap), the rover STOPS cleanly - observed behaviour, no
# radio watchdog needed. Revisit ONLY if a radio death ever leaves a non-zero
# command running.


# ── 2026-09-13: metrox's two complaints from the 30/08 piloted lap ──────────
# (docs/notes_etabli.md, his words) :
#   "transitions de commandes pas propres : relacher un stick puis le remettre
#    vite -> lag / collision de commandes"
#   "inertie teleop excessive : stick lache -> le rover glisse encore ~1,5 m"
# One constant per button. Restoring the 2026-09-12 flight is one line each:
# BRAKE_CANCEL_ON_DEADMAN = False, and brake_s left alone (0.5 s).

BRAKE_CANCEL_ON_DEADMAN = True
# A new deadman press CANCELS whatever is left of the brake window, on its
# RISING EDGE (brake_until = 0.0). From that instant the brake path cannot emit
# one more zero, however long the window was.
#
# MEASURED on the cold bench 2026-09-13, BEFORE this change, at 50 Hz with
# BRAKE_S = 0.5 s and the deadman re-pressed 0.200 s after the release: the
# module already published the stick command from the first tick after the
# press (+0.213 s -> 0.012 m/s, one slew step) and no zero after it. So this
# does NOT change the default flight, and it is NOT the cure for the felt lag
# (that one is the slew restarting from rest: 0.6 m/s2 = 0.75 s to the ceiling).
# What it buys is the right to LENGTHEN the zero window (brake_s below) without
# a stale zero from the release ever chasing a fresh command down the bus -
# which is precisely what the anti-inertia button wants to do.
# False = the 12/09 behaviour exactly: the window always runs to its end.

# The length of that window is now a knob, not a literal. 0.5 s is the value
# flown since 28/08 (see BRAKE_S); the anti-inertia trial raises it towards
# 1.0 s so the drives keep being TOLD to stop for longer instead of falling
# silent and free-wheeling. dimOS builds this module from a blueprint with no
# arguments of ours, so the environment is the operator's only lever:
#     VECTOR_BRAKE_S=1.0 tools/fly.sh GAMEPAD=1 REPOSITIONNE=1
BRAKE_S_ENV = "VECTOR_BRAKE_S"
BRAKE_S_MAX = 1.0
# Why the ceiling is 1.0 and not more - the cost, in seconds, not a story.
# dimOS's MovementManager treats ANY tele_cmd_vel message, zeros included, as
# "a human is driving": _on_teleop cancels the nav goal on EVERY message and
# _on_nav refuses to forward nav_cmd_vel until tele_cooldown_sec = 1.0 s has
# passed since the LAST teleop message (movement_manager.py, re-read
# 2026-09-13). So every release mutes autonomy for brake_s + 1.0 s: 1.5 s
# today, 2.0 s at this ceiling. That number IS the justification.
# TWO CLAIMS THAT USED TO STAND HERE AND WERE FALSE (adversarial review,
# 2026-09-13) - written down so nobody rebuilds on them:
#  1. "above the ceiling a pad at rest would mute exploration FOR GOOD". No:
#     whatever brake_s is, the zeros STOP at brake_s (see the worker loop) and
#     autonomy comes back 1.0 s later. "For good" was the pre-28/08 module,
#     which published 50 Hz of zeros for ever. The ceiling is prudence about
#     the 2 s above, not a cliff.
#  2. "in the GAMEPAD=1 blueprint the gamepad IS the commander (direct drive
#     to cmd_vel, no nav), so the cost there is zero". That describes
#     `vector-dimos.gamepad` (blueprints.py remaps tele_cmd_vel -> cmd_vel).
#     tools/fly.sh runs `vector-dimos.explore`, where GAMEPAD=1 only ADDS this
#     module with NO remapping (nav_blueprints.py): the pad publishes on
#     tele_cmd_vel and MovementManager IS in the path. The cost on the flight
#     metrox actually runs is 2.0 s, not zero.

BRAKE_UNTIL_STOPPED = False
# ASKED FOR on 2026-09-13, and NOT implemented on purpose - here is why, so
# nobody re-opens it blind. The idea: keep publishing zeros until the wheels
# actually read below BRAKE_STOP_RPM, capped at BRAKE_STOP_MAX_S, then silence.
# It needs wheel-speed feedback INSIDE this module, and this module has none:
# GamepadTeleop declares exactly one stream, `tele_cmd_vel: Out[Twist]`, and it
# runs in its own forkserver worker. The RPM feedback is read by
# VectorBaseAdapter (adapter.read_velocities) in the COORDINATOR's process,
# and nothing publishes it anywhere this module could subscribe to. Wiring it
# would mean: a new Out on the coordinator, a new In here, a blueprint
# remapping, and a new failure mode (feedback stops arriving -> the brake never
# ends -> the pad mutes autonomy for ever) - i.e. new machinery inside an armed
# chain, which is the one thing the 27/08 incident says not to do.
# THE FALLBACK IS brake_s ABOVE: a longer window of zeros, no new plumbing, one
# environment variable. Setting this flag True changes nothing but a warning.
BRAKE_STOP_RPM = 5.0        # kept as the spec of the day we do wire feedback
BRAKE_STOP_MAX_S = 2.0      # ...and its safety cap, so silence always comes


def resolve_brake_s(brake_s: float | None = None,
                    env: dict | None = None) -> float:
    """How long zeros keep flowing after the deadman is released, in seconds.

    Pure, cold-testable. Precedence: explicit argument > VECTOR_BRAKE_S >
    BRAKE_S (0.5 s, the 28/08 value). Out-of-range values are CLAMPED to
    [0.0, BRAKE_S_MAX] and logged; unparseable text falls back to BRAKE_S,
    loudly - a mistyped knob gives yesterday's flight, never a random one.
    """
    raw: float | None = None if brake_s is None else float(brake_s)
    if raw is None:
        text = (os.environ if env is None else env).get(BRAKE_S_ENV, "")
        text = text.strip() if isinstance(text, str) else ""
        if text:
            try:
                raw = float(text)
            except ValueError:
                logger.warning("%s=%r is not a number - brake window stays at "
                               "%.2f s", BRAKE_S_ENV, text, BRAKE_S)
                raw = None
    if raw is None:
        return BRAKE_S
    value = max(0.0, min(BRAKE_S_MAX, raw))
    if value != raw:
        logger.warning("brake window %.2f s is outside [0.0, %.2f] s - clamped "
                       "to %.2f s (above the ceiling a released pad mutes "
                       "dimOS autonomy for good; see BRAKE_S_MAX)",
                       raw, BRAKE_S_MAX, value)
    return value


def brake_window_after_press(brake_until: float, deadman: bool,
                             prev_deadman: bool) -> float:
    """The brake deadline this tick keeps - pure, cold-testable.

    RISING edge of the deadman (released -> held) cancels the window by
    returning 0.0, which is always in the past: the brake path can no longer
    publish. Anything else returns the window untouched - in particular a
    deadman simply HELD, because every driving tick re-arms the window itself
    and that one must live its full brake_s after the next release.

    With BRAKE_CANCEL_ON_DEADMAN = False this is the identity function, i.e.
    exactly the 2026-09-12 flight.
    """
    if BRAKE_CANCEL_ON_DEADMAN and deadman and not prev_deadman:
        return 0.0
    return brake_until


def slew(prev: float, target: float, dt: float) -> float:
    """Rate-limit a linear command - pure, cold-testable."""
    step = SLEW_LINEAR_MS2 * dt
    return max(prev - step, min(prev + step, target))


def clamp_twist(vx: float, vy: float, wz: float) -> tuple[float, float, float]:
    """The last gate before the bus - pure, cold-testable. Per-axis clamps,
    then the mecanum wheel envelope: translation and rotation ADD at the rim,
    so a mixed command is scaled down proportionally (the feel is preserved,
    the top speed is not exceeded)."""
    lim = CLAMP_LINEAR_MS
    vx = max(-lim, min(lim, vx))
    vy = max(-lim, min(lim, vy))
    wz = max(-CLAMP_ANGULAR_RADS, min(CLAMP_ANGULAR_RADS, wz))
    rim = abs(vx) + abs(vy) + MECANUM_LEVER_M * abs(wz)
    if rim > WHEEL_ENVELOPE_MS:
        k = WHEEL_ENVELOPE_MS / rim
        vx, vy, wz = vx * k, vy * k, wz * k
    return (vx, vy, wz)


def axes_neutral(ax0: float, ax1: float, ax3: float, deadzone: float) -> bool:
    """True when every drive axis rests inside the deadzone - the trust gate:
    a pad (or a userspace driver) must be SEEN at neutral once before a single
    non-zero command is believed. Uninitialised axes never pass this."""
    return abs(ax0) < deadzone and abs(ax1) < deadzone and abs(ax3) < deadzone


def axes_to_twist(ax0: float, ax1: float, ax3: float, ax5: float,
                  cfg: TeleopConfig) -> tuple[float, float, float]:
    """Raw SDL axis values -> (vx m/s, vy m/s, wz rad/s).

    Pure function - the whole mapping lives here so it is testable without a
    pad, a display, or pygame.

    SDL reports stick up and stick left as NEGATIVE, while the robot frame is
    x forward / y left / wz counter-clockwise, hence the three sign flips:
        ax0 left stick X  -> vy   (stick left  = -1 -> strafe left,  +y)
        ax1 left stick Y  -> vx   (stick up    = -1 -> forward,      +x)
        ax3 right stick X -> wz   (stick right = +1 -> clockwise,    -wz)
        ax5 R2            -> boost when > 0 (trigger rests at -1)

    Boost multiplies the linear axes only: rotation stays at its capped rate,
    because a spin fast enough to be useful is already fast enough to hurt.
    """
    boost = cfg.boost_multiplier if ax5 > 0.0 else 1.0
    vx = -apply_deadzone(ax1, cfg.deadzone) * cfg.linear_speed * boost
    vy = -apply_deadzone(ax0, cfg.deadzone) * cfg.linear_speed * boost
    wz = -apply_deadzone(ax3, cfg.deadzone) * cfg.angular_speed
    return clamp_twist(vx, vy, wz)


class GamepadTeleop(Module):
    """pygame.joystick teleop. Outputs Twist on tele_cmd_vel."""

    dedicated_worker = True

    tele_cmd_vel: Out[Twist]

    def __init__(self, linear_speed: float = DEFAULT_LINEAR_SPEED,
                 angular_speed: float = DEFAULT_ANGULAR_SPEED,
                 deadzone: float = DEFAULT_DEADZONE,
                 rate_hz: float = DEFAULT_RATE_HZ,
                 boost_multiplier: float = DEFAULT_BOOST,
                 joystick_index: int = 0, brake_s: float | None = None,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = TeleopConfig(linear_speed=linear_speed,
                                angular_speed=angular_speed,
                                deadzone=deadzone,
                                boost_multiplier=boost_multiplier)
        self.rate_hz = rate_hz
        self.joystick_index = joystick_index
        # 2026-09-13: None -> BRAKE_S (0.5 s), or VECTOR_BRAKE_S. Resolved HERE,
        # at construction, so the value is fixed and logged once for a flight -
        # not re-read per tick.
        self.brake_s = resolve_brake_s(brake_s)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # @rpc is not decoration for its own sake: Module.start/stop carry it,
    # and an override that drops it falls out of the class's rpcs table.
    # dimOS then proxies the call by pickling the module across the worker
    # pipe, which dies on our threading.Event ('cannot pickle _thread.lock').
    @rpc
    def start(self) -> None:
        super().start()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker,
                                        name="vector-gamepad", daemon=True)
        self._thread.start()

    @rpc
    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        super().stop()

    def _publish(self, vx: float, vy: float, wz: float) -> None:
        self.tele_cmd_vel.publish(Twist(
            linear=Vector3(x=vx, y=vy, z=0.0),
            angular=Vector3(x=0.0, y=0.0, z=wz)))

    def _acquire(self, pygame: Any) -> Any:
        """Re-scan SDL for the pad. Returns an initialised joystick or None."""
        try:
            pygame.event.pump()          # let SDL process hotplug events
            pygame.joystick.quit()       # full re-scan: SDL caches the device
            pygame.joystick.init()       # list from the last init()
            if pygame.joystick.get_count() <= self.joystick_index:
                return None
            pad = pygame.joystick.Joystick(self.joystick_index)
            pad.init()
            return pad
        except pygame.error as exc:
            logger.debug("Gamepad scan failed: %s", exc)
            return None

    # Named _worker, NOT _loop: dimOS's Module keeps its asyncio event
    # loop in self._loop, which would shadow the method and make the
    # thread target the event loop object.
    def _worker(self) -> None:
        try:
            import pygame
        except ImportError:
            logger.error("pygame is not installed - gamepad teleop is off "
                         "(pip install 'vector-dimos[gamepad]')")
            return

        pygame.init()  # dummy video/audio drivers: works with no display
        pygame.joystick.init()
        period = 1.0 / self.rate_hz
        pad = None
        trusted = False            # neutral-first trust gate (13h42 runaway)
        prev_vx = prev_vy = 0.0    # slew-limiter state
        brake_until = 0.0          # publish zeros until this instant, then shut up
        prev_deadman = False       # to see the RISING edge of the deadman (2026-09-13)
        waiting_logged = False
        if BRAKE_UNTIL_STOPPED:
            # Declared, never wired - see the constant. Say so at every start
            # rather than let an operator believe in a brake that is not there.
            logger.warning("BRAKE_UNTIL_STOPPED=True is INERT: this module has "
                           "no wheel-speed feedback (see the constant). The "
                           "brake window stays at %.2f s - raise it with %s.",
                           self.brake_s, BRAKE_S_ENV)
        logger.info("gamepad brake window: %.2f s of zeros after the deadman is "
                    "released, then silence (cancel-on-press: %s)",
                    self.brake_s, BRAKE_CANCEL_ON_DEADMAN)
        try:
            while not self._stop_event.is_set():
                if pad is None:
                    pad = self._acquire(pygame)
                    if pad is None:
                        if not waiting_logged:
                            logger.info("waiting for gamepad (index %d)",
                                        self.joystick_index)
                            waiting_logged = True
                        self._stop_event.wait(RESCAN_PERIOD_S)
                        continue
                    waiting_logged = False
                    trusted = False   # every (re)connection re-earns trust at neutral
                    logger.info("Gamepad connected: %s - waiting to see the sticks at NEUTRAL "
                                "before trusting a single command", pad.get_name())
                try:
                    pygame.event.pump()
                    axes = (_axis(pad, AXIS_LEFT_X), _axis(pad, AXIS_LEFT_Y),
                            _axis(pad, AXIS_RIGHT_X), _axis(pad, AXIS_R2))
                    deadman = bool(pad.get_button(DEADMAN_BUTTON)) if pad.get_numbuttons() > DEADMAN_BUTTON else False
                    if pygame.joystick.get_count() <= self.joystick_index:
                        raise pygame.error("joystick disappeared")
                except pygame.error as exc:
                    pad = None
                    trusted = False
                    prev_deadman = False          # a pad that is gone holds nothing
                    # ... and it holds no RAMP either (2026-09-13, adversarial
                    # bench). prev_vx/prev_vy were reset on the deadman RELEASE
                    # path only, so a pad that vanished for one read while
                    # driving at the ceiling came back with 0.45 m/s of slew
                    # state: the first trusted tick, STICKS AT NEUTRAL, published
                    # +0.438 m/s and the rover left on its own for ~0.75 s -
                    # the exact 28/08 replay the release path was written to
                    # kill. The trust gate does not catch it: neutral axes
                    # satisfy the gate, and the danger is inside this module.
                    prev_vx = prev_vy = 0.0
                    self._publish(0.0, 0.0, 0.0)  # one zero Twist, then wait
                    logger.warning("Gamepad lost (%s) - back to waiting", exc)
                    continue
                # TRUST GATE (the 13h42 runaway): until the sticks have been
                # SEEN at neutral once, this pad's words are worth nothing.
                if not trusted:
                    if axes_neutral(axes[0], axes[1], axes[2], self.cfg.deadzone):
                        trusted = True
                        logger.info("Gamepad axes seen at neutral - commands now trusted "
                                    "(hold the deadman button to drive)")
                    else:
                        if time.monotonic() < brake_until:
                            self._publish(0.0, 0.0, 0.0)
                        time.sleep(period)
                        continue
                # BRAKE CANCEL (2026-09-13, metrox 30/08 "collision de
                # commandes"): the RISING edge of the deadman ends the brake
                # window there and then, so not one zero left over from the
                # release can still go out behind the commands of the new
                # press. Rising edge, not "held": a window re-armed by a tick
                # that DROVE (below) must keep its own life.
                # Set BRAKE_CANCEL_ON_DEADMAN = False to fly the 12/09 way.
                #
                # ORDER MATTERS, and it was WRONG for a few hours on 2026-09-13
                # (caught by an adversarial cold bench, fixed the same day):
                # these two lines used to sit ABOVE the trust gate. On any pad
                # that has not yet earned trust - i.e. after EVERY reconnection,
                # and after every one-tick read glitch, which is exactly when
                # the rover is rolling with nobody commanding it - a deadman
                # press cancelled the brake window while the untrusted path
                # could publish NOTHING to replace it. Measured on that bench:
                # a single missed read at 0.45 m/s took the zeros published
                # after the dropout from 25 (to 0.486 s) down to 1 (0.011 s).
                # BRAKE_S exists to REPEAT the stop order on a latest-only bus;
                # the cancel may therefore only run on a tick that is itself
                # about to publish a command - i.e. here, below the gate.
                brake_until = brake_window_after_press(brake_until, deadman,
                                                       prev_deadman)
                prev_deadman = deadman
                # DEADMAN: no held button, no motion - ever.
                if not deadman:
                    # Releasing also resets the slew state: the ramp restarts
                    # from rest, so a re-press with the sticks centred cannot
                    # replay the last driven speed (28/08 audit: 0.44 m/s for
                    # ~0.75 s, sticks at rest).
                    prev_vx = prev_vy = 0.0
                    # BRAKE THEN SILENCE (see BRAKE_S / self.brake_s): zeros for
                    # brake_s after the last command, then not one message until
                    # the deadman is held again - a released pad must not mute
                    # autonomy.
                    if time.monotonic() < brake_until:
                        self._publish(0.0, 0.0, 0.0)
                    time.sleep(period)
                    continue
                vx, vy, wz = axes_to_twist(*axes, self.cfg)
                vx = slew(prev_vx, vx, period)
                vy = slew(prev_vy, vy, period)
                prev_vx, prev_vy = vx, vy
                # envelope AFTER the slew too: while vx decays and wz is
                # instant, the mix could transiently exceed the rim ceiling
                vx, vy, wz = clamp_twist(vx, vy, wz)
                self._publish(vx, vy, wz)
                brake_until = time.monotonic() + self.brake_s
                time.sleep(period)
        finally:
            try:
                self._publish(0.0, 0.0, 0.0)
            except Exception:  # stream already torn down: nothing to do
                logger.debug("no zero Twist on shutdown", exc_info=True)
            pygame.joystick.quit()
            pygame.quit()


def _axis(pad: Any, index: int) -> float:
    """Axis value, or 0.0 when this pad has no such axis.

    Pads differ (some report 4 axes, not 6). A missing R2 must read as "no
    boost", not throw the loop into the reconnect path on every tick.
    """
    if index >= pad.get_numaxes():
        return 0.0
    return float(pad.get_axis(index))
