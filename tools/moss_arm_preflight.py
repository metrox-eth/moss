#!/usr/bin/env python3
"""Twenty seconds before any arm session: is every servo healthy, powered and free?

    .venv/bin/python tools/moss_arm_preflight.py            # the arm in its drive pose, torque off or on
    .venv/bin/python tools/moss_arm_preflight.py --no-move  # registers only, nothing moves

Reads each servo (voltage, temperature, load, torque limit, acceleration, speed), then
gives each joint one small frank move away from the drive pose and back (the moves are
in config/arm_preflight_poses.json, checked in the CAD scene), timing the move and
watching the load and the bus voltage. One line per servo with a verdict, and a YAML
record in ~/.local/state/moss/arm_preflight/. The arm ends in the drive pose, torque off.

Healthy on this arm (measured): a 150 tick move completes in well under a second at
acceleration 254, peak load under 400 of 1000 with no load, temperature under 45 C,
bus above 11.5 V. The arm must start near the drive pose.
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

POSES = ROOT / "config" / "arm_preflight_poses.json"
STATE = Path(os.path.expanduser("~/.local/state/moss/arm_preflight"))
LIMITS = {"temp_c": 45, "volt_min": 11.5, "load_max": 400, "move_s": 1.2, "short_ticks": 20}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-move", action="store_true")
    ap.add_argument("--rate", type=float, default=300.0)
    a = ap.parse_args(argv)
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402

    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    ad = FeetechSo101Adapter(address=port)
    if not ad.connect():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    STATE.mkdir(parents=True, exist_ok=True)
    record = {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "servos": {}, "moves": {}, "verdict": {}}
    try:
        bus = ad._bus  # noqa: SLF001
        print("servo               pos   volt  temp  load  torque_limit  acc  speed  P  D  I  deadband")
        for name, sid in ad.servo_table():
            st = M.read_servo(bus, sid)
            st["torque_limit"] = bus.read2(sid, 48)
            st["acc"] = (bus.read2(sid, 41) or 0) & 0xFF
            st["speed"] = bus.read2(sid, 46)
            # the position loop (registers 21-23) and the dead band (26-27): what a goal a few
            # ticks away does under load depends on these, not on the maker's figures
            pdi = bus.read2(sid, 21) or 0
            st["P"], st["D"] = pdi & 0xFF, pdi >> 8
            st["I"] = (bus.read2(sid, 23) or 0) & 0xFF
            dz = bus.read2(sid, 26) or 0
            st["deadband"] = [dz & 0xFF, dz >> 8]
            record["servos"][name] = st
            print(f"{name:18s} {st['pos']:5d}  {st['volt']:.1f}  {st['temp']:3d}   {st['load']:4d}  {st['torque_limit']:5d}       {st['acc']:3d}  {st['speed']:5d}  {st['P']:2d} {st['D']:2d} {st['I']:2d}  {st['deadband']}")
        if ad.twin():
            print(f"  {ad.twin_name()} (id {ad.twin()[1]}) reads {ad.twin_gap():+d} ticks off the mirror of {ad.twin()[0]} (sum {ad.twin()[2]})")
        q = ad.read_joint_positions() or []
        drive = A.drive_pose_rad()
        near_drive = len(q) >= A.ARM_DOF and all(abs(x - y) <= 0.17 for x, y in zip(q[:4], drive[:4]))
        if not a.no_move:
            if not near_drive:
                print("the arm is not in the drive pose: registers only, no move (fold it first)", file=sys.stderr)
            else:
                doc = json.loads(POSES.read_text())
                poses = {k: [float(x) for x in v["rad"]] for k, v in doc["poses"].items()}
                poses["drive"] = list(drive)      # the sequence's "drive" is the calibration's drive pose
                gap = float(q[A.ARM_DOF])
                M.hold_here(ad)
                for mv in doc["sequence"]:
                    rep = M.goto(ad, poses[mv["to"]], gap, rate=a.rate, phase=mv["phase"])
                    record["moves"][mv["phase"]] = {"planned_s": rep.planned_s, "short": rep.short_ticks, "peak_load": rep.peak_load,
                                                    "min_volt": rep.min_volt, "aborted": rep.aborted}
                    print("  " + rep.line())
                    if rep.aborted:
                        break
                M.restore_defaults(ad)
                fin = ad.read_joint_positions() or []
                if ad.twin():
                    print(f"  {ad.twin_name()} reads {ad.twin_gap():+d} ticks off its mirror after the moves")
                code, msg = ad.read_error()
                if code:
                    print(f"  adapter error {code}: {msg}", file=sys.stderr)
                    record["verdict"]["adapter"] = [msg]
                if len(fin) >= A.ARM_DOF and all(abs(x - y) <= 0.17 for x, y in zip(fin[:4], drive[:4])):
                    ad.deactivate()
                    print("back in the drive pose, torque off")
                else:
                    ad._enabled = False  # noqa: SLF001
                    print("NOT back in the drive pose, torque left on", file=sys.stderr)
        # verdicts
        worst = "OK"
        for name, st in record["servos"].items():
            flags = []
            if st["temp"] is not None and st["temp"] > LIMITS["temp_c"]:
                flags.append(f"hot {st['temp']} C")
            if st["volt"] is not None and st["volt"] < LIMITS["volt_min"]:
                flags.append(f"low bus {st['volt']} V")
            if st["torque_limit"] is not None and name != "gripper" and st["torque_limit"] < 1000:
                flags.append(f"torque limit {st['torque_limit']}")
            record["verdict"][name] = flags or ["OK"]
            if flags:
                worst = "CHECK"
        for phase, mv in record["moves"].items():
            if mv["aborted"] or max(mv["short"]) > LIMITS["short_ticks"] or max(mv["peak_load"].values() or [0]) > LIMITS["load_max"]:
                record["verdict"][phase] = ["slow or loaded: short %s, load %s" % ([round(v) for v in mv["short"]], mv["peak_load"])]
                worst = "CHECK"
        record["worst"] = worst
        out = STATE / f"preflight_{time.strftime('%Y%m%d_%H%M%S')}.json"
        out.write_text(json.dumps(record, indent=1))
        print(f"PREFLIGHT {worst}: " + "; ".join(f"{k} {' '.join(v)}" for k, v in record["verdict"].items() if v != ["OK"]) + f"  -> {out}")
        return 0 if worst == "OK" else 1
    finally:
        ad._enabled = False  # noqa: SLF001
        ad.disconnect()


if __name__ == "__main__":
    sys.exit(main())
