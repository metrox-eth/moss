#!/usr/bin/env python3
"""The pick zone drawn in the wrist camera's image, with the detector on top.

    .venv/bin/python tools/moss_zone_view.py                      # one frame from the wrist camera, the zone, the marks
    .venv/bin/python tools/moss_zone_view.py --detect             # ... and YOLOE (dimOS's detector) with litter words
    .venv/bin/python tools/moss_zone_view.py --image some.jpg     # on a stored upright frame instead of the camera

The camera's pose comes from the servos (moss_dimos/arm_kin on the joints read now) and
config/wrist_camera_extrinsics.yaml; the image points from config/wrist_camera_intrinsics.yaml.
Drawn: the pick poses taught by hand (config/arm_reach_marks.json, tool point of each, joined
in their order) and, when present, the hull of the CAD reach table (config/arm_floor_reach.json).
Output: ~/.local/state/moss/zone_view/zone_<time>.jpg
"""
from __future__ import annotations

import argparse
import json
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
import moss_wrist_handeye as H  # noqa: E402

MARKS = ROOT / "config" / "arm_reach_marks.json"
REACH = ROOT / "config" / "arm_floor_reach.json"
OUT = Path(os.path.expanduser("~/.local/state/moss/zone_view"))
LITTER_WORDS = ["can", "bottle", "paper", "wrapper", "plastic bag", "cup", "cardboard", "trash"]


def load_extrinsics(path=H.EXTRINSICS):
    for line in Path(path).read_text().splitlines():
        if line.startswith("camera_in_tool_matrix:"):
            return np.array(json.loads(line.split(":", 1)[1].strip()), float)
    raise SystemExit(f"no camera_in_tool_matrix in {path}")


def read_arm():
    from moss_dimos.arm_feetech import FeetechSo101Adapter  # noqa: E402
    port = os.environ.get(A.ARM_PORT_ENV, A.ARM_PORT_DEFAULT)
    ad = FeetechSo101Adapter(address=port)
    if not ad.connect():
        raise SystemExit(f"the bus did not open on {port}")
    try:
        q = ad.read_joint_positions()
    finally:
        ad.disconnect()
    return list(q[:A.ARM_DOF])


def project(points_base, T_base_cam, K, dist):
    T_cam_base = H.inv(T_base_cam)
    rvec, _ = cv2.Rodrigues(T_cam_base[:3, :3])
    pts, _ = cv2.projectPoints(np.asarray(points_base, float).reshape(-1, 1, 3), rvec, T_cam_base[:3, 3], K, dist)
    z = (T_cam_base[:3, :3] @ np.asarray(points_base, float).T + T_cam_base[:3, 3:4])[2]
    return pts.reshape(-1, 2), z


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None, help="an upright frame instead of the camera")
    ap.add_argument("--joints", default=None, help="five ticks instead of reading the servos, e.g. 2865,1583,2404,2889,3214")
    ap.add_argument("--detect", action="store_true", help="run YOLOE with litter words on the frame")
    ap.add_argument("--no-reach", action="store_true", help="skip the CAD reach hull")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    K, dist = H.load_intrinsics()
    X = load_extrinsics()
    kin = ArmKin.load()

    if a.joints:
        q = [A.ticks_to_rad(float(t)) for t in a.joints.split(",")]
    else:
        q = read_arm()
    print("arm: " + " ".join(f"{j} {A.rad_to_ticks(v)}" for j, v in zip(A.ARM_JOINTS, q)))
    p, R = kin.tool(q)
    T_base_cam = H.T(R, p) @ X

    if a.image:
        frame = cv2.imread(a.image)
    else:
        cap = W.open_wrist(1280, 720)
        for _ in range(6):
            ok, frame = cap.read()
        cap.release()
        frame = W.upright(frame)
    shown = frame.copy()

    # the CAD reach hull (tool points on the floor), in orange
    if not a.no_reach and REACH.exists():
        reach = json.loads(REACH.read_text())
        floor = np.array([r["tcp_chassis_m"] for r in reach["poses"]], float)
        uv, z = project(floor, T_base_cam, K, dist)
        h_img, w_img = frame.shape[:2]
        inside = (z > 0.05) & (uv[:, 0] >= 0) & (uv[:, 0] < w_img) & (uv[:, 1] >= 0) & (uv[:, 1] < h_img)
        pts = uv[inside].astype(np.int32)
        if len(pts) >= 3:
            hull = cv2.convexHull(pts)
            cv2.polylines(shown, [hull], True, (0, 140, 255), 2)
            cv2.putText(shown, "CAD reach (hull)", (int(hull[0][0][0]), int(hull[0][0][1]) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        print(f"CAD reach: {inside.sum()}/{len(floor)} floor points in front of the camera")

    # the hand-taught marks: tool point of each pose, joined around the perimeter (by angle about their centre), in green
    zone_poly = None
    if MARKS.exists():
        marks = json.loads(MARKS.read_text())["marks"]
        tcp = []
        for m in marks:
            pm, Rm = kin.tcp(m["rad"])
            tcp.append(pm)
        uv, z = project(tcp, T_base_cam, K, dist)
        centre = uv.mean(0)
        order = np.argsort(np.arctan2(uv[:, 1] - centre[1], uv[:, 0] - centre[0]))
        zone_poly = uv[order].astype(np.int32)
        zone_file = ROOT / "config" / "arm_pick_zone.json"
        if zone_file.exists():
            # the smooth, widened contour built by tools/moss_pick_zone.py replaces the straight lines
            zdoc = json.loads(zone_file.read_text())
            zxy = np.array([[x, y, 0.0] for x, y in zdoc["polygon_xy_m"]], float)
            zuv, _ = project(zxy, T_base_cam, K, dist)
            zone_poly = zuv.astype(np.int32)
            cv2.putText(shown, f"pick zone (+{zdoc['offset_m'] * 100:g} cm)", (int(zuv[0][0]) + 8, int(zuv[0][1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)
        cv2.polylines(shown, [zone_poly], True, (0, 220, 0), 3)
        for (u, v), m, zz in zip(uv, marks, z):
            cv2.circle(shown, (int(u), int(v)), 7, (0, 220, 0), -1)
            cv2.putText(shown, m["name"], (int(u) + 8, int(v) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)
            print(f"  {m['name']:22s} tool point chassis {np.round(tcp[marks.index(m)], 3)} -> image ({u:.0f}, {v:.0f}), {zz * 100:.0f} cm from the lens")

    if a.detect:
        from ultralytics import YOLO  # noqa: E402
        model = YOLO(os.path.expanduser("~/.local/state/moss/models/yoloe-11s-seg.pt"))
        model.set_classes(LITTER_WORDS, model.get_text_pe(LITTER_WORDS))
        t0 = time.time()
        r = model.predict(frame, imgsz=640, conf=0.2, verbose=False)[0]
        det = [(r.names[int(c)], round(float(s), 2)) for c, s in zip(r.boxes.cls, r.boxes.conf)]
        print(f"YOLOE: {len(det)} detections in {(time.time() - t0) * 1000:.0f} ms: {det}")
        shown = r.plot(img=shown, line_width=2)
        # in or out of the zone: the bottom centre of each box (where the object meets the floor) against the polygon
        if zone_poly is not None:
            for (name, conf), box in zip(det, r.boxes.xyxy.tolist()):
                foot = (int((box[0] + box[2]) / 2), int(box[3]))
                inside = cv2.pointPolygonTest(zone_poly, foot, False) >= 0
                label = "IN ZONE" if inside else "OUT OF ZONE"
                cv2.circle(shown, foot, 8, (0, 220, 0) if inside else (0, 0, 255), -1)
                cv2.putText(shown, f"{name} {label}", (foot[0] + 10, foot[1] + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (0, 220, 0) if inside else (0, 0, 255), 2)
                print(f"  {name} {conf}: foot at {foot} -> {label}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = OUT / f"zone_{stamp}.jpg"
    cv2.imwrite(str(out), shown, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
