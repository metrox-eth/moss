#!/usr/bin/env python3
"""Set up a second servo on a joint's axis (the shoulder's twin), the way the RoArm-M3
firmware runs its two shoulder servos: the driven one re-zeroed on the driving one, the
same goal mirrored about the middle, the same speed, acceleration and torque limit.

    .venv/bin/python tools/moss_arm_twin_setup.py rename 11 2        # one servo's bus id (EEPROM)
    .venv/bin/python tools/moss_arm_twin_setup.py zero --joint-id 2 --twin-id 7 \\
        --joint shoulder_lift --stop-ticks 860 --sum 4094              # the arm at the joint's rear stop, torque off
    .venv/bin/python tools/moss_arm_twin_setup.py rest --seconds 30  # torque on, nothing moves, both loads read

rename: the old id must answer and the new one must not; written to the EEPROM (lock
register 55 opened and closed around it), then pinged under its new id.

zero: with the arm at the joint's rear stop (the drive pose) and the torque off, the
joint's homing offset (register 31, sign in bit 11; reported = raw - offset) is set so
the stop reads `--stop-ticks` (the calibration's range_min), the twin's so the stop
reads `sum - stop_ticks`: from then on twin + joint = sum at every pose. The angle
limits (9-12) follow the calibration's range for the joint and its mirror for the twin;
P/D/I (21-23), dead band (26-27) and torque limit (48) are copied from the joint to
the twin. Each write is read back. config/arm_calibration.json gets the joint's new
offset and a `<joint>_twin` record, which is what the adapter reads to drive the twin.

rest: the adapter connects (it refuses if the two are not in mirror within 25 ticks),
torque goes on with every goal latched to its own reading, nothing moves, and both
loads, currents and temperatures are read at 5 Hz for --seconds. Each servo signs its
load in its own direction of count, and the twin counts the other way: the same
physical torque reads with OPPOSITE signs on the two (that is the share), the SAME
sign on both is the two pushing against each other through the bracket (the fight).
Measured on the first preflight with the pair: shoulder -35 and twin +31 at rest
after a lift, peaks 111 and 107 during it. Torque goes off at the end only if the arm
is folded.
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
from moss_dimos.arm_feetech import FeetechBus  # noqa: E402
from moss_dimos.arm_motion import read_servo  # noqa: E402

REG_ID, REG_MIN, REG_MAX, REG_P, REG_I, REG_DEAD, REG_OFS, REG_LOCK, REG_TORQUE_LIMIT = 5, 9, 11, 21, 23, 26, 31, 55, 48
REG_PRESENT = 56
REV = A.TICKS_PER_REV


def enc11(v: int) -> int:
    """Sign-magnitude, sign in bit 11, for the homing offset."""
    v = int(v)
    if not -2047 <= v <= 2047:
        raise ValueError(f"offset {v} is outside -2047..2047")
    return (abs(v) | 0x800) if v < 0 else v


def dec11(v: int) -> int:
    return -(v & 0x7FF) if v & 0x800 else v


def open_bus() -> FeetechBus:
    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    bus = FeetechBus(port)
    if not bus.open():
        sys.exit(f"the bus did not open on {port}")
    return bus


def answers(bus: FeetechBus, sid: int) -> bool:
    try:
        _m, comm, _e = bus._pk.ping(bus._ph, sid)  # noqa: SLF001
        return comm == 0
    except Exception:  # noqa: BLE001
        return False


def eeprom(bus: FeetechBus, sid: int, writes: list[tuple[int, int, int]]) -> None:
    """(addr, width, value)... written with the EEPROM unlocked, each read back."""
    if not bus.write1(sid, REG_LOCK, 0):
        sys.exit(f"servo {sid}: the EEPROM did not unlock")
    try:
        for addr, width, value in writes:
            ok = bus.write1(sid, addr, value) if width == 1 else bus.write2(sid, addr, value)
            back = bus.read2(sid, addr)
            if width == 1 and back is not None:
                back &= 0xFF
            if not ok or back != value:
                sys.exit(f"servo {sid}: register {addr} wanted {value}, reads {back}")
    finally:
        bus.write1(sid, REG_LOCK, 1)


def cmd_rename(a) -> int:
    bus = open_bus()
    old, new = int(a.old), int(a.new)
    if not answers(bus, old):
        sys.exit(f"id {old} does not answer")
    if answers(bus, new):
        sys.exit(f"id {new} already answers: two servos would share it")
    if not bus.write1(old, REG_LOCK, 0):
        sys.exit(f"servo {old}: the EEPROM did not unlock")
    bus.write1(old, REG_ID, new)
    bus.write1(new, REG_LOCK, 1)
    time.sleep(0.1)
    if answers(bus, new) and not answers(bus, old):
        print(f"servo {old} is now id {new}; it reads {bus.read2(new, REG_PRESENT)}")
        return 0
    sys.exit(f"after the write: {new} answers {answers(bus, new)}, {old} answers {answers(bus, old)}")


def set_offset_for(bus: FeetechBus, sid: int, want: int) -> int:
    """The homing offset that makes this servo read `want` where it is now; written, read back."""
    cur = bus.read2(sid, REG_PRESENT)
    ofs = dec11(bus.read2(sid, REG_OFS) or 0)
    raw = (cur + ofs) % REV
    new = (raw - want + REV // 2) % REV - REV // 2          # reported = raw - offset
    new = max(-2047, min(2047, new))
    eeprom(bus, sid, [(REG_OFS, 2, enc11(new))])
    time.sleep(0.05)
    back = bus.read2(sid, REG_PRESENT)
    if back is None or abs((back - want + REV // 2) % REV - REV // 2) > 2:
        sys.exit(f"servo {sid}: offset {new} written, wanted to read {want}, reads {back}")
    print(f"servo {sid}: offset {ofs} -> {new}, reads {back} (wanted {want})")
    return new


def cmd_zero(a) -> int:
    cal_path = A.calibration_path()
    doc = json.loads(cal_path.read_text()) if cal_path.is_file() else {}
    rec = doc.get(a.joint) or {}
    stop = int(a.stop_ticks if a.stop_ticks is not None else rec.get("range_min", 0))
    rmin = int(a.range_min if a.range_min is not None else rec.get("range_min", stop))
    rmax = int(a.range_max if a.range_max is not None else rec.get("range_max", REV - 1))
    bus = open_bus()
    for sid in (a.joint_id, a.twin_id):
        if not answers(bus, sid):
            sys.exit(f"id {sid} does not answer")
        if (bus.read2(sid, 40) or 0) & 0xFF:
            sys.exit(f"servo {sid} has torque on: the arm must rest at the stop with the torque off")
    pj0, pt0 = bus.read2(a.joint_id, REG_PRESENT), bus.read2(a.twin_id, REG_PRESENT)
    print(f"{a.joint} id {a.joint_id} reads {pj0}, twin id {a.twin_id} reads {pt0}")
    if a.expect and (abs(pj0 - a.expect[0]) > 5 or abs(pt0 - a.expect[1]) > 5):
        sys.exit(f"the arm has moved since the sweep: expected {a.expect[0]} / {a.expect[1]}; nothing written")
    j_ofs = set_offset_for(bus, a.joint_id, stop)
    t_ofs = set_offset_for(bus, a.twin_id, (a.sum - stop) % REV)
    # angle limits: the joint's range, the twin's its mirror
    eeprom(bus, a.joint_id, [(REG_MIN, 2, rmin), (REG_MAX, 2, rmax)])
    eeprom(bus, a.twin_id, [(REG_MIN, 2, (a.sum - rmax) % REV), (REG_MAX, 2, (a.sum - rmin) % REV)])
    # the position loop and the dead band: the twin takes the joint's
    p = bus.read2(a.joint_id, REG_P)
    i = bus.read2(a.joint_id, REG_I)
    dead = bus.read2(a.joint_id, REG_DEAD)
    lim = bus.read2(a.joint_id, REG_TORQUE_LIMIT)
    eeprom(bus, a.twin_id, [(REG_P, 2, p), (REG_I, 2, i), (REG_DEAD, 2, dead)])
    if not bus.write2(a.twin_id, REG_TORQUE_LIMIT, lim) or bus.read2(a.twin_id, REG_TORQUE_LIMIT) != lim:
        sys.exit(f"twin {a.twin_id}: torque limit {lim} did not take")
    pj, pt = bus.read2(a.joint_id, REG_PRESENT), bus.read2(a.twin_id, REG_PRESENT)
    print(f"P/D {p & 0xFF}/{p >> 8}, I {i & 0xFF}, dead band {dead & 0xFF}/{dead >> 8}, torque limit {lim} on both")
    print(f"now: {a.joint} {pj}, twin {pt}, sum {pj + pt} (wanted {a.sum})")
    bus.close()
    rec.update({"id": a.joint_id, "homing_offset": j_ofs, "range_min": rmin, "range_max": rmax, "travel_ticks": rmax - rmin})
    doc[a.joint] = rec
    doc[f"{a.joint}_twin"] = {"id": a.twin_id, "of": a.joint, "sum_ticks": a.sum, "homing_offset": t_ofs,
                              "range_min": (a.sum - rmax) % REV, "range_max": (a.sum - rmin) % REV,
                              "note": "second servo back to back on the same axis; it counts the other way: twin + joint = sum_ticks at every pose"}
    cal_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(f"written to {cal_path}")
    return 0


def cmd_rest(a) -> int:
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402
    from moss_dimos import arm_motion as M  # noqa: E402

    ad = FeetechSo101Adapter()
    if not ad.connect():
        sys.exit(f"not connected: {ad.read_error()[1]}")
    tw = ad.twin()
    if not tw:
        sys.exit("no twin in the calibration file")
    joint, tid, _ = tw
    bus, jid = ad._bus, ad._ids[joint]  # noqa: SLF001
    print(f"{joint} id {jid} and twin id {tid}: gap {ad.twin_gap():+d} ticks; torque on, nothing moves")
    M.hold_here(ad)
    t0 = time.monotonic()
    rows = []
    heavy = 0
    try:
        while time.monotonic() - t0 < a.seconds:
            sj, st = read_servo(bus, jid), read_servo(bus, tid)
            lj = (sj["load"] or 0) * (sj["load_sign"] or 1)
            lt = (st["load"] or 0) * (st["load_sign"] or 1)
            rows.append((lj, lt))
            print(f"{time.monotonic() - t0:5.1f} s  {joint} load {lj:+5d} {sj['current_mA']:5.0f} mA {sj['temp']} C   twin load {lt:+5d} {st['current_mA']:5.0f} mA {st['temp']} C   pos {sj['pos']} {st['pos']}")
            # the same sign on both = pushing against each other (each counts its own way)
            heavy = heavy + 1 if (min(abs(lj), abs(lt)) > a.fight_load and lj * lt > 0) else 0
            if heavy >= 5:
                print(f"both loads above {a.fight_load} with the same sign for a second, nothing to lift: the two are fighting, stopping")
                break
            time.sleep(0.2)
    finally:
        # torque off only where the arm rests on its own: shoulder and elbow folded as in the drive pose
        q = ad.read_joint_positions() or []
        drive = A.drive_pose_rad()
        if len(q) >= A.ARM_DOF and all(abs(q[i] - drive[i]) <= 0.17 for i in (1, 2)):
            ad.deactivate()
            print("arm folded: torque off")
        else:
            ad._enabled = False  # noqa: SLF001
            print("arm NOT folded: torque left on")
        ad.disconnect()
    if rows:
        mj = sum(r[0] for r in rows) / len(rows)
        mt = sum(r[1] for r in rows) / len(rows)
        print(f"mean load {joint} {mj:+.0f}, twin {mt:+.0f}; max |load| {max(abs(r[0]) for r in rows)} / {max(abs(r[1]) for r in rows)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rename")
    r.add_argument("old", type=int)
    r.add_argument("new", type=int)
    z = sub.add_parser("zero")
    z.add_argument("--joint", default="shoulder_lift")
    z.add_argument("--joint-id", type=int, default=2)
    z.add_argument("--twin-id", type=int, default=7)
    z.add_argument("--stop-ticks", type=int, default=None, help="what the joint reads at the stop (default: the calibration's range_min)")
    z.add_argument("--range-min", type=int, default=None, help="position limits for the joint (default: the calibration's)")
    z.add_argument("--range-max", type=int, default=None)
    z.add_argument("--expect", type=int, nargs=2, metavar=("JOINT", "TWIN"), default=None,
                   help="what the two must read now (from the sweep's log); off by more than 5 ticks = nothing written")
    z.add_argument("--sum", type=int, default=4094, help="twin + joint at every pose (2047 + p and 2047 - p)")
    t = sub.add_parser("rest")
    t.add_argument("--seconds", type=float, default=30.0)
    t.add_argument("--fight-load", type=int, default=300, help="load (of 1000) on either servo, held a second at rest, that stops the test")
    a = ap.parse_args(argv)
    return {"rename": cmd_rename, "zero": cmd_zero, "rest": cmd_rest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
