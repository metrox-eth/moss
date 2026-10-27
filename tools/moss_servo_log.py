#!/usr/bin/env python3
"""Log the present position, load, voltage and temperature of some servos until killed.

    .venv/bin/python tools/moss_servo_log.py --ids 11,15 --hz 5 --out /path/file.csv

Reads only, nothing moves: the arm can be moved by hand with the torque off while
this runs, and the file says what each servo saw (which way each one counts when the
joint goes one way, where the stops are). One CSV line per sample: time, then for each
id its position, load (signed), voltage and temperature.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos.arm_feetech import FeetechBus  # noqa: E402
from moss_dimos.arm_motion import read_servo  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True, help="comma separated servo ids")
    ap.add_argument("--hz", type=float, default=5.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ids = [int(x) for x in a.ids.split(",")]
    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    bus = FeetechBus(port)
    if not bus.open():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write("t," + ",".join(f"pos{i},load{i},volt{i},temp{i}" for i in ids) + "\n")
        t0 = time.monotonic()
        try:
            while True:
                row = [f"{time.monotonic() - t0:.2f}"]
                for sid in ids:
                    s = read_servo(bus, sid)
                    load = None if s["load"] is None else s["load"] * s["load_sign"]
                    row += [str(s["pos"]), str(load), str(s["volt"]), str(s["temp"])]
                f.write(",".join(row) + "\n")
                f.flush()
                time.sleep(1.0 / a.hz)
        except KeyboardInterrupt:
            pass
    bus.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
