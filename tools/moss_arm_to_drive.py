#!/usr/bin/env python3
"""The arm back to the drive pose from wherever it is near it, one frank move, torque off there.

    .venv/bin/python tools/moss_arm_to_drive.py            # move, then torque off in the drive pose
    .venv/bin/python tools/moss_arm_to_drive.py --dry-run  # the numbers and the keep-out check, nothing sent

For an arm left a little out of the drive pose (moved by hand, a tool stopped early):
every joint within --max-ticks of the drive pose (default 400, 35 degrees), the straight
joint-space move checked by the keep-out table, then one move at --rate ticks per second
with the loads watched (moss_dimos.arm_motion.goto: a joint pressing against something
stops and holds). Torque goes off only once the arm reads the drive pose.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos import arm_motion as M  # noqa: E402

NEAR_RAD = 0.17


def ticks(q) -> str:
    return " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, q))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rate", type=float, default=150.0)
    ap.add_argument("--max-ticks", type=float, default=400.0)
    a = ap.parse_args(argv)
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402

    ad = FeetechSo101Adapter(address=os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT))
    if not ad.connect():
        print(f"not connected: {ad.read_error()[1]}", file=sys.stderr)
        return 2
    try:
        q = ad.read_joint_positions() or []
        if len(q) <= A.ARM_DOF:
            print("the servos do not answer", file=sys.stderr)
            return 2
        q_now, gap = list(q[:A.ARM_DOF]), float(q[A.ARM_DOF])
        drive = A.drive_pose_rad()
        off = [(b - a_) * A.TICKS_PER_RAD for a_, b in zip(q_now, drive)]
        print(f"now   {ticks(q_now)}")
        print(f"drive {ticks(drive)}")
        print("move  " + " ".join(f"{j} {d:+.0f}" for j, d in zip(A.ARM_JOINTS, off)) + " ticks")
        far = [j for j, d in zip(A.ARM_JOINTS, off) if abs(d) > a.max_ticks]
        if far:
            print(f"refused: {', '.join(far)} more than {a.max_ticks:.0f} ticks from the drive pose; nothing moves", file=sys.stderr)
            return 3
        try:
            from moss_dimos.arm_guard import ArmGuard  # noqa: E402
            guard = ArmGuard.load()
            if not guard.segment_allowed(dict(zip(A.ARM_JOINTS, q_now)), dict(zip(A.ARM_JOINTS, drive))):
                print("refused: the keep-out table does not allow the straight move to drive from here; nothing moves", file=sys.stderr)
                return 3
            print("keep-out table: the move is allowed")
        except ImportError:
            print("warning: no keep-out table here, the move is not checked", file=sys.stderr)
        if a.dry_run:
            return 0
        M.hold_here(ad)
        rep = M.goto(ad, drive, gap, rate=a.rate, phase="to_drive")
        print("  " + rep.line())
        M.restore_defaults(ad)
        fin = ad.read_joint_positions() or []
        if not rep.aborted and len(fin) >= A.ARM_DOF and all(abs(x - y) <= NEAR_RAD for x, y in zip(fin[:4], drive[:4])):
            ad.deactivate()
            print(f"in the drive pose ({ticks(fin[:A.ARM_DOF])}), torque off")
            return 0
        ad._enabled = False  # noqa: SLF001
        print(f"NOT in the drive pose ({ticks(fin[:A.ARM_DOF])}), torque left on", file=sys.stderr)
        return 1
    finally:
        ad._enabled = False  # noqa: SLF001
        ad.disconnect()


if __name__ == "__main__":
    sys.exit(main())
