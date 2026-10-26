#!/usr/bin/env python3
"""The wrist camera against a ChArUco board: capture the frames, then solve the intrinsics.

    .venv/bin/python tools/moss_wrist_calib.py capture --seconds 90      # keep the frames that show the board
    .venv/bin/python tools/moss_wrist_calib.py solve                      # intrinsics from the kept frames
    .venv/bin/python tools/moss_wrist_calib.py selftest                   # a synthetic camera round trip, no hardware

The board is docs/calibration's ChArUco 7x5, squares 30 mm, markers 22 mm,
DICT_5X5_100 (the same as Chloé's). --square and --marker take the printed
sizes if the print was not at 100 %.

capture: one frame every --every seconds; a frame is kept when at least
--min-corners ChArUco corners are found; the kept frames and an annotated copy
go to --out (default ~/.local/state/moss/wrist_calib). Stop with --frames or
--seconds, or Ctrl-C.

solve: cv2.aruco calibration on the kept frames; writes intrinsics.yaml (fx, fy,
cx, cy, distortion, image size, reprojection error, frames used).
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

OUT_DEFAULT = "~/.local/state/moss/wrist_calib"
WRIST_DEV_GLOB = "/dev/v4l/by-id/usb-Xitech*-index0"
# The wrist camera's raw stream is upside down for the way it is mounted (the jaws come out at the
# top of the raw frame, the floor ahead at the bottom, seen on the robot). Every frame is turned
# by 180 degrees here before anything looks at it, so the far floor is at the top, as the eye sees it.
RAW_ROTATE = cv2.ROTATE_180


def upright(frame):
    return cv2.rotate(frame, RAW_ROTATE)
SQUARES = (7, 5)
SQUARE_M = 0.030
MARKER_M = 0.022
DICT = cv2.aruco.DICT_5X5_100


def board(square_m: float, marker_m: float):
    d = cv2.aruco.getPredefinedDictionary(DICT)
    return cv2.aruco.CharucoBoard(SQUARES, square_m, marker_m, d)


def detect(b, gray):
    """ChArUco corners and ids of the board in a grey image, or (None, None)."""
    det = cv2.aruco.CharucoDetector(b)
    cc, ci, _mc, _mi = det.detectBoard(gray)
    if cc is None or ci is None or len(cc) < 4:
        return None, None
    return cc, ci


def open_wrist(width: int, height: int):
    devs = glob.glob(WRIST_DEV_GLOB)
    if not devs:
        raise SystemExit(f"no wrist camera at {WRIST_DEV_GLOB}")
    cap = cv2.VideoCapture(devs[0])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    for _ in range(5):
        cap.read()
    return cap


def cmd_capture(a) -> int:
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    b = board(a.square, a.marker)
    cap = open_wrist(a.width, a.height)
    kept, seen, t0, last = 0, 0, time.monotonic(), 0.0
    last_centre, last_width = None, None       # a frame is kept only when the board MOVED since the last kept one
    print(f"capture: one look every {a.every:g} s, keep >= {a.min_corners} corners and the board moved "
          f"(>= {a.min_move:g} px or {a.min_scale:.0%} in size) since the last kept frame, "
          f"stop at {a.frames} frames or {a.seconds:g} s; frames -> {out}")
    try:
        while True:
            ok, frame = cap.read()
            now = time.monotonic()
            if not ok:
                time.sleep(0.1)
                continue
            if now - last < a.every:
                continue
            last = now
            seen += 1
            frame = upright(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cc, ci = detect(b, gray)
            n = 0 if cc is None else len(cc)
            moved = True
            if n >= a.min_corners:
                pts = cc.reshape(-1, 2)
                centre, width = pts.mean(0), float(pts[:, 0].max() - pts[:, 0].min())
                if last_centre is not None:
                    moved = (float(np.linalg.norm(centre - last_centre)) >= a.min_move
                             or abs(width - last_width) >= a.min_scale * last_width)
            if n >= a.min_corners and not moved:
                print(f"  look {seen:3d}: {n} corners, board did not move, not kept  (t = {now - t0:5.1f} s)")
            elif n >= a.min_corners:
                last_centre, last_width = centre, width
                kept += 1
                stem = out / f"frame_{kept:03d}"
                cv2.imwrite(f"{stem}.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 96])
                shown = frame.copy()
                for (u, v), cid in zip(cc.reshape(-1, 2), ci.reshape(-1)):   # OpenCV 5's own drawer asserts on shapes
                    cv2.circle(shown, (int(u), int(v)), 6, (0, 255, 0), 2)
                    cv2.putText(shown, str(int(cid)), (int(u) + 6, int(v) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                cv2.putText(shown, f"{n} corners", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.imwrite(f"{stem}_corners.jpg", shown, [cv2.IMWRITE_JPEG_QUALITY, 90])
                print(f"  kept {kept:3d}: {n} corners  (t = {now - t0:5.1f} s)")
            else:
                print(f"  look {seen:3d}: {n} corners, not kept  (t = {now - t0:5.1f} s)")
            if (a.frames and kept >= a.frames) or (a.seconds and now - t0 >= a.seconds):
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
    print(f"capture done: {kept} frames kept out of {seen} looks")
    return 0 if kept else 1


def solve_frames(b, frames, size_wh):
    """Intrinsics from the frames (grey images). Returns (K, dist, rms, used)."""
    all_obj, all_img, used = [], [], 0
    for gray in frames:
        cc, ci = detect(b, gray)
        if cc is None or len(cc) < 6:
            continue
        obj, img = b.matchImagePoints(cc, ci)
        if obj is None or len(obj) < 6:
            continue
        all_obj.append(obj)
        all_img.append(img)
        used += 1
    if used < 4:
        raise SystemExit(f"only {used} usable frames, need at least 4")
    rms, K, dist, _r, _t = cv2.calibrateCamera(all_obj, all_img, size_wh, None, None)
    return K, dist, float(rms), used


def cmd_solve(a) -> int:
    out = Path(os.path.expanduser(a.out))
    paths = sorted(p for p in glob.glob(str(out / "frame_*.jpg")) if not p.endswith("_corners.jpg"))
    if not paths:
        raise SystemExit(f"no frames in {out}")
    # frames captured by an earlier version were stored raw (upside down): --raw-frames turns them here
    frames = [cv2.cvtColor(upright(cv2.imread(p)) if a.raw_frames else cv2.imread(p), cv2.COLOR_BGR2GRAY) for p in paths]
    h, w = frames[0].shape[:2]
    K, dist, rms, used = solve_frames(board(a.square, a.marker), frames, (w, h))
    text = (f"image_width: {w}\nimage_height: {h}\n"
            f"fx: {K[0, 0]:.3f}\nfy: {K[1, 1]:.3f}\ncx: {K[0, 2]:.3f}\ncy: {K[1, 2]:.3f}\n"
            f"distortion: [{', '.join(f'{float(v):.6f}' for v in dist.ravel())}]\n"
            f"reprojection_error_px: {rms:.4f}\nframes_used: {used}\nframes_found: {len(paths)}\n"
            f"board: charuco 7x5, square_m {a.square}, marker_m {a.marker}, DICT_5X5_100\n"
            f"camera: wrist ({WRIST_DEV_GLOB})\nframe_orientation: raw stream turned 180 deg (upright: floor ahead at the top)\n"
            f"written: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    (out / "intrinsics.yaml").write_text(text)
    print(text)
    print(f"-> {out / 'intrinsics.yaml'}")
    return 0


def cmd_selftest(a) -> int:
    """A known camera renders the board at random poses; the solver must give it back."""
    b = board(SQUARE_M, MARKER_M)
    w, h = 1280, 720
    fx, fy, cx, cy = 900.0, 905.0, 650.0, 350.0
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    dist = np.array([-0.05, 0.02, 0.0, 0.0, 0.0])
    img_board = b.generateImage((700, 500), marginSize=20, borderBits=1)
    bw, bh = b.getChessboardSize()[0] * SQUARE_M, b.getChessboardSize()[1] * SQUARE_M
    src = np.float32([[20, 20], [680, 20], [680, 480], [20, 480]])
    corners_board = np.float32([[0, 0, 0], [bw, 0, 0], [bw, bh, 0], [0, bh, 0]])
    rng = np.random.default_rng(3)
    frames = []
    for _ in range(14):
        rvec = rng.uniform(-0.45, 0.45, 3)
        tvec = np.array([rng.uniform(-0.06, 0.06), rng.uniform(-0.04, 0.04), rng.uniform(0.30, 0.45)])
        rvec[2] += rng.uniform(-0.3, 0.3)
        dst, _ = cv2.projectPoints(corners_board, rvec, tvec, K, dist)
        H = cv2.getPerspectiveTransform(src, dst.reshape(-1, 2).astype(np.float32))
        frames.append(cv2.warpPerspective(img_board, H, (w, h), borderValue=200))
    K2, dist2, rms, used = solve_frames(b, frames, (w, h))
    errs = {"fx": abs(K2[0, 0] - fx), "fy": abs(K2[1, 1] - fy), "cx": abs(K2[0, 2] - cx), "cy": abs(K2[1, 2] - cy)}
    print(f"selftest: {used} frames, rms {rms:.3f} px, recovered fx {K2[0, 0]:.1f} fy {K2[1, 1]:.1f} "
          f"cx {K2[0, 2]:.1f} cy {K2[1, 2]:.1f} (truth {fx:.0f} {fy:.0f} {cx:.0f} {cy:.0f})")
    tol = 0.02 * fx
    ok = used >= 8 and all(e <= tol for e in errs.values())
    print("SELFTEST PASSED" if ok else f"SELFTEST FAILED (tolerance {tol:.1f} px): {errs}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--square", type=float, default=SQUARE_M, help="printed square size in metres")
    ap.add_argument("--marker", type=float, default=MARKER_M, help="printed marker size in metres")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("capture")
    pc.add_argument("--every", type=float, default=1.5)
    pc.add_argument("--frames", type=int, default=20)
    pc.add_argument("--seconds", type=float, default=120.0)
    pc.add_argument("--min-corners", type=int, default=12)
    pc.add_argument("--min-move", type=float, default=40.0, help="pixels the board centre must move between kept frames")
    pc.add_argument("--min-scale", type=float, default=0.10, help="or this fraction of change in the board's width")
    pc.add_argument("--width", type=int, default=1280)
    pc.add_argument("--height", type=int, default=720)
    ps = sub.add_parser("solve")
    ps.add_argument("--raw-frames", action="store_true", help="the stored frames are raw (upside down): turn them first")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    return {"capture": cmd_capture, "solve": cmd_solve, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
