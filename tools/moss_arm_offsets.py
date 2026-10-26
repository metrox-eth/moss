#!/usr/bin/env python3
"""Joint offsets of the arm from the wrist camera's views of a board on the floor.

    .venv/bin/python tools/moss_arm_offsets.py selftest          # synthetic round trip, no hardware
    .venv/bin/python tools/moss_arm_offsets.py fit               # from ~/.local/state/moss/wrist_handeye/records*.json
    .venv/bin/python tools/moss_arm_offsets.py fit --write       # ... and write config/arm_joint_offsets.json + extrinsics

The model: the servo reading of every joint is off by a constant (q_true = q_read + delta, five
values), the camera sits on the tool at X (six values), the board lies at one fixed pose on the
floor (six values). Every recorded view (servo readings + board pose in the camera) must give the
same board pose through FK(q + delta) * X * T_cam_board. Levenberg-Marquardt on all of it, 17
parameters, started from delta = 0 and the hand-eye X. The check: the spread of the board's
origin over the views, before and after, and the per-joint offsets in ticks.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from moss_dimos import arm as A  # noqa: E402
from moss_dimos.arm_kin import ArmKin  # noqa: E402
import moss_wrist_handeye as H  # noqa: E402

STATE = H.STATE
OFFSETS = ROOT / "config" / "arm_joint_offsets.json"
ROT_W = 0.1   # metres per radian in the residual: 1 deg counts like 1.7 mm


def pose_vec(Tm):
    return np.concatenate([H.rotvec(Tm[:3, :3]), Tm[:3, 3]])


def vec_pose(v):
    Rm, _ = cv2.Rodrigues(np.asarray(v[:3], float))
    return H.T(Rm, v[3:6])


def residuals(x, kin, views, n_boards):
    delta = x[:5]
    X = vec_pose(x[5:11])
    boards = [vec_pose(x[11 + 6 * k: 17 + 6 * k]) for k in range(n_boards)]
    res = []
    for q, Tct, b in views:
        p, R = kin.tool([qi + di for qi, di in zip(q, delta)])
        Tpred = H.T(R, p) @ X @ Tct
        D = H.inv(boards[b]) @ Tpred
        res.extend(D[:3, 3])
        res.extend(H.rotvec(D[:3, :3]) * ROT_W)
    return np.array(res)


def lm(x0, fun, iters=60):
    x = np.array(x0, float)
    r = fun(x)
    lam = 1e-3
    for _ in range(iters):
        J = np.zeros((len(r), len(x)))
        for k in range(len(x)):
            dx = np.zeros(len(x)); dx[k] = 1e-6
            J[:, k] = (fun(x + dx) - r) / 1e-6
        Hh = J.T @ J
        g = J.T @ r
        step = np.linalg.solve(Hh + lam * np.diag(np.diag(Hh) + 1e-12), -g)
        r_new = fun(x + step)
        if r_new @ r_new < r @ r:
            x, r, lam = x + step, r_new, max(lam / 3, 1e-9)
        else:
            lam *= 5
        if np.linalg.norm(step) < 1e-10:
            break
    return x, r


def spread(views, kin, delta, X, n_boards):
    out = []
    for b in range(n_boards):
        pts = []
        for q, Tct, bb in views:
            if bb != b:
                continue
            p, R = kin.tool([qi + di for qi, di in zip(q, delta)])
            pts.append((H.T(R, p) @ X @ Tct)[:3, 3])
        pts = np.array(pts)
        out.append(float(np.max(np.linalg.norm(pts - pts.mean(0), axis=1))) if len(pts) else 0.0)
    return out


def load_views(kin):
    """(q_read, T_cam_board, board_group) from every records*.json; one board group per file tag."""
    views, groups = [], []
    for f in sorted(STATE.glob("records*.json")):
        doc = json.loads(f.read_text())
        group = doc.get("board_group", 0)
        if group not in groups:
            groups.append(group)
        for r in doc["records"]:
            if r["rvec"] is None or r["corners"] < 8:
                continue
            Rct, _ = cv2.Rodrigues(np.array(r["rvec"]))
            views.append((list(r["rad_read"]), H.T(Rct, r["tvec"]), groups.index(group)))
    return views, len(groups)


def fit_views(views, n_boards, kin, X0):
    # initial board pose(s): the mean of the predictions with delta = 0
    x0 = [0.0] * 5 + list(pose_vec(X0))
    for b in range(n_boards):
        vs = [pose_vec(H.T(*reversed(kin.tool(q))) @ X0 @ Tct) for q, Tct, bb in views if bb == b]
        x0 += list(np.mean(vs, axis=0))
    x, r = lm(x0, lambda v: residuals(v, kin, views, n_boards))
    return x, r


def cmd_fit(a) -> int:
    kin = ArmKin.load()
    views, n_boards = load_views(kin)
    X0 = H.load_extrinsics() if hasattr(H, "load_extrinsics") else None
    if X0 is None:
        import moss_zone_view as Z  # noqa: E402
        X0 = Z.load_extrinsics()
    before = spread(views, kin, [0] * 5, X0, n_boards)
    print(f"{len(views)} views, {n_boards} board pose(s); spread before: {[round(s * 1000, 1) for s in before]} mm")
    x, r = fit_views(views, n_boards, kin, X0)
    delta, X = x[:5], vec_pose(x[5:11])
    after = spread(views, kin, delta, X, n_boards)
    print(f"spread after: {[round(s * 1000, 1) for s in after]} mm; rms residual {math.sqrt(float(r @ r) / len(r)) * 1000:.2f} mm-equivalent")
    print("joint offsets (q_true = q_read + delta): " + ", ".join(f"{j} {math.degrees(d):+.2f} deg ({d * A.TICKS_PER_RAD:+.0f} ticks)" for j, d in zip(A.ARM_JOINTS, delta)))
    print(f"camera in tool: t {np.round(X[:3, 3] * 100, 2)} cm, rot {np.round(np.degrees(H.rotvec(X[:3, :3])), 1)} deg (was t {np.round(X0[:3, 3] * 100, 2)})")
    for b in range(n_boards):
        Tb = vec_pose(x[11 + 6 * b: 17 + 6 * b])
        print(f"board {b}: origin chassis {np.round(Tb[:3, 3] * 100, 1)} cm")
    if a.write:
        OFFSETS.write_text(json.dumps({"format": "moss-arm-joint-offsets/1",
                                       "about": "constant offsets added to the servo readings before the kinematics (q_true = q_read + delta), fitted on wrist camera views of a board on the floor",
                                       "joints": list(A.ARM_JOINTS), "delta_rad": [float(d) for d in delta],
                                       "delta_ticks": [float(d * A.TICKS_PER_RAD) for d in delta],
                                       "views": len(views), "spread_before_m": before, "spread_after_m": after,
                                       "written": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
        rv = np.degrees(H.rotvec(X[:3, :3]))
        H.EXTRINSICS.write_text(
            f"camera_in_tool_xyz_m: [{', '.join(f'{v:.5f}' for v in X[:3, 3])}]\n"
            f"camera_in_tool_rotvec_deg: [{', '.join(f'{v:.3f}' for v in rv)}]\n"
            f"camera_in_tool_matrix: {np.round(X, 6).tolist()}\n"
            f"method: joint offsets + hand-eye, joint fit on {len(views)} views (tools/moss_arm_offsets.py)\n"
            f"board_origin_spread_m: {max(after):.4f}\ncheck: {'PASS' if max(after) <= 0.010 else 'FAIL'} (tolerance 0.010 m)\n"
            f"frame_orientation: upright (raw stream turned 180 deg)\n"
            f"tool_frame: moss_dimos/arm_kin tool() with config/arm_joint_offsets.json applied, chassis frame\n"
            f"written: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        print(f"-> {OFFSETS}\n-> {H.EXTRINSICS}")
    return 0


def cmd_selftest(a) -> int:
    rng = np.random.default_rng(11)
    kin = ArmKin.load()
    delta_true = np.radians([1.5, -2.0, 1.0, -0.8, 0.5])
    Rx, _ = cv2.Rodrigues(np.array([0.0, math.radians(-20.0), 0.0]))
    X_true = H.T(Rx, [0.055, 0.03, -0.003])
    Tb_true = H.T(np.eye(3), [0.30, 0.02, -0.02])
    bases = [[2865, 1583, 2404, 2889, 3214], [2131, 2642, 1676, 2938, 3229], [2866, 2642, 1663, 2944, 3230],
             [3140, 2861, 1551, 2833, 3230], [2492, 2864, 1553, 2829, 3232]]
    views = []
    for base in bases:
        for _ in range(5):
            q_true = [A.ticks_to_rad(t) + rng.normal(0, 0.05) for t in base]
            q_read = [qt - dt for qt, dt in zip(q_true, delta_true)]
            p, R = kin.tool(q_true)
            Tct = H.inv(H.T(R, p) @ X_true) @ Tb_true
            n_r, _ = cv2.Rodrigues(rng.normal(0, math.radians(0.1), 3))
            views.append((q_read, Tct @ H.T(n_r, rng.normal(0, 0.0005, 3)), 0))
    X0 = X_true @ H.T(np.eye(3), [0.004, -0.003, 0.002])   # a slightly wrong start, like a hand-eye done without offsets
    x, r = fit_views(views, 1, kin, X0)
    delta, X = x[:5], vec_pose(x[5:11])
    err_deg = np.degrees(np.abs(delta - delta_true))
    dX = np.linalg.norm(X[:3, 3] - X_true[:3, 3]) * 1000
    print(f"selftest: offsets recovered within {err_deg.max():.3f} deg (worst joint), camera within {dX:.2f} mm, spread {spread(views, kin, delta, X, 1)[0] * 1000:.2f} mm")
    ok = err_deg.max() < 0.3 and dX < 3.0
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("fit")
    pf.add_argument("--write", action="store_true")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    return {"fit": cmd_fit, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
