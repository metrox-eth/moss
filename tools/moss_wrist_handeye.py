#!/usr/bin/env python3
"""The wrist camera's pose on the gripper (eye-in-hand), from a ChArUco board taped on the floor.

    .venv/bin/python tools/moss_wrist_handeye.py poses      # config/arm_handeye_poses.json: ten poses around look_floor
    .venv/bin/python tools/moss_wrist_handeye.py run        # plays them one by one, records joints + board pose, torque stays on
    .venv/bin/python tools/moss_wrist_handeye.py solve      # camera-in-tool transform, then the board-on-the-floor check
    .venv/bin/python tools/moss_wrist_handeye.py selftest   # synthetic round trip, no hardware

run: the arm must start near look_floor (the recognition pose). At each pose it settles,
reads the servos, takes one frame (turned upright), finds the board and its pose
(solvePnP with config/wrist_camera_intrinsics.yaml). Records go to
~/.local/state/moss/wrist_handeye/records.json with the frames next to them.

solve: cv2.calibrateHandEye on (tool pose in the chassis frame from the servos and
moss_dimos/arm_kin, board pose in the camera). The check that matters: the board's origin
computed from every view must land on the same floor point. The spread is printed and
written with the result to config/wrist_camera_extrinsics.yaml.
"""
from __future__ import annotations

import argparse
import json
import math
import os
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
import moss_wrist_calib as W  # noqa: E402

OBSERVE_POSES = ROOT / "config" / "arm_observe_poses.json"
HANDEYE_POSES = ROOT / "config" / "arm_handeye_poses.json"
INTRINSICS = ROOT / "config" / "wrist_camera_intrinsics.yaml"
EXTRINSICS = ROOT / "config" / "wrist_camera_extrinsics.yaml"
STATE = Path(os.path.expanduser("~/.local/state/moss/wrist_handeye"))
SPEED = 80.0
SETTLE_S = 1.5
# variations around look_floor, in ticks per joint (pan, lift, elbow, wrist_flex, roll)
VARIATIONS = [
    ("centre", [0, 0, 0, 0, 0]),
    ("pan_plus", [80, 0, 0, 0, 0]),
    ("pan_minus", [-80, 0, 0, 0, 0]),
    ("wrist_plus", [0, 0, 0, 90, 0]),
    ("wrist_minus", [0, 0, 0, -90, 0]),
    ("roll_plus", [0, 0, 0, 0, 120]),
    ("roll_minus", [0, 0, 0, 0, -120]),
    ("higher", [0, -60, 60, 0, 0]),
    ("lower", [0, 60, -60, 0, 0]),
    ("mixed", [60, 0, 0, -60, 60]),
    ("back_centre", [0, 0, 0, 0, 0]),
]
# the second series: rotations about twice as large, the board still in the camera's field at 30 cm
VARIATIONS_BIG = [
    ("centre", [0, 0, 0, 0, 0]),
    ("pan_plus", [150, 0, 0, 0, 0]),
    ("pan_minus", [-150, 0, 0, 0, 0]),
    ("wrist_plus", [0, 0, 0, 200, 0]),
    ("wrist_minus", [0, 0, 0, -200, 0]),
    ("roll_plus", [0, 0, 0, 0, 250]),
    ("roll_minus", [0, 0, 0, 0, -250]),
    ("higher", [0, -110, 110, 0, 0]),
    ("lower", [0, 110, -110, 0, 0]),
    ("mixed_a", [120, 0, 0, -150, 180]),
    ("mixed_b", [-120, -60, 60, 150, -180]),
    ("back_centre", [0, 0, 0, 0, 0]),
]


def T(R, t):
    M = np.eye(4)
    M[:3, :3] = np.asarray(R, float).reshape(3, 3)
    M[:3, 3] = np.asarray(t, float).reshape(3)
    return M


def inv(M):
    R, t = M[:3, :3], M[:3, 3]
    return T(R.T, -R.T @ t)


def rotvec(R):
    r, _ = cv2.Rodrigues(np.asarray(R, float))
    return r.reshape(3)


def load_intrinsics(path=INTRINSICS):
    vals = {}
    for line in Path(path).read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            vals[k.strip()] = v.strip()
    K = np.array([[float(vals["fx"]), 0, float(vals["cx"])], [0, float(vals["fy"]), float(vals["cy"])], [0, 0, 1]])
    dist = np.array([float(x) for x in vals["distortion"].strip("[]").split(",")])
    return K, dist


def ticks_str(ticks):
    return " ".join(f"{j} {int(t)}" for j, t in zip(A.ARM_JOINTS, ticks))


# ------------------------------------------------------------------ poses
def cmd_poses(a) -> int:
    doc = json.loads(OBSERVE_POSES.read_text())
    base = doc["poses"]["look_floor"]["ticks"]
    variations = VARIATIONS_BIG if a.big else VARIATIONS
    target = HANDEYE_POSES.with_name("arm_handeye_poses_big.json") if a.big else HANDEYE_POSES
    out = {k: doc[k] for k in ("format", "joints", "units", "ticks_rule", "interpolation", "gripper")}
    out["rest"] = ["drive"]
    out["about"] = ("Hand-eye poses (tools/moss_wrist_handeye.py): small variations around look_floor so the wrist camera "
                    "keeps the board taped on the floor in view; played in this order, one move at a time.")
    poses, seq, prev = {}, [], None
    for name, dv in variations:
        t = [b + d for b, d in zip(base, dv)]
        poses[name] = {"ticks": t, "rad": [A.ticks_to_rad(x) for x in t]}
        if prev:
            seq.append({"phase": f"to_{name}", "from": prev, "to": name, "duration_s": 4.0, "gap_mm": [90, 90]})
        prev = name
    out["poses"] = poses
    out["sequence"] = seq
    target.write_text(json.dumps(out, indent=1))
    print(f"{len(poses)} poses, {len(seq)} moves -> {target}")
    for name, p in poses.items():
        print(f"  {name:12s} {ticks_str(p['ticks'])}")
    return 0


# ------------------------------------------------------------------ run
def board_pose(frame_upright, b, K, dist):
    """(rvec, tvec, n) of the board in the camera, or (None, None, n)."""
    gray = cv2.cvtColor(frame_upright, cv2.COLOR_BGR2GRAY)
    cc, ci = W.detect(b, gray)
    n = 0 if cc is None else len(cc)
    if n < 8:
        return None, None, n, None, None
    obj, img = b.matchImagePoints(cc, ci)
    ok, rvec, tvec = cv2.solvePnP(obj, img, K, dist, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None, None, n, cc, ci
    rvec, tvec = cv2.solvePnPRefineLM(obj, img, K, dist, rvec, tvec)
    return rvec.reshape(3), tvec.reshape(3), n, cc, ci


def cmd_run(a) -> int:
    doc = json.loads(Path(a.poses).read_text())
    names = [m["to"] for m in doc["sequence"]]
    first = doc["sequence"][0]["from"]
    poses = {k: [float(x) for x in v["rad"]] for k, v in doc["poses"].items()}
    K, dist = load_intrinsics()
    b = W.board(a.square, a.marker)
    STATE.mkdir(parents=True, exist_ok=True)
    print(f"{len(names)} moves from {first}, {a.speed:g} ticks/s, settle {SETTLE_S} s")
    if a.dry_run:
        return 0
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402

    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    ad = FeetechSo101Adapter(address=port)
    if not ad.connect():
        print(f"the bus did not open on {port}", file=sys.stderr)
        return 2
    cap = None
    records = []
    try:
        q = ad.read_joint_positions()
        q_now, gap_now = list(q[:A.ARM_DOF]), float(q[A.ARM_DOF])
        print(f"arm now: {ticks_str([A.rad_to_ticks(v) for v in q_now])}")
        if any(abs(x - y) > 0.17 for x, y in zip(q_now[:4], poses[first][:4])) or abs(q_now[4] - poses[first][4]) > 0.35:
            print(f"refused: the arm is not near {first}; nothing moves", file=sys.stderr)
            return 3
        if not ad.activate():
            print("activate failed", file=sys.stderr)
            return 2
        cap = W.open_wrist(1280, 720)
        goal = list(poses[first])            # the goal the servos hold; moves start from the goal, not the sagged reading
        goal_first = list(goal)
        goal_first[0] = q_now[0]
        for i, name in enumerate(names):
            start = goal if i else q_now
            step = A.goto_step(list(start), gap_now, list(poses[name]), gap_now, speed=a.speed)
            traj = A.cycle_trajectory([step], sim=False)
            t0 = time.monotonic()
            for p in traj.points:
                while time.monotonic() - t0 < float(p.time_from_start):
                    time.sleep(0.002)
                ad.write_joint_positions(list(p.positions))
            goal = list(poses[name])
            time.sleep(SETTLE_S)
            read = list(ad.read_joint_positions() or [])[:A.ARM_DOF]
            for _ in range(6):
                ok, frame = cap.read()
            if not ok:
                print(f"  {name}: no frame", file=sys.stderr)
                continue
            frame = W.upright(frame)
            rvec, tvec, n, cc, ci = board_pose(frame, b, K, dist)
            stem = STATE / f"pose_{a.tag + '_' if a.tag else ''}{i + 1:02d}_{name}"
            cv2.imwrite(f"{stem}.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            shown = frame.copy()
            if cc is not None:
                for (u, v) in cc.reshape(-1, 2):
                    cv2.circle(shown, (int(u), int(v)), 6, (0, 255, 0), 2)
                if rvec is not None:
                    cv2.drawFrameAxes(shown, K, dist, rvec, tvec, 0.05, 3)
            cv2.putText(shown, f"{name}: {n} corners", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.imwrite(f"{stem}_board.jpg", shown, [cv2.IMWRITE_JPEG_QUALITY, 90])
            rec = {"name": name, "ticks_cmd": [A.rad_to_ticks(v) for v in poses[name]],
                   "ticks_read": [A.rad_to_ticks(v) for v in read], "rad_read": read, "corners": n,
                   "rvec": None if rvec is None else rvec.tolist(), "tvec": None if tvec is None else tvec.tolist(),
                   "frame": f"{stem}.jpg"}
            records.append(rec)
            d = "-" if tvec is None else f"{np.linalg.norm(tvec) * 100:.1f} cm from the lens"
            print(f"  {name:12s} read {ticks_str(rec['ticks_read'])}  board: {n} corners, {d}")
        out_json = STATE / (f"records_{a.tag}.json" if a.tag else "records.json")
        out_json.write_text(json.dumps({"square_m": a.square, "marker_m": a.marker,
                                        "intrinsics": str(INTRINSICS), "records": records}, indent=1))
        print(f"{len(records)} records -> {out_json}")
        return 0
    finally:
        if cap is not None:
            cap.release()
        ad._enabled = False  # noqa: SLF001  (disconnect would write torque off; the arm stays up and held)
        print("torque LEFT ON: the arm is at its last pose (tools/moss_arm_observe.py --back folds it from look_down)")
        ad.disconnect()


# ------------------------------------------------------------------ solve
def skew(v):
    x, y, z = v
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], float)


def tsai_lenz(pairs):
    """Closed form (Tsai & Lenz 1989) for AX = XB on every pair of views. pairs: (T_base_tool, T_cam_target)."""
    rows_r, rhs_r, As, Bs = [], [], [], []
    n = len(pairs)
    for i in range(n):
        for j in range(i + 1, n):
            Gi, Ci = pairs[i]
            Gj, Cj = pairs[j]
            Amat = inv(Gj) @ Gi
            Bmat = Cj @ inv(Ci)
            As.append(Amat); Bs.append(Bmat)
            ra, rb = rotvec(Amat[:3, :3]), rotvec(Bmat[:3, :3])
            ta, tb = np.linalg.norm(ra), np.linalg.norm(rb)
            if ta < 1e-6 or tb < 1e-6:
                continue
            Pa = 2 * math.sin(ta / 2) * ra / ta
            Pb = 2 * math.sin(tb / 2) * rb / tb
            rows_r.append(skew(Pa + Pb)); rhs_r.append(Pb - Pa)
    M = np.vstack(rows_r); v = np.concatenate(rhs_r)
    Px_, *_ = np.linalg.lstsq(M, v, rcond=None)
    Px = 2 * Px_ / math.sqrt(1 + float(Px_ @ Px_))
    n2 = float(Px @ Px)
    Rx = (1 - n2 / 2) * np.eye(3) + 0.5 * (np.outer(Px, Px) + math.sqrt(max(0.0, 4 - n2)) * skew(Px))
    rows_t, rhs_t = [], []
    for Amat, Bmat in zip(As, Bs):
        rows_t.append(Amat[:3, :3] - np.eye(3)); rhs_t.append(Rx @ Bmat[:3, 3] - Amat[:3, 3])
    tx, *_ = np.linalg.lstsq(np.vstack(rows_t), np.concatenate(rhs_t), rcond=None)
    return T(Rx, tx)


def consensus_residual(x, pairs):
    """Every view must give the same board pose in the chassis frame: residuals against view 0."""
    Rm, _ = cv2.Rodrigues(np.asarray(x[:3], float))
    X = T(Rm, x[3:6])
    B0 = pairs[0][0] @ X @ pairs[0][1]
    res = []
    for Tbt, Tct in pairs[1:]:
        Bi = Tbt @ X @ Tct
        D = inv(B0) @ Bi
        res.extend(D[:3, 3])
        res.extend(rotvec(D[:3, :3]) * 0.1)        # 0.1 m per radian: 1 deg counts like 1.7 mm
    return np.array(res)


def refine(X0, pairs, iters=40):
    """Levenberg-Marquardt on the consensus residual, numeric Jacobian, 6 parameters."""
    x = np.concatenate([rotvec(X0[:3, :3]), X0[:3, 3]])
    lam = 1e-3
    r = consensus_residual(x, pairs)
    for _ in range(iters):
        J = np.zeros((len(r), 6))
        for k in range(6):
            dx = np.zeros(6); dx[k] = 1e-6
            J[:, k] = (consensus_residual(x + dx, pairs) - r) / 1e-6
        H = J.T @ J
        g = J.T @ r
        step = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-12), -g)
        r_new = consensus_residual(x + step, pairs)
        if r_new @ r_new < r @ r:
            x, r, lam = x + step, r_new, max(lam / 3, 1e-9)
        else:
            lam *= 5
        if np.linalg.norm(step) < 1e-9:
            break
    Rm, _ = cv2.Rodrigues(x[:3])
    return T(Rm, x[3:6])


def solve_from(pairs, method="tsai+lm"):
    """pairs: list of (T_base_tool, T_cam_target). Returns T_tool_cam."""
    X = tsai_lenz(pairs)
    if method == "tsai":
        return X
    return refine(X, pairs)


def board_points_in_base(pairs, Ttc):
    pts = []
    for Tbt, Tct in pairs:
        Tbb = Tbt @ Ttc @ Tct
        pts.append(Tbb[:3, 3])
    pts = np.array(pts)
    return pts, float(np.max(np.linalg.norm(pts - pts.mean(0), axis=1)))


def cmd_solve(a) -> int:
    files = sorted(STATE.glob("records*.json"))
    recs = []
    for f in files:
        recs.extend(json.loads(f.read_text())["records"])
    print(f"{len(recs)} records from {', '.join(f.name for f in files)}")
    kin = ArmKin.load()
    pairs, used = [], []
    for r in recs:
        if r["rvec"] is None:
            continue
        p, R = kin.tool(r["rad_read"])
        Tbt = T(R, p)
        Rct, _ = cv2.Rodrigues(np.array(r["rvec"]))
        pairs.append((Tbt, T(Rct, r["tvec"])))
        used.append(r["name"])
    if len(pairs) < 4:
        raise SystemExit(f"only {len(pairs)} usable views, need at least 4")
    best = None
    for mname in ("tsai", "tsai+lm"):
        Ttc = solve_from(pairs, mname)
        pts, spread = board_points_in_base(pairs, Ttc)
        z_axes = [(Tbt @ Ttc @ Tct)[:3, 2] for Tbt, Tct in pairs]
        tilt = float(np.degrees(np.mean([math.acos(max(-1, min(1, float(z[2])))) for z in z_axes])))
        print(f"  {mname:10s} camera in tool: t {np.round(Ttc[:3, 3] * 100, 2)} cm, rot {np.round(np.degrees(rotvec(Ttc[:3, :3])), 1)} deg; "
              f"board origin spread {spread * 1000:.1f} mm, mean {np.round(pts.mean(0) * 100, 1)} cm (chassis), board normal {tilt:.1f} deg from up")
        if best is None or spread < best[1]:
            best = (mname, spread, Ttc, pts)
    mname, spread, Ttc, pts = best
    verdict = "PASS" if spread <= a.tolerance_m else "FAIL"
    rv = np.degrees(rotvec(Ttc[:3, :3]))
    text = (f"camera_in_tool_xyz_m: [{', '.join(f'{v:.5f}' for v in Ttc[:3, 3])}]\n"
            f"camera_in_tool_rotvec_deg: [{', '.join(f'{v:.3f}' for v in rv)}]\n"
            f"camera_in_tool_matrix: {np.round(Ttc, 6).tolist()}\n"
            f"method: {mname}\nviews_used: {len(pairs)} ({', '.join(used)})\n"
            f"board_origin_spread_m: {spread:.4f}\nboard_origin_mean_chassis_m: [{', '.join(f'{v:.4f}' for v in pts.mean(0))}]\n"
            f"check: {verdict} (tolerance {a.tolerance_m:.3f} m)\nframe_orientation: upright (raw stream turned 180 deg)\n"
            f"tool_frame: moss_dimos/arm_kin tool() (config/arm_chain.json), chassis frame\n"
            f"written: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(text)
    if verdict == "PASS" or a.force:
        EXTRINSICS.write_text(text)
        print(f"-> {EXTRINSICS}")
    else:
        print("not written: the check failed (use --force to write anyway)")
    return 0 if verdict == "PASS" else 1


# ------------------------------------------------------------------ selftest
def cmd_selftest(a) -> int:
    rng = np.random.default_rng(7)
    kin = ArmKin.load()
    base = [A.ticks_to_rad(t) for t in (2865, 1583, 2404, 2889, 3214)]
    Rx, _ = cv2.Rodrigues(np.array([0.0, math.radians(-20.0), 0.0]))
    Ttc_true = T(Rx, [-0.06, 0.004, 0.012])                 # camera on the tool, tilted
    Tbb_true = T(np.eye(3), [0.26, 0.0, 0.0])               # board flat on the floor ahead
    pairs = []
    for _, dv in VARIATIONS:
        q = [b + d / A.TICKS_PER_RAD + rng.normal(0, 0.002) for b, d in zip(base, dv)]
        p, R = kin.tool(q)
        Tbt = T(R, p)
        Tct = inv(Tbt @ Ttc_true) @ Tbb_true
        # measurement noise: 0.5 mm, 0.1 deg
        n_r, _ = cv2.Rodrigues(rng.normal(0, math.radians(0.1), 3))
        Tct = Tct @ T(n_r, rng.normal(0, 0.0005, 3))
        pairs.append((Tbt, Tct))
    Ttc = solve_from(pairs, "tsai+lm")
    dt = np.linalg.norm(Ttc[:3, 3] - Ttc_true[:3, 3]) * 1000
    dr = np.degrees(np.linalg.norm(rotvec(Ttc[:3, :3].T @ Ttc_true[:3, :3])))
    pts, spread = board_points_in_base(pairs, Ttc)
    print(f"selftest: {len(pairs)} views, camera recovered within {dt:.2f} mm and {dr:.3f} deg, board spread {spread * 1000:.2f} mm")
    # with these small rotations (7 to 10 deg) and 0.5 mm / 0.1 deg of noise, the method lands within ~2.5 mm
    ok = dt < 3.0 and dr < 0.5 and spread < 0.004
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--square", type=float, default=W.SQUARE_M)
    ap.add_argument("--marker", type=float, default=W.MARKER_M)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("poses")
    pp.add_argument("--big", action="store_true", help="the second series, rotations twice as large")
    pr = sub.add_parser("run")
    pr.add_argument("--poses", default=str(HANDEYE_POSES))
    pr.add_argument("--tag", default="", help="records_<tag>.json instead of records.json")
    pr.add_argument("--speed", type=float, default=SPEED)
    pr.add_argument("--dry-run", action="store_true")
    ps = sub.add_parser("solve")
    ps.add_argument("--tolerance-m", type=float, default=0.010)
    ps.add_argument("--force", action="store_true")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    return {"poses": cmd_poses, "run": cmd_run, "solve": cmd_solve, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
