"""Study 4: does a stronger shoulder let the arm tip the rover?

Static only: the whole robot's centre of mass, plus a payload at the tcp,
against the tracks' footprint on flat ground (x -0.140..+0.145 m,
y ±0.151 m: the belts' lowest points in the R92 model). The tip angle is the
slope, in the worst direction, at which the centre of mass would leave the
footprint. The model's 4.0 kg rover body is an estimate (issue #2: rover
complete about 4.2 kg, so the margins here are on the generous side).
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

import moss_arm as ma

FOOT_X = (-0.140, 0.145)
FOOT_Y = (-0.151, 0.151)


def exit_fraction(c0: np.ndarray, p: np.ndarray) -> float:
    """s in [0, 1] where c0 + s (p - c0) leaves the footprint (1 if p is inside)."""
    s_best = 1.0
    d = p - c0
    for axis, (lo, hi) in ((0, FOOT_X), (1, FOOT_Y)):
        if d[axis] > 1e-12:
            s_best = min(s_best, (hi - c0[axis]) / d[axis])
        elif d[axis] < -1e-12:
            s_best = min(s_best, (lo - c0[axis]) / d[axis])
    return max(0.0, s_best)


def margin(c: np.ndarray) -> float:
    return min(c[0] - FOOT_X[0], FOOT_X[1] - c[0], c[1] - FOOT_Y[0], FOOT_Y[1] - c[1])


def main() -> None:
    arm = ma.load()
    m, d = arm.model, arm.data
    M = float(m.body_subtreemass[0])
    rows = []
    q_stretch = None
    from s1_torque_budget import worst_stretch
    q_stretch = worst_stretch(arm)
    for pan_deg in np.linspace(-110, 110, 23):
        for label, q in (("stretched level", q_stretch), ("far floor pick", None)):
            if q is None:
                from s2_cycle import far_pick_pose
                q = far_pick_pose()
            qq = [math.radians(pan_deg)] + list(q[1:])
            arm.set_q(qq)
            c0 = d.subtree_com[0][:2].copy()
            hz = d.subtree_com[0][2]
            p = d.site("tcp").xpos[:2].copy()
            s = exit_fraction(c0, p)
            m_tip = math.inf if s >= 1.0 else M * s / (1 - s)
            row = {"pan_deg": float(pan_deg), "pose": label, "tcp_xy": p.tolist(), "m_tip_kg": m_tip}
            for kg in (0.0, 0.35, 0.53, 1.0):
                c = (M * c0 + kg * p) / (M + kg)
                h = (M * hz + kg * d.site("tcp").xpos[2]) / (M + kg)
                row[f"tip_deg_{kg}"] = math.degrees(math.atan2(margin(c), h))
            rows.append(row)
    ma.save("s4_tipping", {"robot_kg": M, "footprint": {"x": FOOT_X, "y": FOOT_Y}, "rows": rows})
    print(f"robot {M:.2f} kg; footprint x {FOOT_X}, y {FOOT_Y}")
    for label in ("stretched level", "far floor pick"):
        sub = [r for r in rows if r["pose"] == label]
        worst = min(sub, key=lambda r: r["m_tip_kg"])
        tip = min(sub, key=lambda r: r["tip_deg_0.53"])
        print(f"{label:16s}: least payload that tips it {worst['m_tip_kg']:.2f} kg (pan {worst['pan_deg']:.0f}°); "
              f"with a full 0.5 l bottle the worst slope before tipping is {tip['tip_deg_0.53']:.1f}° (pan {tip['pan_deg']:.0f}°); "
              f"empty {min(r['tip_deg_0.0'] for r in sub):.1f}°")


if __name__ == "__main__":
    main()
