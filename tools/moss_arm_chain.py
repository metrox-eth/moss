#!/usr/bin/env python3
"""The arm's kinematic chain, taken from the CAD model once so the robot can do
forward and inverse kinematics without MuJoCo (moss_dimos/arm_kin.py).

    python3 tools/moss_arm_chain.py extract        # CAD -> config/arm_chain.json (needs mujoco + the CAD scene)
    python3 tools/moss_arm_chain.py check          # arm_kin's FK against MuJoCo's at random poses, and a lift round trip
    python3 tools/moss_arm_chain.py cold           # no mujoco: FK of the delivered poses against their tcp_m

`check` is the proof the chain is right: the tool point from the pure chain and
from mj_kinematics must agree to well under a millimetre at every pose, and a
pose lifted 2 cm by the solver must land 2 cm higher with the same orientation.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos.arm_kin import ArmKin, CHAIN_PATH, FORMAT, JOINTS, TCP_IN_TOOL_M, JAWS_BELOW_TCP_M  # noqa: E402

TOOL_BODY = "nc90_tool"
CHECK_POSES = 300
SEED = 7
FK_TOL = 1e-5      # metres / matrix entries: a hundredth of a millimetre


def extract(out: Path = CHAIN_PATH) -> dict:
    import mujoco

    cad = A.find_cad()
    if cad is None:
        raise SystemExit("no CAD scene (MOSS_ARM_CAD, or ~/moss-*/cad/*/MOSS_R31.xml)")
    m = mujoco.MjModel.from_xml_path(str(cad))
    tool = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, TOOL_BODY)
    if tool < 0:
        raise SystemExit(f"body {TOOL_BODY} missing in {cad.name}")
    chain, b = [], tool
    while b != 0:
        chain.append(b)
        b = int(m.body_parentid[b])
    links = []
    for b in reversed(chain):
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b)
        rec = {"body": name, "pos": [round(float(v), 6) for v in m.body_pos[b]],
               "quat": [round(float(v), 7) for v in m.body_quat[b]], "joint": None}
        n = int(m.body_jntnum[b])
        if n > 1:
            raise SystemExit(f"body {name} has {n} joints: the chain expects at most one hinge per body")
        if n == 1:
            j = int(m.body_jntadr[b])
            if int(m.jnt_type[j]) != int(mujoco.mjtJoint.mjJNT_HINGE):
                raise SystemExit(f"joint on {name} is not a hinge")
            if np.linalg.norm(m.jnt_pos[j]) > 1e-9:
                raise SystemExit(f"joint on {name} is not at the body's origin: {m.jnt_pos[j]}")
            rec["joint"] = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
            rec["axis"] = [round(float(v), 6) for v in m.jnt_axis[j]]
            rec["range"] = [round(float(v), 6) for v in m.jnt_range[j]] if m.jnt_limited[j] else None
        links.append(rec)
    doc = {"format": FORMAT, "model": cad.name,
           "frame": "the model's world frame: the chassis, x forward, y left, the floor at z = 0",
           "about": "one link per body from the arm's mount to the tool; pos / quat (w x y z) = the body's offset "
                    "from its parent as in the CAD model; a hinge at the body's origin about axis, model radians",
           "links": links, "tcp_in_tool_m": list(TCP_IN_TOOL_M), "jaws_below_tcp_m": JAWS_BELOW_TCP_M}
    out.write_text(json.dumps(doc, indent=1))
    kin = ArmKin(doc)
    print(f"{cad.name}: {len(links)} links, joints {kin.joints} -> {out}")
    return doc


def check(say=print) -> int:
    import mujoco

    cad = A.find_cad()
    if cad is None:
        raise SystemExit("no CAD scene")
    kin = ArmKin.load()
    m = mujoco.MjModel.from_xml_path(str(cad))
    d = mujoco.MjData(m)
    tool = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, TOOL_BODY)
    jid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in JOINTS]
    adr = [int(m.jnt_qposadr[j]) for j in jid]
    rng = np.random.default_rng(SEED)
    base = d.qpos.copy()
    worst = 0.0
    for _ in range(CHECK_POSES):
        q = [float(rng.uniform(*kin.ranges[j])) for j in JOINTS]
        d.qpos[:] = base
        for a, v in zip(adr, q):
            d.qpos[a] = v
        mujoco.mj_kinematics(m, d)
        R = d.xmat[tool].reshape(3, 3)
        p_mj = d.xpos[tool] + R @ np.asarray(TCP_IN_TOOL_M)
        p_k, R_k = kin.tcp(q)
        worst = max(worst, float(np.linalg.norm(p_mj - p_k)), float(np.abs(R - R_k).max()))
    ok = worst < FK_TOL      # the JSON rounds offsets to the micrometre: a micrometre of drift is the file, not the maths
    say(f"FK against MuJoCo at {CHECK_POSES} random poses: worst difference {worst:.2e} (tolerance {FK_TOL:.0e}) -> {'OK' if ok else 'FAIL'}")
    fails = 0 if ok else 1
    # the lift round trip on the delivered poses
    doc = json.loads(A.POSES_PATH.read_text())
    for name, rec in doc["poses"].items():
        q = [float(v) for v in rec["rad"]]
        p0, R0 = kin.tcp(q)
        for dz in (0.02, -0.02, 0.05):
            q2 = kin.lift(q, dz)
            if q2 is None:
                say(f"  {name}: lift {dz:+.2f} m -> no solution (range)")
                continue
            p2, R2 = kin.tcp(q2)
            dp = p2 - p0
            rot = math.degrees(np.linalg.norm(__import__('moss_dimos.arm_kin', fromlist=['rotvec']).rotvec(R2 @ R0.T)))
            good = abs(dp[2] - dz) < 1e-3 and abs(dp[0]) < 1e-3 and abs(dp[1]) < 1e-3 and rot < 0.5 \
                and abs(q2[0] - q[0]) < 1e-9 and abs(q2[4] - q[4]) < 1e-9
            fails += 0 if good else 1
            say(f"  {name}: lift {dz:+.2f} m -> moved ({dp[0] * 1000:+.1f}, {dp[1] * 1000:+.1f}, {dp[2] * 1000:+.1f}) mm, "
                f"orientation {rot:.2f} deg, ticks {[A.rad_to_ticks(v) for v in q2]} -> {'OK' if good else 'FAIL'}")
    say(f"{'all OK' if not fails else f'{fails} FAIL'}")
    return 0 if not fails else 1


def cold(say=print) -> int:
    kin = ArmKin.load()
    doc = json.loads(A.POSES_PATH.read_text())
    fails = 0
    for name, rec in doc["poses"].items():
        if not rec.get("tcp_m"):
            continue
        p, R = kin.tcp([float(v) for v in rec["rad"]])
        err = float(np.linalg.norm(p - np.asarray(rec["tcp_m"], dtype=float)))
        good = err < 1e-3
        fails += 0 if good else 1
        say(f"  {name}: FK {np.round(p, 4).tolist()} vs file {rec['tcp_m']}: {err * 1000:.2f} mm, tilt {kin.tilt_deg(R):.1f} deg -> {'OK' if good else 'FAIL'}")
    say("all OK" if not fails else f"{fails} FAIL")
    return 0 if not fails else 1


def main(argv=None) -> int:
    cmd = (argv or sys.argv[1:] or ["check"])[0]
    if cmd == "extract":
        extract()
        return 0
    if cmd == "check":
        return check()
    if cmd == "cold":
        return cold()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
