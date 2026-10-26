#!/usr/bin/env python3
"""The arm to its observation pose (wrist camera over the floor) and back, straight on the bus.

    .venv/bin/python tools/moss_arm_observe.py --dry-run     # the numbers, nothing sent, no bus
    .venv/bin/python tools/moss_arm_observe.py               # drive -> travel -> look_down, torque stays ON
    .venv/bin/python tools/moss_arm_observe.py --back        # look_down -> travel -> drive, torque off once in drive
    .venv/bin/python tools/moss_arm_observe.py --where       # read the joints, nothing moves

The poses and the order are config/arm_observe_poses.json. The move is refused
unless the arm starts near the pose the sequence expects (drive, or look_down for
--back). The torque is never cut with the arm out of the drive pose.
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

POSES = ROOT / "config" / "arm_observe_poses.json"
NEAR_RAD = 0.17                  # pan, lift, elbow, wrist: within ~110 ticks of the expected start pose
NEAR_ROLL_RAD = 0.35             # the roll is looser (it does not change the arm's silhouette)
SLOW = 250.0                     # ticks per second of the largest joint per move (the servos profile the motion themselves)
ROLL_CAMERA_UP_TICKS = (3000, 3500)   # wrist_roll band where the camera is on top of the gripper (set by eye on the robot)
OVERLOAD = 950                   # servo load (of 1000) that means the arm is pressing against something: stop and hold


def near(q: list[float], ref: list[float]) -> bool:
    return all(abs(a - b) <= NEAR_RAD for a, b in zip(q[:4], ref[:4])) and abs(q[4] - ref[4]) <= NEAR_ROLL_RAD


def ticks(q: list[float]) -> str:
    return " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, q))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--back", action="store_true", help="look_down -> travel -> drive")
    ap.add_argument("--speed", type=float, default=SLOW)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--where", action="store_true", help="read the joints and exit")
    ap.add_argument("--phase", default=None, help="play this one move of the file (the arm must be near its start pose)")
    ap.add_argument("--allow-roll", action="store_true", help="play a pose whose roll puts the camera under the gripper (never by default)")
    ap.add_argument("--free", action="store_true", help="torque off (someone holds the arm): the arm is moved by hand")
    ap.add_argument("--mark", default=None, metavar="NAME", help="read the servos and append the pose to --marks")
    ap.add_argument("--marks", default=str(ROOT / "config" / "arm_reach_marks.json"))
    ap.add_argument("--hold", action="store_true", help="torque on where the arm is, no jump")
    ap.add_argument("--nudge", default=None, metavar="JOINT:TICKS",
                    help="move one joint by a few ticks from where it is (e.g. shoulder_pan:+34), torque stays on")
    ap.add_argument("--allow-turn", action="store_true",
                    help="play the pan-only turn back to drive even when the coarse table refuses it (after a CAD check)")
    ap.add_argument("--poses", default=str(POSES))
    a = ap.parse_args()

    if a.nudge:
        cycle = None                     # the move is built from the measured pose below
    elif a.phase:
        cycle = A.load_cycle(a.poses, speed=a.speed, start=a.phase, stop_after=a.phase, pick_pose="pick")
    elif a.back:
        cycle = A.load_cycle(a.poses, speed=a.speed, start="leave_observe", stop_after="to_drive", pick_pose="pick")
    else:
        cycle = A.load_cycle(a.poses, speed=a.speed, stop_after="observe", pick_pose="pick")
    steps = list(cycle.steps) if cycle else []
    # the wrist camera sits on top of the gripper only for a roll near 3214-3254 ticks (drive 3221): any pose
    # of a sequence outside that band turns the camera under the gripper. Three times on the same day,
    # through intermediate poses taken from the delivered cycle. Refused here, pose by pose, before anything moves.
    for s in steps:
        roll = A.rad_to_ticks(s.q_to[4])
        if not (ROLL_CAMERA_UP_TICKS[0] <= roll <= ROLL_CAMERA_UP_TICKS[1]) and not a.allow_roll:
            print(f"refused: pose {s.end} has wrist_roll {roll}, outside {ROLL_CAMERA_UP_TICKS} (camera under the gripper); "
                  f"fix the pose or pass --allow-roll", file=sys.stderr)
            return 3
    if cycle:
        print(f"sequence: {' -> '.join([steps[0].start] + [s.end for s in steps])}, "
              f"{sum(s.duration_s for s in steps):.1f} s at {a.speed:g} ticks/s")
        for s in steps:
            print(f"  {s.phase:14s} {ticks(s.q_from)}  ->  {ticks(s.q_to)}  {s.duration_s:.1f} s")
    if a.dry_run and not a.nudge:
        return 0

    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402

    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    ad = FeetechSo101Adapter(address=port)
    if not ad.connect():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    ends_in_drive = False
    where_only = False
    try:
        q = ad.read_joint_positions()
        if not q or len(q) != len(A.JOINT_NAMES):
            print(f"no positions from the servos: {q}", file=sys.stderr)
            return 2
        q_now, gap_now = list(q[:A.ARM_DOF]), float(q[A.ARM_DOF])
        print(f"arm now: {ticks(q_now)}  gap {gap_now * 1000:.0f} mm")
        if a.where:
            where_only = True
            return 0
        if a.free:
            # the hand on the arm, then the torque off: the arm is moved by hand to the poses it should learn
            ad.deactivate()
            where_only = True
            print("torque OFF: move the arm by hand; --mark NAME reads a pose, --hold puts the torque back where it is")
            return 0
        if a.mark:
            marks = Path(a.marks)
            doc = json.loads(marks.read_text()) if marks.exists() else {"about": "poses set by hand on the robot, torque off, read from the servos", "marks": []}
            doc["marks"].append({"name": a.mark, "ticks": [A.rad_to_ticks(v) for v in q_now], "rad": q_now,
                                 "gap_mm": round(gap_now * 1000), "at": time.strftime("%H:%M:%S")})
            marks.write_text(json.dumps(doc, indent=1))
            print(f"marked {a.mark}: {ticks(q_now)}  gap {gap_now * 1000:.0f} mm  ({len(doc['marks'])} marks in {marks})")
            where_only = True
            return 0
        if a.hold:
            # the goal register first, where the arm is, then the torque: no jump to a stale goal.
            # The adapter only writes goals when it thinks it is enabled: tell it so for this write.
            ad._enabled = True  # noqa: SLF001
            if not ad.write_joint_positions(list(q_now) + [gap_now]):
                print("refused: could not write the goal where the arm is; torque stays off", file=sys.stderr)
                ad._enabled = False  # noqa: SLF001
                return 2
            ad.activate()
            print(f"torque ON, holding {ticks(q_now)}")
            ad._enabled = False  # noqa: SLF001  (keep it on through disconnect)
            where_only = True
            return 0
        if a.nudge:
            # one joint, a few ticks (relative, "shoulder_pan:+34") or an absolute target ("shoulder_pan:=2865").
            # The other joints go back to the file's look_down values when they are near them (the measured
            # pose sags under gravity: starting every nudge from the reading lowered the shoulder 27 ticks
            # over five nudges), else they stay where they are.
            joint, delta = a.nudge.split(":")
            j = list(A.ARM_JOINTS).index(joint)
            ref = A.load_cycle(a.poses, speed=a.speed, stop_after="observe", pick_pose="pick").steps[-1].q_to
            q_to = [r if abs(r - m) * A.TICKS_PER_RAD <= 60 else m for r, m in zip(ref, q_now)]
            if delta.startswith("="):
                q_to[j] = A.ticks_to_rad(float(delta[1:]))
            else:
                q_to[j] = q_now[j] + float(delta) / A.TICKS_PER_RAD
            if abs(q_to[j] - q_now[j]) * A.TICKS_PER_RAD > 120:
                print("refused: a nudge is at most 120 ticks", file=sys.stderr)
                return 3
            # the other joints keep their goal from the first point to the last: no twitch (seen on the robot) - only the nudged joint is interpolated
            start = list(q_to)
            start[j] = q_now[j]
            steps = [A.goto_step(start, gap_now, q_to, gap_now, speed=a.speed)]
            print(f"nudge {joint} {delta}: {ticks(q_now)} -> {ticks(q_to)}")
            if a.dry_run:
                where_only = True
                return 0
        elif not near(q_now, steps[0].q_from):
            drive = A.drive_pose_rad()
            folded = (not a.back and all(abs(x - y) <= NEAR_RAD for x, y in zip(q_now[1:4], drive[1:4])))
            if not folded:
                print(f"refused: the arm is not near {steps[0].start} ({ticks(steps[0].q_from)}); nothing moves",
                      file=sys.stderr)
                return 3
            # folded but turned (the pan is off): first a pan-only move back to drive, checked by the keep-out table
            goto = A.goto_step(q_now, gap_now, drive, steps[0].gap_from_m, speed=a.speed)
            try:
                from moss_dimos.arm_guard import ArmGuard  # noqa: E402
                guard = ArmGuard.load()
                if not guard.segment_allowed(dict(zip(A.ARM_JOINTS, q_now)), dict(zip(A.ARM_JOINTS, drive))):
                    msg = f"the keep-out table (coarse) does not allow the turn back to drive from {ticks(q_now)}"
                    if not a.allow_turn:
                        print(f"refused: {msg}; check it in the CAD scene (tools/moss_arm_drop.py plan --mujoco auto) "
                              f"and pass --allow-turn", file=sys.stderr)
                        return 3
                    print(f"warning: {msg}; --allow-turn given, the CAD pass is trusted")
            except ImportError:
                print("warning: no keep-out table here, the turn back to drive is not checked", file=sys.stderr)
            print(f"goto drive first: the pan is {abs(q_now[0] - drive[0]) * A.TICKS_PER_RAD:.0f} ticks off, "
                  f"{goto.duration_s:.1f} s")
            steps.insert(0, goto)          # goto already starts from the measured pose
        else:
            # start the first move from the measured pose, not the nominal one (bug of the
            # first run: this replacement ran AFTER the goto was inserted and turned the
            # goto into drive -> drive, so the pan jumped 1045 ticks at the servo's own speed)
            steps[0] = A.Step(phase=steps[0].phase, start=steps[0].start, end=steps[0].end,
                              q_from=q_now, q_to=steps[0].q_to, gap_from_m=gap_now, gap_to_m=steps[0].gap_to_m,
                              timed_s=steps[0].timed_s, duration_s=steps[0].duration_s)
        if not ad.activate():
            print("activate failed", file=sys.stderr)
            return 2
        # One frank goal per move, the servos' own profile doing the motion: acceleration at the maximum
        # (what LeRobot sets on its SO-101s), each joint's speed chosen so that all joints arrive together,
        # the largest joint moving at --speed ticks/s. Streaming the goal in 1-2 tick steps at 50 Hz gave
        # the loaded shoulder no torque at all and left it 950 ticks behind the others (26/10).
        fin = list(q_now)
        for s in steps:
            d_ticks = [abs(b - a) * A.TICKS_PER_RAD for a, b in zip(fin, s.q_to)]
            T = max(max(d_ticks) / a.speed, 0.6)
            for i, j in enumerate(A.ARM_JOINTS):
                sid = ad._ids[j]  # noqa: SLF001
                ad._bus.write1(sid, 41, 254)  # noqa: SLF001
                ad._bus.write2(sid, 46, max(20, int(d_ticks[i] / T)))  # noqa: SLF001
            ad.write_joint_positions(list(s.q_to) + [s.gap_to_m])
            t0 = time.monotonic()
            overload_since = None
            aborted = False
            while time.monotonic() - t0 < T + 0.8:
                time.sleep(0.05)
                loads = [((ad._bus.read2(ad._ids[j], 60) or 0) & 0x3FF) for j in ("shoulder_lift", "elbow_flex")]  # noqa: SLF001
                if max(loads) >= OVERLOAD:
                    overload_since = overload_since or time.monotonic()
                    if time.monotonic() - overload_since > 0.6:
                        cur = list(ad.read_joint_positions() or fin + [s.gap_to_m])
                        ad.write_joint_positions(cur[:A.ARM_DOF] + [cur[A.ARM_DOF] if len(cur) > A.ARM_DOF else s.gap_to_m])
                        print(f"ABORT {s.phase}: shoulder/elbow load {loads} for 0.6 s (something is pressed against), "
                              f"goal set to where the arm is: {ticks(cur[:A.ARM_DOF])}", file=sys.stderr)
                        aborted = True
                        break
                else:
                    overload_since = None
            cur = list(ad.read_joint_positions() or [])
            fin = cur[:A.ARM_DOF] if len(cur) >= A.ARM_DOF else list(s.q_to)
            lag = [abs(f - t) * A.TICKS_PER_RAD for f, t in zip(fin, s.q_to)]
            print(f"  {s.phase:14s} {T:4.1f} s -> {ticks(fin)}  short by " +
                  " ".join(f"{j} {v:.0f}" for j, v in zip(A.ARM_JOINTS, lag)) + " ticks")
            if aborted:
                return 4
        print("done: " + ticks(fin))
        ends_in_drive = a.back and near(fin[:A.ARM_DOF], A.drive_pose_rad())
        return 0
    finally:
        if where_only:
            pass
        elif ends_in_drive:
            try:
                ad.deactivate()
                print("torque off: the arm is in the drive pose")
            except Exception:  # noqa: BLE001
                pass
        else:
            # disconnect() would write torque off on an enabled adapter: forget the
            # enable so the bus closes with the servos still holding the pose.
            ad._enabled = False  # noqa: SLF001
            print("torque LEFT ON: the arm is not in the drive pose (run --back to fold it)")
        ad.disconnect()


if __name__ == "__main__":
    sys.exit(main())
