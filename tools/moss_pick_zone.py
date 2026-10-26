#!/usr/bin/env python3
"""The pick zone on the floor from the hand-taught marks: a smooth closed contour, a little wider.

    .venv/bin/python tools/moss_pick_zone.py build --offset-cm 1.5     # config/arm_pick_zone.json
    .venv/bin/python tools/moss_pick_zone.py show                       # the contour's points in the chassis frame

The marks (config/arm_reach_marks.json) give the tool point of each taught pick pose on the
floor (chassis frame, moss_dimos/arm_kin). They are ordered around their centre, joined by a
closed Catmull-Rom curve (it passes through every mark), and the curve is pushed outward by
--offset-cm. The result is the polygon the camera image shows and the pick logic tests against.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from moss_dimos.arm_kin import ArmKin  # noqa: E402

MARKS = ROOT / "config" / "arm_reach_marks.json"
ZONE = ROOT / "config" / "arm_pick_zone.json"


def catmull_rom_closed(points, per_segment=10):
    """A closed curve through every point (Catmull-Rom, tension 0.5)."""
    P = np.asarray(points, float)
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for k in range(per_segment):
            t = k / per_segment
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def build(offset_m: float):
    marks = json.loads(MARKS.read_text())["marks"]
    kin = ArmKin.load()
    pts, names = [], []
    for m in marks:
        p, _ = kin.tcp(m["rad"])
        pts.append(p[:2])
        names.append(m["name"])
    pts = np.array(pts)
    centre = pts.mean(0)
    order = np.argsort(np.arctan2(pts[:, 1] - centre[1], pts[:, 0] - centre[0]))
    ring = pts[order]
    curve = catmull_rom_closed(ring)
    # outward offset: along the local normal of the curve (left-hand normal of the tangent, oriented away from the centre)
    nxt = np.roll(curve, -1, axis=0)
    prv = np.roll(curve, 1, axis=0)
    tang = nxt - prv
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
    normal = np.stack([tang[:, 1], -tang[:, 0]], axis=1)
    away = np.sign(np.sum((curve - centre) * normal, axis=1))
    normal *= away[:, None]
    wide = curve + offset_m * normal
    doc = {"format": "moss-arm-pick-zone/1",
           "about": "closed contour of the floor the gripper can pick from, through the hand-taught marks, pushed outward",
           "frame": "chassis (model world of config/arm_chain.json), metres, floor",
           "offset_m": offset_m,
           "marks_used": [names[i] for i in order],
           "marks_xy_m": [[round(float(v), 4) for v in ring[i]] for i in range(len(ring))],
           "polygon_xy_m": [[round(float(v), 4) for v in p] for p in wide],
           "written": time.strftime("%Y-%m-%d %H:%M:%S")}
    ZONE.write_text(json.dumps(doc, indent=1))
    return doc


def tape(image_path: str, joints_ticks: list[int], z_floor_m: float, offset_m: float, v_max: int = 120, shrink_px: float = 12.0):
    """The zone from the black tape seen by the wrist camera: dark pixels (the board's squares sit inside the
    ring, the jaws are masked out), their convex hull, each hull pixel cast onto the floor plane z = z_floor
    through the calibrated camera at the given joints. Returns the document written to config/arm_pick_zone.json."""
    import cv2
    sys.path.insert(0, str(ROOT / "tools"))
    import moss_wrist_handeye as H  # noqa: E402
    from moss_dimos import arm as A  # noqa: E402
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    dark = cv2.inRange(hsv, (0, 0, 0), (180, 160, v_max))
    green = cv2.inRange(hsv, (40, 80, 80), (90, 255, 255))
    dark[cv2.dilate(green, np.ones((7, 7), np.uint8)) > 0] = 0      # drawings on an annotated frame
    dark[628:, :] = 0; dark[:, :150] = 0; dark[:, 1130:] = 0
    # the jaws' shadow lies just under the tape's lower edge, which runs from about (240, 585) to (850, 615) in
    # the recognition pose: drop the dark pixels more than 8 px below that line
    xx = np.arange(w)
    y_edge = 585 + (xx - 240) * (30.0 / 610.0) + 8
    for x_ in range(w):
        dark[int(min(h - 1, max(0, y_edge[x_]))):, x_] = 0        # the black gripper parts at the very bottom, the frame's edges
    dark[600:, 900:] = 0                                            # the right jaw's black base
    # the board's own black squares are dark too: find the board from its markers (a few corners are enough),
    # map its chessboard rectangle into the image with a homography, and blank it out with a margin
    import moss_wrist_calib as W  # noqa: E402
    b = W.board(W.SQUARE_M, W.MARKER_M)
    cc, ci = W.detect(b, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    if cc is not None and len(cc) >= 4:
        obj = b.getChessboardCorners()[ci.reshape(-1)][:, :2]
        Hm, _ = cv2.findHomography(obj.astype(np.float64), cc.reshape(-1, 2).astype(np.float64))
        cols, rows = b.getChessboardSize()
        m = 0.004
        rect = np.array([[-m, -m], [cols * W.SQUARE_M + m, -m], [cols * W.SQUARE_M + m, rows * W.SQUARE_M + m], [-m, rows * W.SQUARE_M + m]])
        quad = cv2.perspectiveTransform(rect.reshape(-1, 1, 2), Hm).reshape(-1, 2).astype(np.int32)
        cv2.fillPoly(dark, [quad], 0)
        # the tape's crown crosses the white paper above the squares, under the lamps' glare: there, anything
        # that is not white is the tape (the paper margin above the squares is 20 mm on the printed sheet)
        above = np.array([[-0.03, -0.017], [cols * W.SQUARE_M + 0.03, -0.017], [cols * W.SQUARE_M + 0.03, -m], [-0.03, -m]])
        quad_above = cv2.perspectiveTransform(above.reshape(-1, 1, 2), Hm).reshape(-1, 2).astype(np.int32)
        band = np.zeros_like(dark)
        cv2.fillPoly(band, [quad_above], 255)
        not_white = cv2.inRange(hsv, (0, 0, 0), (180, 130, 200))   # grey-blue tape, not the white paper, not the yellow card
        dark = cv2.bitwise_or(dark, cv2.bitwise_and(not_white, band))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ys, xs = np.nonzero(dark)
    hull = cv2.convexHull(np.stack([xs, ys], axis=1).astype(np.int32))
    # the hull sits on the tape's outer edge: erode the filled hull by about half the tape's width, which moves
    # every edge inward along its own normal and keeps the corners (a radial shrink cut the sharp ones)
    filled = np.zeros((h, w), np.uint8)
    cv2.fillPoly(filled, [hull], 255)
    k = int(round(shrink_px))
    eroded = cv2.erode(filled, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    cnts, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inner = max(cnts, key=cv2.contourArea)
    hull = cv2.approxPolyDP(inner, 3.0, True).reshape(-1, 2).astype(np.float64)
    K, dist = H.load_intrinsics()
    X = H.load_extrinsics() if hasattr(H, "load_extrinsics") else None
    if X is None:
        for line in H.EXTRINSICS.read_text().splitlines():
            if line.startswith("camera_in_tool_matrix:"):
                X = np.array(json.loads(line.split(":", 1)[1].strip()), float)
    kin = ArmKin.load()
    q = [A.ticks_to_rad(t) for t in joints_ticks]
    p_tool, R_tool = kin.tool(q)
    T_base_cam = H.T(R_tool, p_tool) @ X
    # pixels -> rays in the camera -> floor plane
    und = cv2.undistortPoints(hull.reshape(-1, 1, 2).astype(np.float64), K, dist).reshape(-1, 2)
    floor = []
    for u, v in und:
        d_cam = np.array([u, v, 1.0])
        d_base = T_base_cam[:3, :3] @ d_cam
        o = T_base_cam[:3, 3]
        if abs(d_base[2]) < 1e-6:
            continue
        s_ = (z_floor_m - o[2]) / d_base[2]
        if s_ <= 0:
            continue
        floor.append((o + s_ * d_base)[:2])
    floor = np.array(floor)
    centre = floor.mean(0)
    out_pts = floor + offset_m * (floor - centre) / (np.linalg.norm(floor - centre, axis=1, keepdims=True) + 1e-9)
    doc = {"format": "moss-arm-pick-zone/1",
           "about": "closed contour of the floor the gripper can pick from, measured on the black tape laid on the floor, seen by the wrist camera and cast onto the floor plane",
           "frame": "chassis (model world of config/arm_chain.json), metres, floor plane z = %.3f (the plane the chain puts the floor at)" % z_floor_m,
           "source": {"image": str(image_path), "joints_ticks": list(joints_ticks), "hull_px": hull.tolist()},
           "offset_m": offset_m,
           "polygon_xy_m": [[round(float(a), 4) for a in p] for p in out_pts],
           "written": time.strftime("%Y-%m-%d %H:%M:%S")}
    ZONE.write_text(json.dumps(doc, indent=1))
    return doc, hull


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("build")
    pb.add_argument("--offset-cm", type=float, default=1.5)
    pt = sub.add_parser("tape")
    pt.add_argument("--image", required=True, help="an upright wrist frame showing the whole tape ring")
    pt.add_argument("--joints", required=True, help="five ticks read when the image was taken")
    pt.add_argument("--z-floor-cm", type=float, default=-2.0, help="where the chain puts the floor (hand-eye board mean z)")
    pt.add_argument("--offset-cm", type=float, default=0.0)
    pt.add_argument("--v-max", type=int, default=120, help="darkness threshold (HSV value) for the tape")
    pt.add_argument("--shrink-px", type=float, default=12.0, help="pull the outer edge onto the tape's middle")
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "tape":
        doc, hull = tape(a.image, [int(t) for t in a.joints.split(",")], a.z_floor_cm / 100.0, a.offset_cm / 100.0, a.v_max, a.shrink_px)
        xy = np.array(doc["polygon_xy_m"])
        print(f"tape: hull of {len(hull)} px -> {len(xy)} floor points, x {xy[:, 0].min():.3f}..{xy[:, 0].max():.3f} m, "
              f"y {xy[:, 1].min():.3f}..{xy[:, 1].max():.3f} m -> {ZONE}")
        return 0
    if a.cmd == "build":
        doc = build(a.offset_cm / 100.0)
        xy = np.array(doc["polygon_xy_m"])
        print(f"{len(xy)} points, x {xy[:, 0].min():.3f}..{xy[:, 0].max():.3f} m, y {xy[:, 1].min():.3f}..{xy[:, 1].max():.3f} m, "
              f"offset {a.offset_cm:g} cm, marks {doc['marks_used']} -> {ZONE}")
    else:
        doc = json.loads(ZONE.read_text())
        for p in doc["polygon_xy_m"]:
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
