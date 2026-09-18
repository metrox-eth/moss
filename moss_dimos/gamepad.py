"""Gamepad teleop for MOSS as a dimOS module: reads a pygame joystick, publishes Twist.

All decision logic lives in `moss_dimos.teleop_logic` (pure, cold-tested here);
this file only wires it to pygame and to the dimOS stream. Runs headless (SDL
dummy drivers) and waits for a pad instead of failing at startup.

Not yet run on the MOSS base: there is no motor driver module in this
repository yet (see docs/software.md).
"""
from __future__ import annotations

import os
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from dimos.core.core import rpc
from dimos.core.module import Module
from dimos.core.stream import Out
from dimos.msgs.geometry_msgs.Twist import Twist
from dimos.msgs.geometry_msgs.Vector3 import Vector3
from dimos.utils.logging_config import setup_logger

from .teleop_logic import DeadmanBrake, TeleopConfig, axes_to_twist

logger = setup_logger()

# Standard dual-stick pad (pygame numbering). Override through the constructor.
AXIS_LEFT_Y = 1
AXIS_RIGHT_X = 2
BUTTON_DEADMAN = 4   # L1
BUTTON_BOOST = 5     # R1


class GamepadTeleop(Module):
    """Publishes `tele_cmd_vel` while the deadman is held, zeros for brake_s after, then nothing."""

    tele_cmd_vel: Out[Twist]

    def __init__(self, config: TeleopConfig | None = None, axis_left_y: int = AXIS_LEFT_Y,
                 axis_right_x: int = AXIS_RIGHT_X, button_deadman: int = BUTTON_DEADMAN,
                 button_boost: int = BUTTON_BOOST, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cfg = config or TeleopConfig()
        self.axis_left_y, self.axis_right_x = axis_left_y, axis_right_x
        self.button_deadman, self.button_boost = button_deadman, button_boost
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @rpc
    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="moss-gamepad", daemon=True)
        self._thread.start()

    @rpc
    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _publish(self, vx: float, wz: float) -> None:
        self.tele_cmd_vel.publish(Twist(linear=Vector3(x=vx, y=0.0, z=0.0), angular=Vector3(x=0.0, y=0.0, z=wz)))

    def _loop(self) -> None:
        import pygame  # optional dependency: pip install 'moss-dimos[gamepad]'

        pygame.init()
        pygame.joystick.init()
        period = 1.0 / self.cfg.rate_hz
        brake = DeadmanBrake(self.cfg.brake_s)
        pad = None
        while not self._stop.is_set():
            if pad is None:
                pygame.joystick.quit(); pygame.joystick.init()
                if pygame.joystick.get_count() == 0:
                    time.sleep(1.0); continue
                pad = pygame.joystick.Joystick(0); pad.init()
                logger.info(f"gamepad connected: {pad.get_name()}")
            pygame.event.pump()
            try:
                held = bool(pad.get_button(self.button_deadman))
                boost = bool(pad.get_button(self.button_boost))
                ly, rx = pad.get_axis(self.axis_left_y), pad.get_axis(self.axis_right_x)
            except pygame.error:
                logger.warning("gamepad lost; publishing zeros then waiting for it")
                self._publish(0.0, 0.0); pad = None; continue
            state = brake.tick(held, time.monotonic())
            if state == "command":
                vx, wz = axes_to_twist(ly, rx, self.cfg, boost_held=boost)
                self._publish(vx, wz)
            elif state == "brake":
                self._publish(0.0, 0.0)
            time.sleep(period)
