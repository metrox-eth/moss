"""Study 6: the cheapest fix. Where the rover puts the object decides the shoulder's load.

The mission drives the rover until the object sits at one pick point
(MOSS_PICK_XY_M; the cycle's pick pose puts the tool at x = 0.345 m in the
model frame, 18 cm past the tracks' front end at 0.17 m). Every floor pose of
config/arm_floor_reach.json straight ahead of the rover (tool within 5 cm of the
pick line), posed in the R92 model with MOSS's 20 g can: the shoulder's and
elbow's heat against how far forward the tool is. Per 2 cm of x, the best pose
(the one a pick point there would use) and the median.
"""
from __future__ import annotations

import numpy as np

import moss_arm as ma

TRACK_FRONT_X = 0.169       # the tracks' front end in the model (the rover's foremost part below the arm)
LINE_Y = -0.010             # the cycle's pick line: pick and pick_low both put the tool at y = -0.01
HALF_WIDTH = 0.05


def main() -> None:
    arm = ma.load()
    kg = ma.MOSS_CAN_KG
    rows = []
    for p in ma.floor_reach_poses():
        q = p["rad"]
        x, y, _ = arm.tcp(q)
        if abs(y - LINE_Y) > HALF_WIDTH:
            continue
        tau = arm.hold_torque(q) + kg * ma.G * arm.tcp_z_jac(q)
        rows.append({"x": float(x), "y": float(y), "shoulder": float(abs(tau[1])), "elbow": float(abs(tau[2])),
                     "heat_shoulder": ma.heat_ratio(tau[1]), "heat_elbow": ma.heat_ratio(tau[2])})
    q_low = ma.moss_poses()["pick_low"]
    x_low = float(arm.tcp(q_low)[0])
    t_low = arm.hold_torque(q_low) + kg * ma.G * arm.tcp_z_jac(q_low)
    bins = []
    for lo in np.arange(0.20, 0.44, 0.02):
        sel = [r for r in rows if lo <= r["x"] < lo + 0.02]
        if not sel:
            continue
        best = min(sel, key=lambda r: r["heat_shoulder"])
        bins.append({"x": round(float(lo + 0.01), 3), "n": len(sel), "ahead_of_tracks_m": round(float(lo + 0.01 - TRACK_FRONT_X), 3),
                     "best_shoulder": best["heat_shoulder"], "best_elbow": best["heat_elbow"],
                     "median_shoulder": float(np.median([r["heat_shoulder"] for r in sel]))})
    ma.save("s6_pick_point", {"track_front_x": TRACK_FRONT_X, "pick_low_x": x_low,
                              "pick_low_heat": {"shoulder": ma.heat_ratio(t_low[1]), "elbow": ma.heat_ratio(t_low[2])},
                              "bins": bins, "poses": rows})
    print(f"pick_low: tool at x {x_low:.3f} m ({x_low - TRACK_FRONT_X:.2f} m past the tracks), shoulder heat {ma.heat_ratio(t_low[1]):.2f}")
    print(f"{'x, m':>6s} {'past tracks':>11s} {'n':>3s} | shoulder best  median | elbow (best pose)")
    for b in bins:
        print(f"{b['x']:6.2f} {b['ahead_of_tracks_m']:11.2f} {b['n']:3d} | {b['best_shoulder']:13.2f} {b['median_shoulder']:7.2f} | {b['best_elbow']:6.2f}")


if __name__ == "__main__":
    main()
