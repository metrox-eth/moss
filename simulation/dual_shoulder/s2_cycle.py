"""Study 2: MOSS's own pick-and-drop cycle, run in MuJoCo with the servos'
torque limit, single versus two shoulder servos.

The cycle is config/arm_drop_poses.json as moss_dimos.arm.load_cycle plays it:
the poses as delivered, each move a quintic in joint space, stretched so no
joint passes 400 ticks/s. The object is welded to the hand from the grasp to
the release. Contacts are off: this measures what the servos must give, not
whether the jaws hold. The servos run off the 3S pack, so stall torque is
scaled from 12 V to the pack voltage; the rated (thermal) torque is not.

Heat: copper loss goes with torque squared, so (tau / rated)^2 is the heat as a
multiple of what the servo can shed forever. Above 1 for long, it trips its
over-temperature cut-out (70 °C by default).
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

import moss_arm as ma

TICKS_PER_S = 400.0
QUINTIC_PEAK = 1.875
PACK_V = 10.8           # 3S nominal; MOSS's own docs see 10.5 V under load
DT = 0.002
PAYLOADS = {"nothing": 0.0, "MOSS can 20 g": ma.MOSS_CAN_KG, "glass bottle 250 g": ma.GLASS_BOTTLE_KG,
            "full can 350 g (stress)": 0.35, "full PET 530 g (stress)": 0.53}


def build(payload_kg: float, n_shoulder: int, pack_v: float = PACK_V):
    spec = ma.build_spec(payload_kg if payload_kg > 0 else 1e-6)
    spec.option.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    scale = pack_v / 12.0
    for a in spec.actuators:
        if a.name in ma.ARM:
            a.forcerange = [-ma.STALL_NM * scale, ma.STALL_NM * scale]
    if n_shoulder == 2:
        # two identical servos on one shaft, ideally shared: twice the loop gain,
        # twice the torque, two rotors and two back-EMFs on the joint
        a = spec.actuator("shoulder_lift")
        a.gainprm[0] *= 2
        a.biasprm[1] *= 2
        a.biasprm[2] *= 2
        a.forcerange = [x * 2 for x in a.forcerange]
        j = spec.joint("shoulder_lift")
        j.damping *= 2
        j.armature *= 2
        j.frictionloss *= 2
    m = spec.compile()
    return m, mujoco.MjData(m)


def cycle_steps(pick_pose: str = "pick") -> list[dict]:
    poses = {"drive": ma.drive_pose(), **ma.moss_poses()}
    poses["pick"] = poses[pick_pose]
    steps = []
    for s in ma.moss_sequence():
        a, b = poses[s["from"]], poses[s["to"]]
        d = max(abs(y - x) for x, y in zip(a, b)) / ma.TICK_RAD
        dur = max(s["duration_s"], QUINTIC_PEAK * d / TICKS_PER_S) if d else s["duration_s"]
        steps.append({"phase": s["phase"], "a": a, "b": b, "dur": dur})
    return steps


def quintic(u: float) -> float:
    return 6 * u**5 - 15 * u**4 + 10 * u**3


HOLDS_OBJECT = ("lift", "clear", "transfer")   # from the grasp's end to the release


def run(payload_kg: float, n_shoulder: int, pick_pose: str = "pick", pack_v: float = PACK_V,
        hover_s: float = 0.0) -> dict:
    """One cycle. hover_s adds a wait at the pick pose with the object in hand
    (a re-grasp, a look before lifting): the case the cycle as written never has."""
    m, d = build(payload_kg, n_shoulder, pack_v)
    pid = m.body("payload").id
    qadr = [m.jnt_qposadr[m.joint(j).id] for j in ma.ARM]
    aid = [m.actuator(j).id for j in ma.ARM]
    rng = [tuple(m.jnt_range[m.joint(j).id]) for j in ma.ARM]
    steps = cycle_steps(pick_pose)
    if hover_s:
        i = next(k for k, s in enumerate(steps) if s["phase"] == "grasp")
        steps.insert(i + 1, {"phase": "hover", "a": steps[i]["b"], "b": steps[i]["b"], "dur": hover_s})
    for k, v in zip(qadr, steps[0]["a"]):
        d.qpos[k] = v
    d.ctrl[aid] = steps[0]["a"]
    m.body_mass[pid] = 1e-6
    # settle at the start pose
    for _ in range(int(1.0 / DT)):
        mujoco.mj_step(m, d)
    t_log, tau_log, err_log, phase_log = [], [], [], []
    t = 0.0
    for s in steps:
        carrying = s["phase"] in HOLDS_OBJECT or s["phase"] == "hover"
        m.body_mass[pid] = payload_kg if (carrying and payload_kg > 0) else 1e-6
        n = max(1, int(round(s["dur"] / DT)))
        for i in range(n):
            u = quintic((i + 1) / n)
            target = [x + (y - x) * u for x, y in zip(s["a"], s["b"])]
            d.ctrl[aid] = target
            mujoco.mj_step(m, d)
            t += DT
            if i % 5 == 0:
                t_log.append(t)
                tau_log.append([d.actuator_force[a] for a in aid])
                # the drive pose lies 4.4° past the model's shoulder limit: score against the reachable goal
                err_log.append([d.qpos[k] - min(max(c, lo), hi) for k, c, (lo, hi) in zip(qadr, target, rng)])
                phase_log.append(s["phase"])
    tau = np.array(tau_log)
    err = np.array(err_log)
    stall_v = ma.STALL_NM * pack_v / 12.0
    per = {}
    for k, j in enumerate(ma.ARM):
        nserv = n_shoulder if j == "shoulder_lift" else 1
        per_servo = tau[:, k] / nserv
        heat = (per_servo / ma.RATED_NM) ** 2
        per[j] = {"peak_nm_per_servo": float(np.abs(per_servo).max()),
                  "peak_of_stall": float(np.abs(per_servo).max() / stall_v),
                  "mean_heat": float(heat.mean()),
                  "s_over_rated": float((np.abs(per_servo) > ma.RATED_NM).sum() * 5 * DT),
                  "max_err_deg": float(np.degrees(np.abs(err[:, k]).max())),
                  "end_err_deg": float(np.degrees(abs(err[-1, k])))}
    return {"payload_kg": payload_kg, "n_shoulder": n_shoulder, "pick_pose": pick_pose,
            "pack_v": pack_v, "hover_s": hover_s, "cycle_s": t, "joints": per,
            "trace": {"t": t_log[::4], "phase": phase_log[::4],
                      "shoulder_nm_per_servo": (tau[::4, 1] / n_shoulder).tolist(),
                      "elbow_nm": tau[::4, 2].tolist()}}


def far_pick_pose() -> list[float]:
    """The farthest floor pick in MOSS's reach table."""
    best = max(ma.floor_reach_poses(), key=lambda p: math.hypot(*p["xy_base_m"]))
    return best["rad"]


def main() -> None:
    import moss_arm
    far = far_pick_pose()
    orig = moss_arm.moss_poses
    moss_arm.moss_poses = lambda: {**orig(), "pick_far": far}
    runs = []
    print(f"pack {PACK_V} V → stall {ma.STALL_NM*PACK_V/12:.2f} N·m, rated {ma.RATED_NM:.2f} N·m\n")
    print(f"{'pick':9s} {'object':24s} {'hover':>5s} {'n':>2s} | shoulder: peak/stall mean-heat s>rated maxerr | elbow: peak/stall mean-heat s>rated")
    for pick in ("pick", "pick_low", "pick_far"):
        for name, kg in PAYLOADS.items():
            for hover in (0.0, 20.0):
                if hover and name not in ("MOSS can 20 g", "glass bottle 250 g"):
                    continue
                for n in (1, 2):
                    r = run(kg, n, pick, hover_s=hover)
                    r["object"] = name
                    runs.append(r)
                    s, e = r["joints"]["shoulder_lift"], r["joints"]["elbow_flex"]
                    print(f"{pick:9s} {name:24s} {hover:5.0f} {n:2d} | {s['peak_of_stall']:5.2f} {s['mean_heat']:5.2f} {s['s_over_rated']:5.1f}s {s['max_err_deg']:5.2f}° | "
                          f"{e['peak_of_stall']:5.2f} {e['mean_heat']:5.2f} {e['s_over_rated']:5.1f}s")
    ma.save("s2_cycle", {"pack_v": PACK_V, "runs": runs, "far_pick": far})


if __name__ == "__main__":
    main()
