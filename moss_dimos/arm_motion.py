"""Frank, synchronised moves of the arm on the Feetech bus.

One goal per joint per move, written once; the servos' own motion profile does the
rest, with the acceleration at its maximum (the setting LeRobot gives its SO-101s).
Each joint gets the speed that makes every joint arrive at the same time, the largest
move running at `rate` ticks per second. While the move runs, the shoulder and elbow
loads are watched: a load above `overload` for longer than `overload_s` means the arm
is pressing against something, the goals are set to where the arm is and the move
reports `aborted`.

Why not stream the trajectory point by point at 50 Hz: a loaded joint then only ever
sees an error of one or two ticks, develops almost no torque, and falls hundreds of
ticks behind the others; the arm's shape during the move is wrong and the gripper or
the camera sweep the floor. Measured on the robot on the same day: the streamed goal
moved the loaded shoulder 0 ticks, the frank goal 140 ticks in 0.75 s.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from moss_dimos import arm as A

REG_ACC, REG_GOAL, REG_SPEED, REG_PRESENT, REG_LOAD, REG_VOLT_TEMP, REG_CURRENT = 41, 42, 46, 56, 60, 62, 69
ACC_MAX = 254
RATE_DEFAULT = 250.0          # ticks per second for the largest joint of a move
OVERLOAD_DEFAULT = 950        # servo load (of 1000) that means something is pressed against
OVERLOAD_S = 0.6
SETTLE_S = 0.8
WATCHED = ("shoulder_lift", "elbow_flex")


@dataclass
class MoveReport:
    phase: str
    planned_s: float
    final_rad: list[float]
    short_ticks: list[float]
    peak_load: dict[str, int] = field(default_factory=dict)
    min_volt: float = 0.0
    aborted: bool = False

    def line(self) -> str:
        short = " ".join(f"{j} {v:.0f}" for j, v in zip(A.ARM_JOINTS, self.short_ticks))
        loads = " ".join(f"{j} {v}" for j, v in self.peak_load.items())
        tail = "  ABORTED (pressed against something)" if self.aborted else ""
        return f"{self.phase:14s} {self.planned_s:4.1f} s  short by {short} ticks  peak load {loads}  min {self.min_volt:.1f} V{tail}"


def read_servo(bus, sid: int) -> dict:
    """Position, load, voltage, temperature, current of one servo, as the registers give them."""
    p = bus.read2(sid, REG_PRESENT)
    load = bus.read2(sid, REG_LOAD)
    vt = bus.read2(sid, REG_VOLT_TEMP)
    cur = bus.read2(sid, REG_CURRENT)
    return {"pos": p, "load": None if load is None else (load & 0x3FF), "load_sign": None if load is None else (-1 if load & 0x400 else 1),
            "volt": None if vt is None else (vt & 0xFF) / 10.0, "temp": None if vt is None else vt >> 8,
            "current_mA": None if cur is None else cur * 6.5}


def goto(ad, q_to: list[float], gap_m: float, rate: float = RATE_DEFAULT, overload: int = OVERLOAD_DEFAULT,
         phase: str = "move", least_s: float = 0.6) -> MoveReport:
    """Move the adapter's arm to q_to (model radians, ARM_JOINTS order) with the gripper at gap_m."""
    bus, ids = ad._bus, ad._ids  # noqa: SLF001
    now = ad.read_joint_positions() or []
    q_now = list(now[:A.ARM_DOF]) if len(now) >= A.ARM_DOF else list(q_to)
    d_ticks = [abs(b - a) * A.TICKS_PER_RAD for a, b in zip(q_now, q_to)]
    T = max(max(d_ticks) / rate, least_s)
    for i, j in enumerate(A.ARM_JOINTS):
        bus.write1(ids[j], REG_ACC, ACC_MAX)
        bus.write2(ids[j], REG_SPEED, max(20, int(d_ticks[i] / T)))
    ad.write_joint_positions(list(q_to) + [gap_m])
    t0 = time.monotonic()
    peak = {j: 0 for j in WATCHED}
    vmin = 99.0
    over_since = None
    aborted = False
    while time.monotonic() - t0 < T + SETTLE_S:
        time.sleep(0.05)
        hot = False
        for j in WATCHED:
            s = read_servo(bus, ids[j])
            if s["load"] is not None:
                peak[j] = max(peak[j], s["load"])
                hot = hot or s["load"] >= overload
            if s["volt"] is not None:
                vmin = min(vmin, s["volt"])
        if hot:
            over_since = over_since or time.monotonic()
            if time.monotonic() - over_since > OVERLOAD_S:
                cur = ad.read_joint_positions() or []
                if len(cur) > A.ARM_DOF:
                    ad.write_joint_positions(list(cur[:A.ARM_DOF]) + [float(cur[A.ARM_DOF])])
                aborted = True
                break
        else:
            over_since = None
    fin = ad.read_joint_positions() or []
    q_fin = list(fin[:A.ARM_DOF]) if len(fin) >= A.ARM_DOF else list(q_to)
    short = [abs(f - t) * A.TICKS_PER_RAD for f, t in zip(q_fin, q_to)]
    return MoveReport(phase, T, q_fin, short, peak, vmin, aborted)


def hold_here(ad) -> list[float]:
    """Goals set to the present positions, torque on: nothing jumps, nothing pushes."""
    bus, ids = ad._bus, ad._ids  # noqa: SLF001
    cur = ad.read_joint_positions() or []
    ad._enabled = True  # noqa: SLF001
    if len(cur) > A.ARM_DOF:
        ad.write_joint_positions(list(cur[:A.ARM_DOF]) + [float(cur[A.ARM_DOF])])
    ad.activate()
    return list(cur[:A.ARM_DOF])


def restore_defaults(ad, acc: int = 50, speed: int = 400) -> None:
    """Back to the adapter's own acceleration and speed registers (what activate() writes)."""
    bus, ids = ad._bus, ad._ids  # noqa: SLF001
    for j in A.ARM_JOINTS:
        bus.write1(ids[j], REG_ACC, acc)
        bus.write2(ids[j], REG_SPEED, speed)
