"""The SO-101's Feetech servos as a dimOS manipulator adapter.

`FeetechSo101Adapter` is what the coordinator creates for the `feetech_so101`
hardware type (registered in `moss_dimos.blueprints`): six servos on one
bus, the five arm joints in the model's radians and the gripper as the jaw
gap in metres, the units `moss_dimos.arm` uses everywhere. Ticks come and go
through the keep-out table's joint map (2048 at the model's zero, sign +1,
`moss_dimos.arm_guard.JointMap`) and the calibration file (the servos'
homing offsets and end stops); the gripper's ticks follow the straight
line through the open and grasp values of config/arm_drop_poses.json.

Per coordinator tick: one read of every servo's present position (register
56), then one goal write (register 42) for every servo whose target moved
by a tick or more. Goal speed (46) and acceleration (41) are set once at
connect: the servo's own ceiling, so a streamed position cannot ask more
than the sweep's speed. Torque (40) goes on at activate, after every goal
register has been set to the present position (a servo enables onto the
goal its register holds, and would jump to a stale one), and off at
deactivate; the gripper's force limit goes to registers 44 and 48 at
connect.

What the adapter watches, because the coordinator does not: the following
error. Every read compares each arm servo's present position with its last
goal; a servo more than `lag_ticks` from its goal and not moving (under
`still_ticks_per_s`) for longer than `lag_s` sets the error code
FOLLOWING_ERROR in `read_error()`, which the executor polls (the shoulder
short of its target under load, stopped, is the case; a servo still on
its way to a far goal is not).
A read that fails leaves the last positions in place and, after
`stale_s`, `has_live_state()` turns False so the coordinator stops
commanding.

The bus is scservo_sdk (PortHandler, PacketHandler protocol 0, 1 Mbps),
wrapped in `FeetechBus` so a bench can hand in a fake with the same four
calls. The SDK raises IndexError on a truncated reply: every call is
retried up to three times.

A joint can have a twin: a second servo on the same axis, back to back
with the first (the shoulder since the dual-servo bracket), declared in the
calibration file as `"<joint>_twin": {"id": 7, "of": "<joint>",
"sum_ticks": 4094}`. The twin counts the other way, so at every pose
`twin + joint = sum_ticks` (both set to read mirror positions about the
middle, 2047 + p and 2047 - p, the way the RoArm-M3 firmware runs its two
shoulder servos). The twin gets the joint's goal mirrored, in the same
sync-write packet as every goal (register 42; speed and acceleration are
set per servo before), the same torque on and off, and its goal latched to
its own reading before torque goes on. At connect, and on every read while
torque is on, the two readings are compared: a twin further than
TWIN_TOL_TICKS from its mirror refuses the connection (something slipped or
the zeros are stale), further than TWIN_FIGHT_TICKS under torque sets
TWIN_ERROR.
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any

from moss_dimos import arm as A
from moss_dimos.arm_guard import JointMap, CALIBRATION_PATH as GUARD_CALIBRATION_PATH, TABLE_PATH

REG_TORQUE, REG_ACC, REG_GOAL, REG_SPEED, REG_PRESENT = 40, 41, 42, 46, 56
GRIPPER_FORCE_REGS = (44, 48)
BAUD = 1_000_000
PROTOCOL = 0
SERVO_IDS = {"shoulder_pan": 1, "shoulder_lift": 2, "elbow_flex": 3, "wrist_flex": 4, "wrist_roll": 5, "gripper": 6}
RETRIES = 3
BUS_ERROR, FOLLOWING_ERROR, TWIN_ERROR = 1, 2, 3
TWIN_TOL_TICKS = 25        # a twin this far from its mirror at connect: not the same zero, refuse
TWIN_FIGHT_TICKS = 40      # under torque: the bracket does not flex this much, the two are fighting
DEFAULT_SPEED = int(A.SPEED_TICKS_PER_S)   # register 46: steps per second
DEFAULT_ACC = 50                           # register 41: units of 100 steps per second squared
DEFAULT_LAG_TICKS = 150                    # 13 degrees
DEFAULT_LAG_S = 1.0
DEFAULT_STILL_TICKS_PER_S = 20.0           # below this the servo counts as stopped
DEFAULT_STALE_S = 0.5
GRIPPER_FORCE = 400
# the gripper's line when config/arm_drop_poses.json is not there
GRIPPER_LINE_DEFAULT = ((3674, 0.090), (2780, 0.053))


def _signed(v: int) -> int:
    """A present position as the servo sends it: bit 15 is the sign."""
    return -(v & 0x7FFF) if v & 0x8000 else int(v)


class FeetechBus:
    """scservo_sdk behind four calls; opened lazily so a missing SDK fails at connect."""

    def __init__(self, port: str, baud: int = BAUD) -> None:
        self.port, self.baud = port, baud
        self._scs = self._ph = self._pk = None

    def open(self) -> bool:
        import scservo_sdk as scs  # noqa: PLC0415 - the robot's venv has it

        ph = scs.PortHandler(self.port)
        if not ph.openPort() or not ph.setBaudRate(self.baud):
            return False
        self._scs, self._ph, self._pk = scs, ph, scs.PacketHandler(PROTOCOL)
        return True

    def close(self) -> None:
        if self._ph is not None:
            try:
                self._ph.closePort()
            except Exception:  # noqa: BLE001
                pass
        self._scs = self._ph = self._pk = None

    def read2(self, sid: int, addr: int) -> int | None:
        for _ in range(RETRIES):
            try:
                v, comm, _err = self._pk.read2ByteTxRx(self._ph, sid, addr)
                if comm == self._scs.COMM_SUCCESS:
                    return int(v)
            except Exception:  # noqa: BLE001 - a short packet inside the SDK
                pass
        return None

    def _write(self, fn, sid: int, addr: int, value: int) -> bool:
        for _ in range(RETRIES):
            try:
                comm, _err = fn(self._ph, sid, addr, int(value))
                if comm == self._scs.COMM_SUCCESS:
                    return True
            except Exception:  # noqa: BLE001
                pass
        return False

    def write1(self, sid: int, addr: int, value: int) -> bool:
        return self._write(self._pk.write1ByteTxRx, sid, addr, value)

    def write2(self, sid: int, addr: int, value: int) -> bool:
        return self._write(self._pk.write2ByteTxRx, sid, addr, value)

    def sync_write2(self, addr: int, values: dict[int, int]) -> bool:
        """One packet carrying a two-byte value for several servos: every servo
        applies its value when the packet ends, so a joint and its twin move on
        the same instant. No reply on the bus for a sync write."""
        if not values:
            return True
        gw = self._scs.GroupSyncWrite(self._ph, self._pk, addr, 2)
        for sid, v in values.items():
            v = int(v) & 0xFFFF
            gw.addParam(int(sid), [v & 0xFF, v >> 8])
        for _ in range(RETRIES):
            try:
                if gw.txPacket() == self._scs.COMM_SUCCESS:
                    return True
            except Exception:  # noqa: BLE001
                pass
        return False


def gripper_line(poses_path: str | os.PathLike | None = None) -> tuple[tuple[int, float], tuple[int, float]]:
    """(ticks, gap m) at open and at grasp, from the cycle's JSON when present."""
    path = Path(poses_path) if poses_path else A.POSES_PATH
    if path.is_file():
        g = json.loads(path.read_text()).get("gripper") or {}
        if "open" in g and "grasp" in g:
            return ((int(g["open"]["ticks"]), float(g["open"]["gap_mm"]) / 1000.0),
                    (int(g["grasp"]["ticks"]), float(g["grasp"]["gap_mm"]) / 1000.0))
    return GRIPPER_LINE_DEFAULT


class FeetechSo101Adapter:
    """`ManipulatorAdapter` for the SO-101 on Feetech STS3215 servos (and the
    gripper's servo), units of moss_dimos.arm."""

    def __init__(self, dof: int = 6, address: str | None = None, hardware_id: str | None = None,
                 *, calibration: str | None = None, table: str | None = None, poses: str | None = None,
                 ids: dict | None = None, speed: int = DEFAULT_SPEED, acc: int = DEFAULT_ACC,
                 lag_ticks: float = DEFAULT_LAG_TICKS, lag_s: float = DEFAULT_LAG_S, stale_s: float = DEFAULT_STALE_S,
                 still_ticks_per_s: float = DEFAULT_STILL_TICKS_PER_S,
                 gripper_force: int = GRIPPER_FORCE, bus: Any | None = None,
                 twin: dict | None = None, **_: Any) -> None:
        if dof != len(A.JOINT_NAMES):
            raise ValueError(f"feetech_so101 drives {len(A.JOINT_NAMES)} joints, not {dof}")
        self._dof = dof
        self._hardware_id = hardware_id
        self._port = str(address) if address else A.arm_port()
        self._calibration = Path(calibration) if calibration else GUARD_CALIBRATION_PATH
        self._table = Path(table) if table else TABLE_PATH
        self._ids = dict(ids or SERVO_IDS)
        self._speed, self._acc = int(speed), int(acc)
        self._lag_ticks, self._lag_s, self._stale_s = float(lag_ticks), float(lag_s), float(stale_s)
        self._still = float(still_ticks_per_s)
        self._tick_vel: dict[str, float] = {}     # ticks per second, from the last two reads
        self._prev_read: tuple[float, dict[str, int]] | None = None
        self._gripper_force = int(gripper_force)
        self._bus = bus
        self._owns_bus = bus is None
        # (joint, servo id, sum_ticks) of the joint's twin: given here, else the calibration file's
        self._twin: tuple[str, int, int] | None = self._twin_from(twin) if twin else None
        self._present_twin: int | None = None
        self._goal_twin: int | None = None
        self._twin_gap = 0                       # the twin's reading minus its mirror, last read
        self._map: JointMap | None = None
        self._ranges: dict[str, tuple[int, int]] = {}
        (self._g_open_ticks, self._g_open_m), (self._g_grasp_ticks, self._g_grasp_m) = gripper_line(poses)
        self._ticks_per_m = (self._g_open_ticks - self._g_grasp_ticks) / (self._g_open_m - self._g_grasp_m)
        self._connected = False
        self._enabled = False
        self._present: dict[str, int] = {}       # the last good read, ticks
        self._goal: dict[str, int] = {}          # the last goal written, ticks
        self._last_good = 0.0
        self._lag_since: dict[str, float] = {}
        self._error = (0, "")
        self._prev: tuple[float, list[float]] | None = None
        self._velocities = [0.0] * dof
        self._control_mode = None

    # ── units ──

    def _joints(self) -> list[str]:
        return [*A.ARM_JOINTS, A.GRIPPER]

    # ── the twin ──

    @staticmethod
    def _twin_from(rec: dict, name: str | None = None) -> tuple[str, int, int] | None:
        """(joint, id, sum_ticks) from a calibration record `{"id", "of", "sum_ticks"}`."""
        if not isinstance(rec, dict) or "id" not in rec:
            return None
        joint = rec.get("of") or (name[: -len("_twin")] if name and name.endswith("_twin") else None)
        if joint not in A.ARM_JOINTS:
            return None
        return (str(joint), int(rec["id"]), int(rec.get("sum_ticks", 2 * (A.TICKS_PER_REV // 2 - 1))))

    def twin(self) -> tuple[str, int, int] | None:
        """(joint, servo id, sum_ticks) of the twin, None without one."""
        return self._twin

    def twin_name(self) -> str | None:
        return f"{self._twin[0]}_twin" if self._twin else None

    def servo_ids_for(self, joint: str) -> list[int]:
        """The servo ids that move this joint: its own, and its twin's after it."""
        ids = [self._ids[joint]]
        if self._twin and self._twin[0] == joint:
            ids.append(self._twin[1])
        return ids

    def servo_table(self) -> list[tuple[str, int]]:
        """(name, id) of every servo on the arm, the twin named `<joint>_twin`."""
        out = [(j, self._ids[j]) for j in self._joints()]
        if self._twin:
            out.append((self.twin_name(), self._twin[1]))
        return out

    def twin_goal_for(self, joint_goal: int) -> int:
        return (self._twin[2] - int(joint_goal)) % A.TICKS_PER_REV

    def twin_gap(self) -> int:
        """The twin's last reading minus the mirror of its joint's, in [-2048, 2048)."""
        return self._twin_gap

    def _check_twin(self) -> int | None:
        if not self._twin or self._present_twin is None:
            return None
        joint = self._twin[0]
        p = self._present.get(joint)
        if p is None:
            return None
        gap = (self._present_twin - self.twin_goal_for(p) + A.TICKS_PER_REV // 2) % A.TICKS_PER_REV - A.TICKS_PER_REV // 2
        self._twin_gap = int(gap)
        return self._twin_gap

    def gap_to_ticks(self, gap_m: float) -> int:
        gap = min(max(float(gap_m), A.GAP_CLOSED_M), A.GAP_OPEN_M)
        return int(round(self._g_open_ticks + (gap - self._g_open_m) * self._ticks_per_m))

    def ticks_to_gap(self, ticks: float) -> float:
        return self._g_open_m + (float(ticks) - self._g_open_ticks) / self._ticks_per_m

    def rad_to_ticks(self, joint: str, rad: float) -> int:
        t = self._map.rad_to_ticks(joint, rad) if self._map else A.rad_to_ticks(rad)
        lo, hi = self._ranges.get(joint, (0, A.TICKS_PER_REV - 1))
        return int(min(max(t, lo), hi))

    def ticks_to_rad(self, joint: str, ticks: float) -> float:
        return self._map.ticks_to_rad(joint, ticks) if self._map else A.ticks_to_rad(ticks)

    # ── lifecycle ──

    def connect(self) -> bool:
        if self._bus is None:
            self._bus = FeetechBus(self._port)
        if self._owns_bus and not self._bus.open():
            self._error = (BUS_ERROR, f"cannot open {self._port}")
            return False
        try:
            self._map = JointMap.load(self._calibration, self._table)
        except Exception as exc:  # noqa: BLE001 - no table or calibration: the plain rule
            self._map = None
            self._error = (0, f"joint map not loaded ({exc}); the plain 2048 rule is used")
        if self._calibration.is_file():
            doc = json.loads(self._calibration.read_text())
            for j in A.ARM_JOINTS:
                rec = doc.get(j) or {}
                if "range_min" in rec and "range_max" in rec:
                    self._ranges[j] = (int(rec["range_min"]), int(rec["range_max"]))
            g = doc.get("gripper") or {}
            if "range_min" in g and "range_max" in g:
                self._ranges[A.GRIPPER] = (int(g["range_min"]), int(g["range_max"]))
            if self._twin is None:
                for name, rec in doc.items():
                    if isinstance(name, str) and name.endswith("_twin"):
                        self._twin = self._twin_from(rec, name)
                        if self._twin:
                            break
        if self._read_all() is None:
            self._error = (BUS_ERROR, "the servos do not answer")
            return False
        gap = self._check_twin()
        if gap is not None and abs(gap) > TWIN_TOL_TICKS:
            self._error = (TWIN_ERROR, f"{self.twin_name()} (id {self._twin[1]}) reads {gap:+d} ticks off the mirror of "
                                       f"{self._twin[0]}: not the same zero, torque would fight; not connecting")
            return False
        ok = True
        for j in A.ARM_JOINTS:
            for sid in self.servo_ids_for(j):
                ok &= self._bus.write1(sid, REG_ACC, self._acc)
                ok &= self._bus.write2(sid, REG_SPEED, self._speed)
        gid = self._ids[A.GRIPPER]
        for reg in GRIPPER_FORCE_REGS:
            ok &= self._bus.write2(gid, reg, self._gripper_force)
        if not ok:
            self._error = (BUS_ERROR, "a servo did not take its speed, acceleration or force setting")
            return False
        self._goal = dict(self._present)
        self._goal_twin = self._present_twin
        self._connected = True
        return True

    def disconnect(self) -> None:
        if self._connected and self._enabled:
            try:
                self.write_enable(False)
            except Exception:  # noqa: BLE001
                pass
        if self._owns_bus and self._bus is not None:
            self._bus.close()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def has_live_state(self) -> bool:
        return self._connected and (time.monotonic() - self._last_good) < self._stale_s

    def activate(self) -> bool:
        return self.write_enable(True)

    def deactivate(self) -> bool:
        self.write_stop()
        return self.write_enable(False)

    def get_info(self):
        from dimos.hardware.manipulators.spec import ManipulatorInfo

        return ManipulatorInfo(vendor="Feetech", model="SO-101 STS3215", dof=self._dof,
                               firmware_version=None, serial_number=None)

    def get_dof(self) -> int:
        return self._dof

    def get_limits(self):
        try:
            from dimos.hardware.spec import JointLimits
        except ImportError:  # the robot's dimOS keeps it with the manipulator spec
            from dimos.hardware.manipulators.spec import JointLimits

        lo, hi = [], []
        for j in A.ARM_JOINTS:
            r = self._ranges.get(j)
            lo.append(self.ticks_to_rad(j, r[0]) if r else -math.pi)
            hi.append(self.ticks_to_rad(j, r[1]) if r else math.pi)
        return JointLimits(position_lower=[*lo, A.GAP_CLOSED_M], position_upper=[*hi, A.GAP_OPEN_M],
                           velocity_max=[self._speed / A.TICKS_PER_RAD] * A.ARM_DOF + [A.GRIPPER_SPEED_M_PER_S])

    def set_control_mode(self, mode) -> bool:
        from dimos.hardware.manipulators.spec import ControlMode

        self._control_mode = mode
        return mode in (ControlMode.POSITION, ControlMode.SERVO_POSITION)

    def get_control_mode(self):
        from dimos.hardware.manipulators.spec import ControlMode

        return self._control_mode or ControlMode.POSITION

    # ── reads ──

    def _read_all(self) -> dict[str, int] | None:
        out: dict[str, int] = {}
        for j in self._joints():
            v = self._bus.read2(self._ids[j], REG_PRESENT)
            if v is None:
                return None
            out[j] = _signed(v)
        if self._twin:
            v = self._bus.read2(self._twin[1], REG_PRESENT)
            if v is None:
                return None
            self._present_twin = _signed(v)
        now = time.monotonic()
        if self._prev_read is not None and now > self._prev_read[0]:
            dt = now - self._prev_read[0]
            self._tick_vel = {j: (out[j] - self._prev_read[1].get(j, out[j])) / dt for j in out}
        self._prev_read = (now, dict(out))
        self._present = out
        self._last_good = now
        self._watch_lag(now)
        return out

    def _watch_lag(self, now: float) -> None:
        if not self._enabled:
            self._lag_since.clear()
            return
        lagging = None
        for j in A.ARM_JOINTS:
            g = self._goal.get(j)
            p = self._present.get(j)
            if g is None or p is None:
                continue
            if abs(g - p) > self._lag_ticks and abs(self._tick_vel.get(j, 0.0)) < self._still:
                self._lag_since.setdefault(j, now)
                if now - self._lag_since[j] >= self._lag_s and lagging is None:
                    lagging = (j, g - p, now - self._lag_since[j])
            else:
                self._lag_since.pop(j, None)
        if lagging is not None:
            j, d, s = lagging
            self._error = (FOLLOWING_ERROR, f"{j} is {abs(d):.0f} ticks {'short of' if d > 0 else 'past'} its goal for {s:.1f} s")
        elif self._error[0] == FOLLOWING_ERROR:
            self._error = (0, "")
        gap = self._check_twin()
        if gap is not None and abs(gap) > TWIN_FIGHT_TICKS:
            self._error = (TWIN_ERROR, f"{self.twin_name()} reads {gap:+d} ticks off the mirror of {self._twin[0]} under torque")
        elif self._error[0] == TWIN_ERROR:
            self._error = (0, "")

    def read_joint_positions(self) -> list[float]:
        got = self._read_all()
        src = got if got is not None else self._present
        if not src:
            return [0.0] * self._dof
        q = [self.ticks_to_rad(j, src[j]) for j in A.ARM_JOINTS] + [self.ticks_to_gap(src[A.GRIPPER])]
        now = time.monotonic()
        if got is not None and self._prev is not None and now > self._prev[0]:
            dt = now - self._prev[0]
            self._velocities = [(b - a) / dt for a, b in zip(self._prev[1], q)]
        if got is not None:
            self._prev = (now, q)
        return q

    def read_joint_velocities(self) -> list[float]:
        return list(self._velocities)

    def read_joint_efforts(self) -> list[float]:
        return [0.0] * self._dof

    def read_state(self) -> dict[str, int]:
        moving = any(abs(v) > 1e-3 for v in self._velocities)
        return {"state": 1 if moving else 0, "mode": 0}

    def read_error(self) -> tuple[int, str]:
        return self._error

    def present_ticks(self) -> dict[str, int]:
        out = dict(self._present)
        if self._twin and self._present_twin is not None:
            out[self.twin_name()] = self._present_twin
        return out

    def goal_ticks(self) -> dict[str, int]:
        out = dict(self._goal)
        if self._twin and self._goal_twin is not None:
            out[self.twin_name()] = self._goal_twin
        return out

    # ── writes ──

    def _send_goals(self, want: dict[str, int]) -> bool:
        """The goals that changed, joints and twin, in one sync-write packet
        (one write per servo on a bus without sync writes)."""
        by_id: dict[int, int] = {}
        names: dict[int, str] = {}
        for j, t in want.items():
            if self._goal.get(j) != t:
                by_id[self._ids[j]] = t
                names[self._ids[j]] = j
            if self._twin and self._twin[0] == j:
                tg = self.twin_goal_for(t)
                if self._goal_twin != tg or self._goal.get(j) != t:
                    by_id[self._twin[1]] = tg
                    names[self._twin[1]] = self.twin_name()
        if not by_id:
            return True
        if hasattr(self._bus, "sync_write2"):
            ok = self._bus.sync_write2(REG_GOAL, by_id)
            done = dict(by_id) if ok else {}
        else:
            done = {sid: t for sid, t in by_id.items() if self._bus.write2(sid, REG_GOAL, t)}
            ok = len(done) == len(by_id)
        for sid, t in done.items():
            if self._twin and sid == self._twin[1]:
                self._goal_twin = t
            else:
                self._goal[names[sid]] = t
        return ok

    def write_joint_positions(self, positions: list[float], velocity: float = 1.0) -> bool:
        if not self._connected or not self._enabled or len(positions) != self._dof:
            return False
        want = {j: self.rad_to_ticks(j, positions[i]) for i, j in enumerate(A.ARM_JOINTS)}
        want[A.GRIPPER] = self.gap_to_ticks(positions[A.ARM_DOF])
        ok = self._send_goals(want)
        if not ok:
            self._error = (BUS_ERROR, "a goal write failed")
        return ok

    def write_joint_velocities(self, velocities: list[float]) -> bool:
        return False

    def write_joint_efforts(self, efforts: list[float]) -> bool:
        return False

    def _latch_present(self) -> bool:
        """Every goal register set to the servo's own present position, the twin's to
        its own reading too (not the mirror: a tick or two of bracket play must not
        become a push at torque on)."""
        ok = True
        for j in self._joints():
            t = self._present[j]
            if self._bus.write2(self._ids[j], REG_GOAL, t):
                self._goal[j] = t
            else:
                ok = False
        if self._twin and self._present_twin is not None:
            if self._bus.write2(self._twin[1], REG_GOAL, self._present_twin):
                self._goal_twin = self._present_twin
            else:
                ok = False
        return ok

    def write_stop(self) -> bool:
        if not self._connected or not self._present:
            return False
        return self._latch_present()

    def write_enable(self, enable: bool) -> bool:
        """Torque on or off on the six servos. Before torque goes on, every
        servo's goal register is set to its present position: a servo
        enables onto whatever goal its register holds (the last run's,
        after a power cycle anything), and the arm would jump there."""
        if not self._connected:
            return False
        ok = True
        if enable:
            if self._read_all() is None:
                self._error = (BUS_ERROR, "the servos do not answer before torque on")
                return False
            gap = self._check_twin()
            if gap is not None and abs(gap) > TWIN_TOL_TICKS:
                self._error = (TWIN_ERROR, f"{self.twin_name()} reads {gap:+d} ticks off its mirror; torque stays off")
                return False
            if not self._latch_present():
                self._error = (BUS_ERROR, "a goal could not be latched before torque on; torque stays off")
                return False
        for j in self._joints():
            ok &= self._bus.write1(self._ids[j], REG_TORQUE, 1 if enable else 0)
        if self._twin:
            ok &= self._bus.write1(self._twin[1], REG_TORQUE, 1 if enable else 0)
        if ok:
            self._enabled = bool(enable)
            self._lag_since.clear()
        return ok

    def read_enabled(self) -> bool:
        return self._enabled

    def write_clear_errors(self) -> bool:
        self._error = (0, "")
        self._lag_since.clear()
        return True
