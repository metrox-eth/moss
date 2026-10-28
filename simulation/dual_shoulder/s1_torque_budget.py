"""Study 1: the static torque budget.

Which joint runs out first, and how far does a second shoulder servo move the
line? For every pose MOSS uses (its pick-and-drop poses and all 645 floor-pick
poses of its reach table) and the worst stretched-out pose, the holding torque
per joint against payload, compared with the servo's rated (continuous) and
stall torque. A payload is a point mass at the grasp centre (tcp).
"""
from __future__ import annotations

import numpy as np

import moss_arm as ma

PAYLOADS_KG = [0.0, 0.02, 0.05, 0.1, 0.25, 0.35, 0.5, 0.75, 1.0]
LITTER = {  # grams; MOSS's reference is its 20 g can, its detector also picks glass
    "MOSS reference can (scene.xml)": 20, "empty PET 0.5 l": 25, "empty glass bottle 0.33 l": 250,
    "full can 330 ml (stress)": 350, "full PET 0.5 l (stress)": 530,
}


def max_payload(tau0: float, jz: float, limit: float) -> float:
    """Largest point mass at the tcp before |tau0 + m*g*jz| exceeds limit (inf if it never does)."""
    a = ma.G * jz
    if abs(tau0) > limit:
        return 0.0
    if abs(a) < 1e-9:
        return float("inf")
    # the payload pushes tau towards sign(a); the binding side is +limit if a > 0
    m = (limit - tau0) / a if a > 0 else (-limit - tau0) / a
    return max(m, 0.0)


def budget(arm: ma.Arm, q) -> dict:
    tau0 = arm.hold_torque(q)
    jz = arm.tcp_z_jac(q)
    rows = {}
    for i, j in enumerate(ma.ARM):
        if j in ("shoulder_pan", "wrist_roll"):
            continue  # vertical pan axis and roll carry no gravity load at these poses
        n = 2 if j == "shoulder_lift" else 1
        rows[j] = {
            "tau0": float(tau0[i]), "jz": float(jz[i]),
            "per_kg": float(ma.G * jz[i]),
            "m_rated_single": max_payload(tau0[i], jz[i], ma.RATED_NM),
            "m_stall_single": max_payload(tau0[i], jz[i], ma.STALL_NM),
            "m_rated_dual": max_payload(tau0[i], jz[i], ma.RATED_NM * n),
            "m_stall_dual": max_payload(tau0[i], jz[i], ma.STALL_NM * n),
        }
    return rows


def worst_stretch(arm: ma.Arm) -> list[float]:
    best, bq = 0.0, None
    for lift in np.linspace(-1.74, 1.74, 59):
        for elbow in np.linspace(-1.69, 1.69, 57):
            for wf in np.linspace(-1.65, 1.65, 23):
                q = [1.34, lift, elbow, wf, 0.0]
                t = abs(arm.hold_torque(q)[1])
                if t > best:
                    best, bq = t, q
    return [float(x) for x in bq]


def main() -> None:
    arm = ma.load()
    poses = {"drive": ma.drive_pose(), **ma.moss_poses()}
    poses["stretched (worst case)"] = worst_stretch(arm)

    named = {}
    for k, q in poses.items():
        b = budget(arm, q)
        named[k] = {"q": list(q), "tcp": arm.tcp(q).tolist(), "joints": b,
                    "hold_curve": {j: [abs(b[j]["tau0"] + m * b[j]["per_kg"]) for m in PAYLOADS_KG] for j in b}}

    # the reach table: every floor pick MOSS can make (gripper within 10° of vertical)
    reach = []
    for p in ma.floor_reach_poses():
        q = p["rad"]
        b = budget(arm, q)
        r = float(np.hypot(*p["xy_base_m"]))
        first = min(b, key=lambda j: b[j]["m_rated_single"])
        reach.append({"r": r, "tcp": arm.tcp(q).tolist(),
                      **{f"{j}_tau0": b[j]["tau0"] for j in b},
                      **{f"{j}_per_kg": b[j]["per_kg"] for j in b},
                      "first_rated_single": first,
                      "first_rated_dual": min(b, key=lambda j: b[j]["m_rated_dual"]),
                      "m_rated_single": b[first]["m_rated_single"],
                      "m_rated_dual": min(b[j]["m_rated_dual"] for j in b),
                      "m_stall_single": min(b[j]["m_stall_single"] for j in b),
                      "m_stall_dual": min(b[j]["m_stall_dual"] for j in b)})

    out = {"payloads_kg": PAYLOADS_KG, "litter_g": LITTER,
           "servo": {"stall_nm": ma.STALL_NM, "rated_nm": ma.RATED_NM},
           "arm_mass_kg": ma.MEASURED_ARM_KG, "poses": named, "reach": reach}
    ma.save("s1_torque_budget", out)

    print(f"servo: rated {ma.RATED_NM:.2f} N·m, stall {ma.STALL_NM:.2f} N·m; arm {ma.MEASURED_ARM_KG*1000:.0f} g\n")
    print(f"{'pose':24s} {'lift τ0':>8s} {'elbow τ0':>8s} {'wflex τ0':>8s} | max payload at rated torque, single → dual shoulder")
    for k, v in named.items():
        b = v["joints"]
        lim_s = min(b, key=lambda j: b[j]["m_rated_single"])
        lim_d = min(b, key=lambda j: b[j]["m_rated_dual"])
        print(f"{k:24s} {b['shoulder_lift']['tau0']:8.2f} {b['elbow_flex']['tau0']:8.2f} {b['wrist_flex']['tau0']:8.2f} | "
              f"{b[lim_s]['m_rated_single']*1000:6.0f} g ({lim_s}) → {b[lim_d]['m_rated_dual']*1000:6.0f} g ({lim_d})")
    rs = np.array([x["r"] for x in reach])
    for label, sel in (("all floor picks", rs > 0), ("far picks r>0.30 m", rs > 0.30)):
        sub = [x for x, s in zip(reach, sel) if s]
        fs = {j: sum(x["first_rated_single"] == j for x in sub) for j in ("shoulder_lift", "elbow_flex", "wrist_flex")}
        fd = {j: sum(x["first_rated_dual"] == j for x in sub) for j in ("shoulder_lift", "elbow_flex", "wrist_flex")}
        ms = np.median([x["m_rated_single"] for x in sub]); md = np.median([x["m_rated_dual"] for x in sub])
        print(f"\n{label} (n={len(sub)}): first joint over rated — single {fs}, dual {fd}; "
              f"median payload at rated {ms*1000:.0f} g → {md*1000:.0f} g")


if __name__ == "__main__":
    main()
