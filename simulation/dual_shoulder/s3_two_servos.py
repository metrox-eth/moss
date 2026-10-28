"""Study 3: two STS3215 on one shoulder shaft. Do they share the load, or fight?

Servo A drives the shoulder joint as today. Servo B sits on the other side of the
upper arm, mirrored, and reaches the same joint through its horn and the printed
bracket: a torsion spring k_s, optionally with play b (horn spline, screw holes).
Each servo closes its own position loop on its own output encoder, so what the
two disagree on is not backlash inside the gearbox (the encoder sits after it)
but the offset between their two encoders: delta, in ticks (0.088° each).

Strategies for "software sync":
  same_goal  both servos get the same goal (RoArm-M2 and M3 do this, after zeroing
             the second servo while the first holds the middle pose)
  follower   A holds position; B runs open-loop PWM (STS mode 2) and copies A's
             Present_Load (its PWM duty) over the bus: d_B += alpha*(d_A - d_B)
             at the bus rate, one sample late. B carries no position loop, so an
             encoder offset cannot make it fight.
  single     B absent (today).

A servo here: tau = clip(Kp*e - Kv*w, ±stall at the pack voltage), back-EMF as
joint damping 0.6 N·m·s (the model's value), gear friction 0.052 N·m.

Kp is the one figure same_goal hinges on, and the least known. The main runs use
the model's 998 N·m/rad (Menagerie, P = 32: full torque 2 ticks off the goal).
The bench note in issue #2 (under load, a goal a few ticks away does not move the
arm) says the real loop is much softer near its goal, so the last part sweeps Kp
from 25 to 998 at the pick. A softer loop sags more under the same load, and that
sag, Present_Position minus the goal with one servo, is how to read Kp on the arm.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import mujoco
import numpy as np

import moss_arm as ma
from s2_cycle import PACK_V

DT = 0.0005
KV = 2.731
DELTAS = (-8, -4, -2, 0, 2, 4, 8)
STIFFNESS = (25.0, 50.0, 100.0, 250.0, ma.KP_P16, ma.KP_P32)   # N·m/rad at the output
STALL_V = ma.STALL_NM * PACK_V / 12.0


@dataclass
class Setup:
    strategy: str = "same_goal"     # same_goal | follower | single
    delta_ticks: float = 0.0        # B's encoder reads this much below the shaft (B aims delta above A)
    k_s: float = 200.0              # N·m/rad, B's horn + bracket to the joint
    play_deg: float = 0.0           # free play in B's path, total
    kp: float = ma.KP_P32
    bus_hz: float = 50.0            # follower update rate
    alpha: float = 0.3              # follower gain per update (0.5 limit-cycles at 50 Hz)
    payload_kg: float = 0.0


def build(s: Setup):
    spec = ma.build_spec(s.payload_kg if s.payload_kg > 0 else 1e-6)
    spec.option.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    spec.option.timestep = DT
    spec.delete(spec.actuator("shoulder_lift"))
    for a in spec.actuators:
        if a.name in ma.ARM:
            a.forcerange = [-STALL_V, STALL_V]
    up = spec.body("upper_arm")
    if s.strategy != "single":
        rotor = spec.body("shoulder").add_body(name="servo_b_output", pos=list(up.pos), quat=list(up.quat),
                                               mass=1e-3, inertia=[1e-7] * 3)
        rotor.add_joint(name="servo_b", type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 0, 1],
                        damping=0.60, armature=0.028, frictionloss=0.052)
        spec.add_actuator(name="servo_b", target="servo_b", trntype=mujoco.mjtTrn.mjTRN_JOINT,
                          ctrlrange=[-STALL_V, STALL_V], ctrllimited=True)
    spec.add_actuator(name="servo_a", target="shoulder_lift", trntype=mujoco.mjtTrn.mjTRN_JOINT,
                      ctrlrange=[-STALL_V, STALL_V], ctrllimited=True)
    m = spec.compile()
    return m, mujoco.MjData(m)


def deadzone(x: float, half: float) -> float:
    return 0.0 if abs(x) <= half else x - math.copysign(half, x)


def simulate(s: Setup, q_from, q_to=None, move_s: float = 0.0, hold_s: float = 2.0) -> dict:
    m, d = build(s)
    ja = m.joint("shoulder_lift")
    qa, va = m.jnt_qposadr[ja.id], m.jnt_dofadr[ja.id]
    two = s.strategy != "single"
    if two:
        jb = m.joint("servo_b")
        qb, vb = m.jnt_qposadr[jb.id], m.jnt_dofadr[jb.id]
    act_a = m.actuator("servo_a").id
    act_b = m.actuator("servo_b").id if two else None
    others = [(m.actuator(j).id, i) for i, j in enumerate(ma.ARM) if j != "shoulder_lift"]
    qadr = [m.jnt_qposadr[m.joint(j).id] for j in ma.ARM]
    for k, v in zip(qadr, q_from):
        d.qpos[k] = v
    if two:
        d.qpos[qb] = q_from[1]
    for a, i in others:
        d.ctrl[a] = q_from[i]
    mujoco.mj_forward(m, d)
    # let the arm settle onto the goal with gravity before B is "enabled"
    delta = s.delta_ticks * ma.TICK_RAD
    play = math.radians(s.play_deg) / 2
    c_s = 2 * 0.1 * math.sqrt(s.k_s * 0.03)
    d_b, next_bus, last_da = 0.0, 0.0, 0.0
    q_to = q_to or q_from
    total = move_s + hold_s
    n = int(total / DT)
    log = {"t": [], "tau_a": [], "tau_b": [], "err_deg": []}
    for i in range(n):
        t = i * DT
        u = min(1.0, t / move_s) if move_s else 1.0
        u = 6 * u**5 - 15 * u**4 + 10 * u**3
        goal = [x + (y - x) * u for x, y in zip(q_from, q_to)]
        for a, j in others:
            d.ctrl[a] = goal[j]
        g = goal[1]
        q, w = d.qpos[qa], d.qvel[va]
        tau_a = float(np.clip(s.kp * (g - q) - KV * w, -STALL_V, STALL_V))
        d.ctrl[act_a] = tau_a
        tau_b = 0.0
        d.qfrc_applied[:] = 0
        if two:
            r, wr = d.qpos[qb], d.qvel[vb]
            if s.strategy == "same_goal":
                tau_b = float(np.clip(s.kp * (g - (r - delta)) - KV * wr, -STALL_V, STALL_V))
            else:  # follower: copy A's duty at the bus rate, one sample late
                if t >= next_bus:
                    d_b += s.alpha * (last_da - d_b)
                    last_da = tau_a / STALL_V
                    next_bus += 1.0 / s.bus_hz
                tau_b = float(np.clip(d_b, -1, 1)) * STALL_V
            d.ctrl[act_b] = tau_b
            tc = s.k_s * deadzone(r - q, play) + c_s * (wr - w)
            d.qfrc_applied[va] += tc
            d.qfrc_applied[vb] -= tc
        mujoco.mj_step(m, d)
        if i % 20 == 0:
            log["t"].append(t)
            log["tau_a"].append(tau_a)
            log["tau_b"].append(tau_b)
            log["err_deg"].append(math.degrees(d.qpos[qa] - g))
    tail = slice(-int(0.7 / (DT * 20)), None)
    ta = float(np.mean(log["tau_a"][tail]))
    tb = float(np.mean(log["tau_b"][tail]))
    load = ta + tb
    fight = min(abs(ta), abs(tb)) if ta * tb < 0 else 0.0
    ripple = float(np.std(log["tau_b"][tail])) if two else 0.0
    return {"setup": s.__dict__.copy(), "tau_a": ta, "tau_b": tb, "load": load,
            "share_b": (tb / load) if abs(load) > 1e-6 else float("nan"),
            "fight_nm": fight, "heat_a": ma.heat_ratio(ta), "heat_b": ma.heat_ratio(tb),
            "heat_max": max(ma.heat_ratio(ta), ma.heat_ratio(tb)),
            "copper_w": (ta**2 + tb**2) / ma.KT_NM_PER_A**2 * ma.R_OHM,
            "err_deg": float(np.mean(log["err_deg"][tail])),
            "max_err_deg": float(np.max(np.abs(log["err_deg"]))),
            "ripple_b": ripple, "trace": {k: v[::5] for k, v in log.items()}}


def main() -> None:
    poses = {"drive": ma.drive_pose(), **ma.moss_poses()}
    from s2_cycle import far_pick_pose
    cases = {"pick_low + MOSS can": (poses["pick_low"], ma.MOSS_CAN_KG),
             "far pick + glass bottle": (far_pick_pose(), ma.GLASS_BOTTLE_KG),
             "clear (light load)": (poses["clear"], 0.0)}
    out = {"stall_v": STALL_V, "rows": [], "follower": [], "moves": [], "stiffness": []}

    print("— the load each servo carries, holding still (mean of the last second) —")
    print(f"{'case':22s} {'strategy':9s} {'δ':>4s} {'k_s':>5s} {'play':>5s} {'P':>3s} | {'τA':>6s} {'τB':>6s} {'fight':>6s} {'heatmax':>7s} {'Cu W':>5s} {'err°':>6s}")
    for case, (q, kg) in cases.items():
        base = simulate(Setup(strategy="single", payload_kg=kg), q)
        base["case"] = case
        out["rows"].append(base)
        print(f"{case:22s} {'single':9s} {'':>4s} {'':>5s} {'':>5s} {32:3d} | {base['tau_a']:6.2f} {'':>6s} {'':>6s} {base['heat_max']:7.2f} {base['copper_w']:5.2f} {base['err_deg']:6.2f}")
        for kp, pname in ((ma.KP_P32, 32), (ma.KP_P16, 16)):
            for k_s in (50.0, 200.0, 1000.0):
                for play in (0.0, 0.3):
                    for delta in (-8, -4, -2, 0, 2, 4, 8):
                        r = simulate(Setup("same_goal", delta, k_s, play, kp, payload_kg=kg), q)
                        r["case"] = case
                        out["rows"].append(r)
                        if pname == 32 and play == 0.0 or (k_s == 200.0 and delta in (-4, 0, 4)):
                            print(f"{case:22s} {'same_goal':9s} {delta:4d} {k_s:5.0f} {play:5.1f} {pname:3d} | {r['tau_a']:6.2f} {r['tau_b']:6.2f} {r['fight_nm']:6.2f} {r['heat_max']:7.2f} {r['copper_w']:5.2f} {r['err_deg']:6.2f}")
            for k_s in (50.0, 200.0, 1000.0):
                r = simulate(Setup("follower", 0, k_s, 0.3, kp, payload_kg=kg), q)
                r["case"] = case
                out["rows"].append(r)
                print(f"{case:22s} {'follower':9s} {'any':>4s} {k_s:5.0f} {0.3:5.1f} {pname:3d} | {r['tau_a']:6.2f} {r['tau_b']:6.2f} {r['fight_nm']:6.2f} {r['heat_max']:7.2f} {r['copper_w']:5.2f} {r['err_deg']:6.2f}")

    print("\n— follower: does copying A's duty converge? (far pick + glass bottle, k_s 200, play 0.3°) —")
    q, kg = cases["far pick + glass bottle"]
    for hz in (100.0, 50.0, 20.0):
        for alpha in (0.1, 0.2, 0.3, 0.4, 0.5, 0.8):
            r = simulate(Setup("follower", 0, 200.0, 0.3, ma.KP_P32, hz, alpha, kg), q)
            out["follower"].append(r)
            print(f"bus {hz:5.0f} Hz α {alpha:3.1f} | share_B {r['share_b']:5.2f} ripple_B {r['ripple_b']:5.3f} N·m  heatmax {r['heat_max']:5.2f}")

    print("\n— a lift: pick_low → lift with MOSS's can, 2.6 s —")
    kg = ma.MOSS_CAN_KG
    for s in (Setup("single", payload_kg=kg), Setup("same_goal", 0, 200.0, 0.3, payload_kg=kg),
              Setup("same_goal", 4, 200.0, 0.3, payload_kg=kg), Setup("follower", 0, 200.0, 0.3, payload_kg=kg)):
        r = simulate(s, poses["pick_low"], poses["lift"], move_s=2.6, hold_s=1.5)
        out["moves"].append(r)
        print(f"{s.strategy:9s} δ {s.delta_ticks:3.0f} | max err {r['max_err_deg']:5.2f}°  end τA {r['tau_a']:5.2f} τB {r['tau_b']:5.2f}")

    print("\n— how stiff the servo holds its goal: same goal at the pick, MOSS's can, no play —")
    print("sag = one servo's Present_Position below its goal; then the hotter servo's heat per offset δ, ticks")
    print(f"{'Kp':>5s} {'k_s':>5s} | {'sag°':>5s} {'ticks':>5s} | " + " ".join(f"{dl:+5d}" for dl in DELTAS))
    q, kg = cases["pick_low + MOSS can"]
    for kp in STIFFNESS:
        single = simulate(Setup("single", kp=kp, payload_kg=kg), q, hold_s=3.0)
        for k_s in (50.0, 200.0, 1000.0):
            rs = [simulate(Setup("same_goal", dl, k_s, 0.0, kp, payload_kg=kg), q, hold_s=3.0) for dl in DELTAS]
            out["stiffness"].append({"kp": kp, "k_s": k_s, "sag_deg": abs(single["err_deg"]), "single_heat": single["heat_max"],
                                     "same_goal": [{"delta_ticks": dl, "heat_max": r["heat_max"], "share_b": r["share_b"], "fight_nm": r["fight_nm"]}
                                                   for dl, r in zip(DELTAS, rs)]})
            print(f"{kp:5.0f} {k_s:5.0f} | {abs(single['err_deg']):5.2f} {abs(single['err_deg']) / math.degrees(ma.TICK_RAD):5.1f} | "
                  + " ".join(f"{r['heat_max']:5.2f}" for r in rs))
    ma.save("s3_two_servos", out)


if __name__ == "__main__":
    main()
