#!/usr/bin/env python3
"""Emergency player: the pick-and-drop cycle straight on the Feetech bus, no coordinator.

Same cycle, same trajectory, same adapter class as tools/moss_arm_play.py; what is
missing is dimOS's coordinator in between (the RPC, the lag cancel). The loop below
writes every trajectory point at its time and reads the joints back; the worst
following error is printed, nothing is cancelled.

    .venv/bin/python tools/moss_arm_direct.py --dry-run             # the numbers, nothing sent
    .venv/bin/python tools/moss_arm_direct.py --pick-pose pick_low  # the cycle
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
from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick-pose", default=None)
    ap.add_argument("--poses", default=None, help="the cycle file (default config/arm_drop_poses.json; e.g. config/arm_pick_at.json)")
    ap.add_argument("--speed", type=float, default=A.SPEED_TICKS_PER_S)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cycle = A.load_cycle(*( [a.poses] if a.poses else [] ), speed=a.speed, pick_pose=a.pick_pose or A.pick_pose_name())
    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    ad = FeetechSo101Adapter(address=port)
    if not ad.connect():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    try:
        q = ad.read_joint_positions()
        if not q or len(q) != len(A.JOINT_NAMES):
            print(f"no positions from the servos: {q}", file=sys.stderr)
            return 2
        q_now, gap_now = list(q[:A.ARM_DOF]), float(q[A.ARM_DOF])
        print("arm now: " + " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, q_now)) + f"  gap {gap_now * 1000:.0f} mm")
        steps = list(cycle.steps)
        off = max(abs(x - y) for x, y in zip(q_now, cycle.first_pose)) * A.TICKS_PER_RAD
        if off > A.START_TOLERANCE_RAD * A.TICKS_PER_RAD:
            goto = A.goto_step(q_now, gap_now, cycle.first_pose, cycle.first_gap_m, speed=a.speed)
            print(f"goto: {off:.0f} ticks from {steps[0].start}, {goto.duration_s:.1f} s first")
            steps.insert(0, goto)
        from moss_dimos import arm_motion as M  # noqa: E402
        if a.dry_run:
            print("dry run: " + " -> ".join([steps[0].start] + [s.end for s in steps]))
            return 0
        if not ad.activate():
            print("activate failed", file=sys.stderr)
            return 2
        for s in steps:
            rep = M.goto(ad, list(s.q_to), s.gap_to_m, rate=a.speed, phase=s.phase)
            print("  " + rep.line())
            if rep.aborted:
                print("ABORT: the arm is pressing against something; the cycle stops here, torque stays on", file=sys.stderr)
                ad._enabled = False  # noqa: SLF001
                return 4
        fin = ad.read_joint_positions() or []
        print("done: " + " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, fin)))
        return 0
    finally:
        fin = list(ad.read_joint_positions() or [])
        drive = A.drive_pose_rad()
        if len(fin) >= A.ARM_DOF and all(abs(x - y) <= 0.17 for x, y in zip(fin[:4], drive[:4])):
            try:
                ad.deactivate()
                print("torque off: the arm is in the drive pose")
            except Exception:  # noqa: BLE001
                pass
        else:
            ad._enabled = False  # noqa: SLF001  (disconnect would cut the torque with the arm out)
            print("torque LEFT ON: the arm is not in the drive pose")
        ad.disconnect()


if __name__ == "__main__":
    sys.exit(main())
