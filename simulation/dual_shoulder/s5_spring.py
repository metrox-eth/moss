"""Study 5: the passive alternative. A spring that carries the arm's own weight.

A zero-free-length spring between the shoulder bracket and the upper arm gives
a torque A·sin(θ - φ) about the shoulder: the classic gravity balancer. It
cannot know the elbow angle, so it can only cancel the part of the load that
follows the shoulder angle. Fit A and φ so the worst shoulder heat over every
pose MOSS uses (its cycle, its drive pose, all 645 floor picks) is smallest,
then compare the shoulder's holding torque: single servo, single + spring,
two servos (ideally shared).
"""
from __future__ import annotations

import numpy as np

import moss_arm as ma


def main() -> None:
    arm = ma.load()
    named = {"drive": ma.drive_pose(), **ma.moss_poses()}
    from s2_cycle import far_pick_pose
    named["pick_far"] = far_pick_pose()
    qs = list(named.values()) + [p["rad"] for p in ma.floor_reach_poses()]
    th = np.array([q[1] for q in qs])
    tau0 = np.array([arm.hold_torque(q)[1] for q in qs])
    jz = np.array([arm.tcp_z_jac(q)[1] for q in qs])

    best = None
    for A in np.linspace(0, 1.6, 81):
        for phi in np.linspace(-np.pi, np.pi, 181):
            res = tau0 + A * np.sin(th - phi)  # the servo supplies what the spring does not
            score = np.max(np.abs(res))
            if best is None or score < best[0]:
                best = (score, A, phi)
    _, A, phi = best
    spring = A * np.sin(th - phi)
    out = {"A_nm": A, "phi_rad": phi, "poses": {}}
    print(f"best spring: {A:.2f} N·m peak, phase {np.degrees(phi):.0f}° (shoulder angle where it pushes hardest: {np.degrees(phi + np.pi/2):.0f}°)\n")
    print(f"{'pose':10s} {'payload':>8s} | {'single':>7s} {'+spring':>7s} {'dual/servo':>10s} | heat: single  +spring  dual")
    for name in ("drive", "clear", "pick", "pick_low", "pick_far"):
        i = list(named).index(name)
        for kg in (ma.MOSS_CAN_KG, ma.GLASS_BOTTLE_KG):
            t1 = tau0[i] + kg * ma.G * jz[i]
            ts = t1 + spring[i]
            td = t1 / 2
            out["poses"][f"{name}@{kg}"] = {"single": t1, "spring": ts, "dual": td}
            print(f"{name:10s} {kg*1000:6.0f} g | {abs(t1):7.2f} {abs(ts):7.2f} {abs(td):10.2f} | "
                  f"{ma.heat_ratio(t1):6.2f} {ma.heat_ratio(ts):7.2f} {ma.heat_ratio(td):6.2f}")
    floor = slice(len(named), None)
    for label, arr in (("single", tau0[floor]), ("single + spring", tau0[floor] + spring[floor]), ("dual, per servo", tau0[floor] / 2)):
        h = (np.abs(arr) / ma.RATED_NM) ** 2
        print(f"\nall 645 floor picks, empty gripper — {label:16s}: median heat {np.median(h):.2f}, worst {h.max():.2f}, over rated {np.mean(h > 1)*100:.0f} %", end="")
        out[label] = {"median_heat": float(np.median(h)), "max_heat": float(h.max()), "frac_over": float(np.mean(h > 1))}
    print()
    ma.save("s5_spring", out)


if __name__ == "__main__":
    main()
