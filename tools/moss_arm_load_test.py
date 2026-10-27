#!/usr/bin/env python3
"""Load test: the arm out to a pose, held there, and back, every servo logged all along.

    .venv/bin/python tools/moss_arm_load_test.py --poses config/arm_load_cantilever.json --dry-run
    .venv/bin/python tools/moss_arm_load_test.py --poses config/arm_load_cantilever.json --hold 30 --label no_load
    .venv/bin/python tools/moss_arm_load_test.py --poses config/arm_load_cantilever.json --hold 30 --label 225g

The poses file is the preflight's shape: {"poses": {name: {"ticks": [...]}}, "sequence":
[{"phase", "from", "to"}]}; "drive" is the calibration's drive pose. The sequence is
played out (moss_dimos.arm_motion.goto: one frank goal per move, the servos' own
profile, stop and hold when a watched servo presses against something), the last pose
is held for --hold seconds, then the sequence is played back to the start. The arm
must start near the first pose; torque goes off only once it reads the drive pose.

Logged at 20 Hz during the moves and 5 Hz during the hold, one CSV line per sample
(~/.local/state/moss/arm_load/<label>_<time>.csv): time, phase, then for the
shoulder, its twin, the elbow and the wrist: position, signed load, current (mA),
voltage, temperature. A summary per phase is printed: peak and mean loads, max
current, min voltage, temperatures at the start and the end.

Stops (the arm goes back the way it came, torque stays on): a watched load at or
over --overload for 0.6 s (goto), any watched servo at or over --max-temp, or the
twin more than 40 ticks off its mirror.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos import arm_motion as M  # noqa: E402

STATE = Path(os.path.expanduser("~/.local/state/moss/arm_load"))
NEAR_RAD = 0.17
ROLL_CAMERA_UP_TICKS = (3000, 3500)


def ticks(q) -> str:
    return " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, q))


class Log:
    def __init__(self, path: Path, names: list[str]):
        self.f = path.open("w")
        self.names = names
        self.f.write("t,phase," + ",".join(f"{n}_pos,{n}_load,{n}_mA,{n}_volt,{n}_temp" for n in names) + "\n")
        self.t0 = time.monotonic()
        self.rows: list[tuple] = []

    def sample(self, bus, ids: dict[str, int], phase: str) -> dict[str, dict]:
        out = {}
        row = [f"{time.monotonic() - self.t0:.2f}", phase]
        for n in self.names:
            s = M.read_servo(bus, ids[n])
            load = None if s["load"] is None else s["load"] * (s["load_sign"] or 1)
            out[n] = {**s, "load_signed": load}
            row += [str(s["pos"]), str(load), "" if s["current_mA"] is None else f"{s['current_mA']:.0f}", str(s["volt"]), str(s["temp"])]
        self.f.write(",".join(row) + "\n")
        self.f.flush()
        self.rows.append((phase, out))
        return out

    def summary(self, phase: str) -> str:
        rows = [o for p, o in self.rows if p == phase]
        if not rows:
            return f"{phase}: no samples"
        parts = []
        for n in self.names:
            loads = [r[n]["load_signed"] for r in rows if r[n]["load_signed"] is not None]
            cur = [r[n]["current_mA"] for r in rows if r[n]["current_mA"] is not None]
            volts = [r[n]["volt"] for r in rows if r[n]["volt"] is not None]
            temps = [r[n]["temp"] for r in rows if r[n]["temp"] is not None]
            if not loads:
                continue
            peak = max(loads, key=abs)
            parts.append(f"{n}: load peak {peak:+d} mean {sum(loads) / len(loads):+.0f}, {max(cur) if cur else 0:.0f} mA max, "
                         f"{min(volts) if volts else 0:.1f} V min, {temps[0] if temps else '?'}->{temps[-1] if temps else '?'} C")
        return f"{phase} ({len(rows)} samples)\n    " + "\n    ".join(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poses", required=True)
    ap.add_argument("--hold", type=float, default=30.0)
    ap.add_argument("--label", default="load")
    ap.add_argument("--rate", type=float, default=150.0)
    ap.add_argument("--overload", type=int, default=M.OVERLOAD_DEFAULT)
    ap.add_argument("--max-temp", type=int, default=60)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cad-checked", action="store_true",
                    help="the sequence was posed in the CAD scene with zero contact: a coarse table refusal is a warning")
    ap.add_argument("--grip-ticks", type=int, default=None,
                    help="gripper goal kept for the whole test (a payload squeezed in the jaws: the goal past the contact, "
                         "not the jaws' reading, else the squeeze is lost when torque is latched)")
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.poses).read_text())
    drive_rad = A.drive_pose_rad()
    poses = {k: [A.ticks_to_rad(x) for x in v["ticks"]] for k, v in doc["poses"].items()}
    poses["drive"] = list(drive_rad)
    seq = doc["sequence"]
    print("sequence: " + " -> ".join([seq[0]["from"]] + [s["to"] for s in seq]) + f", held {a.hold:.0f} s at {seq[-1]['to']}, then back")
    for s in seq:
        print(f"  {s['phase']:12s} {ticks(poses[s['from']])}  ->  {ticks(poses[s['to']])}")
    for name, q in poses.items():
        roll = A.rad_to_ticks(q[4])
        if not ROLL_CAMERA_UP_TICKS[0] <= roll <= ROLL_CAMERA_UP_TICKS[1]:
            print(f"refused: pose {name} has wrist_roll {roll}, outside {ROLL_CAMERA_UP_TICKS} (camera under the gripper)", file=sys.stderr)
            return 3
    try:
        from moss_dimos.arm_guard import ArmGuard  # noqa: E402
        guard = ArmGuard.load()
        for s in seq:
            qa, qb = poses[s["from"]], poses[s["to"]]
            if not guard.segment_allowed(dict(zip(A.ARM_JOINTS, qa)), dict(zip(A.ARM_JOINTS, qb))):
                msg = f"the keep-out table (coarse) does not allow {s['phase']} ({s['from']} -> {s['to']})"
                if not a.cad_checked:
                    print(f"refused: {msg}; pose the sequence in the CAD scene (tools/moss_arm_drop.py plan --mujoco auto) "
                          f"and pass --cad-checked", file=sys.stderr)
                    return 3
                print(f"warning: {msg}; --cad-checked given, the CAD pass is trusted")
        print("keep-out table: checked")
    except ImportError:
        print("warning: no keep-out table here, the moves are not checked", file=sys.stderr)
    if a.dry_run:
        return 0
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402

    ad = FeetechSo101Adapter(address=os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT))
    if not ad.connect():
        print(f"not connected: {ad.read_error()[1]}", file=sys.stderr)
        return 2
    STATE.mkdir(parents=True, exist_ok=True)
    names = ["shoulder_lift"] + ([ad.twin_name()] if ad.twin() else []) + ["elbow_flex", "wrist_flex"]
    ids = {n: ad._ids[n] for n in names if n in ad._ids}  # noqa: SLF001
    if ad.twin():
        ids[ad.twin_name()] = ad.twin()[1]
    log = Log(STATE / f"{a.label}_{time.strftime('%Y%m%d_%H%M%S')}.csv", names)
    bus = ad._bus  # noqa: SLF001
    try:
        q = ad.read_joint_positions() or []
        q_now, gap = list(q[:A.ARM_DOF]), float(q[A.ARM_DOF])
        start = poses[seq[0]["from"]]
        if not all(abs(x - y) <= NEAR_RAD for x, y in zip(q_now[:4], start[:4])):
            print(f"refused: the arm ({ticks(q_now)}) is not near {seq[0]['from']} ({ticks(start)}); nothing moves", file=sys.stderr)
            return 3
        print("before: " + log.summary("before") if log.sample(bus, ids, "before") is None else "")
        M.hold_here(ad)
        if a.grip_ticks is not None:
            gid = ad._ids[A.GRIPPER]  # noqa: SLF001
            bus.write2(gid, 42, a.grip_ticks)
            ad._goal[A.GRIPPER] = a.grip_ticks  # noqa: SLF001
            gap = ad.ticks_to_gap(a.grip_ticks)
            time.sleep(0.5)
            print(f"gripper goal {a.grip_ticks} kept (reads {bus.read2(gid, 56)})")
        done = []        # the moves played, to play back
        stop = None
        for s in seq:
            rep = M.goto(ad, poses[s["to"]], gap, rate=a.rate, overload=a.overload, phase=s["phase"])
            log.sample(bus, ids, s["phase"])
            print("  " + rep.line())
            print("  " + log.summary(s["phase"]))
            if rep.aborted:
                stop = f"{s['phase']}: a servo pressed against something"
                break
            done.append(s)
            smp = log.sample(bus, ids, s["phase"])
            hot = [n for n, v in smp.items() if v["temp"] is not None and v["temp"] >= a.max_temp]
            if hot:
                stop = f"{s['phase']}: {', '.join(hot)} at {a.max_temp} C or more"
                break
            if ad.twin() and abs(ad.twin_gap()) > 40:
                stop = f"{s['phase']}: the twin is {ad.twin_gap():+d} ticks off its mirror"
                break
        if stop is None:
            print(f"holding {seq[-1]['to']} for {a.hold:.0f} s")
            t0 = time.monotonic()
            over_since = None
            while time.monotonic() - t0 < a.hold:
                smp = log.sample(bus, ids, "hold")
                ad.read_joint_positions()
                loads = {n: abs(v["load_signed"] or 0) for n, v in smp.items()}
                if max(loads.values()) >= a.overload:
                    over_since = over_since or time.monotonic()
                    if time.monotonic() - over_since > 0.6:
                        stop = f"hold: load {loads} for 0.6 s"
                        break
                else:
                    over_since = None
                hot = [n for n, v in smp.items() if v["temp"] is not None and v["temp"] >= a.max_temp]
                if hot:
                    stop = f"hold: {', '.join(hot)} at {a.max_temp} C or more"
                    break
                if ad.twin() and abs(ad.twin_gap()) > 40:
                    stop = f"hold: the twin is {ad.twin_gap():+d} ticks off its mirror"
                    break
                time.sleep(0.2)
            print("  " + log.summary("hold"))
        if stop:
            print(f"STOP: {stop}; going back", file=sys.stderr)
        for s in reversed(done):
            rep = M.goto(ad, poses[s["from"]], gap, rate=a.rate, overload=a.overload, phase=f"back_{s['phase']}")
            log.sample(bus, ids, f"back_{s['phase']}")
            print("  " + rep.line())
            if rep.aborted:
                print(f"  stopped on the way back at {s['phase']}; torque stays on", file=sys.stderr)
                break
        M.restore_defaults(ad)
        fin = ad.read_joint_positions() or []
        if len(fin) >= A.ARM_DOF and all(abs(x - y) <= NEAR_RAD for x, y in zip(fin[:4], drive_rad[:4])):
            ad.deactivate()
            print("back in the drive pose, torque off")
        else:
            ad._enabled = False  # noqa: SLF001
            print(f"NOT in the drive pose ({ticks(fin[:A.ARM_DOF])}), torque left on", file=sys.stderr)
        print(f"log: {log.f.name}")
        return 1 if stop else 0
    finally:
        ad._enabled = False  # noqa: SLF001
        ad.disconnect()


if __name__ == "__main__":
    sys.exit(main())
