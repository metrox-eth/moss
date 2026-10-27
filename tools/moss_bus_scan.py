#!/usr/bin/env python3
"""Who is on the arm's servo bus? Reads only, nothing moves.

    .venv/bin/python tools/moss_bus_scan.py              # IDs 1-253, 1 Mbps
    .venv/bin/python tools/moss_bus_scan.py --ids 1-20   # a narrower range

Pings every ID and, for each servo that answers, reads the registers that say what
it is and how it is set: model, firmware, mode (33), homing offset (31), angle limits
(9-12), position loop P/D/I (21-23), dead band (26-27), torque limit (48), present
position (56), voltage and temperature (62-63). Each ID that answers is pinged ten
more times: a servo that answers some pings and not others is two servos sharing the
ID (their replies collide on the half-duplex line), which is what a servo fresh from
the box (factory ID 1) does next to the arm's shoulder_pan.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos.arm_feetech import FeetechBus, SERVO_IDS  # noqa: E402

KNOWN = {v: k for k, v in SERVO_IDS.items()}
try:    # the robot's calibration file names a twin servo, when there is one
    import json
    for _n, _r in json.loads(A.calibration_path().read_text()).items():
        if isinstance(_r, dict) and "id" in _r and _n not in KNOWN.values():
            KNOWN.setdefault(int(_r["id"]), _n)
except Exception:  # noqa: BLE001
    pass


def sign11(v: int) -> int:
    """Sign-magnitude with the sign in bit 11 (the homing offset)."""
    return -(v & 0x7FF) if v & 0x800 else v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="1-253", help="range a-b")
    ap.add_argument("--pings", type=int, default=10)
    a = ap.parse_args(argv)
    lo, hi = (int(x) for x in a.ids.split("-"))
    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    bus = FeetechBus(port)
    if not bus.open():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    ph, pk = bus._ph, bus._pk  # noqa: SLF001
    found = []
    for sid in range(lo, hi + 1):
        try:
            _model, comm, _err = pk.ping(ph, sid)
        except Exception:  # noqa: BLE001
            comm = -1
        if comm == 0:
            found.append(sid)
    print(f"bus {port}: {len(found)} servo(s) answer: {found}")
    print("id  name            model  fw    mode  offset  min   max   P  D  I  dead    pos   limit  volt temp  pings")
    for sid in found:
        ok = 0
        for _ in range(a.pings):
            try:
                _m, comm, _e = pk.ping(ph, sid)
                ok += comm == 0
            except Exception:  # noqa: BLE001
                pass
        r2 = lambda addr: bus.read2(sid, addr)  # noqa: E731
        model = r2(3)
        fw = (bus.read2(sid, 0) or 0)
        mode = (r2(33) or 0) & 0xFF
        ofs = sign11(r2(31) or 0)
        amin, amax = r2(9), r2(11)
        pdi = r2(21) or 0
        p, d = pdi & 0xFF, pdi >> 8
        i = (r2(23) or 0) & 0xFF
        dz = r2(26) or 0
        dead = f"{dz & 0xFF}/{dz >> 8}"
        pos = r2(56)
        lim = r2(48)
        vt = r2(62) or 0
        volt, temp = (vt & 0xFF) / 10.0, vt >> 8
        name = KNOWN.get(sid, "NEW" if sid not in KNOWN else "")
        flag = "" if ok == a.pings else f"  <-- {ok}/{a.pings} answered: two servos on this ID?"
        print(f"{sid:3d} {name:14s} {model!s:6s} {fw!s:5s} {mode:4d}  {ofs:6d} {amin!s:5s} {amax!s:5s} {p:2d} {d:2d} {i:2d}  {dead:6s} {pos!s:5s} {lim!s:5s}  {volt:4.1f} {temp:3d}   {ok}/{a.pings}{flag}")
    missing = [v for k, v in SERVO_IDS.items() if v not in found]
    if missing:
        print(f"arm servos that did not answer: {missing}", file=sys.stderr)
    bus.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
