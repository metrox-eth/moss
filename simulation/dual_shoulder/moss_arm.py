"""The MOSS R92 arm as these studies use it: the released MuJoCo model with the
rover pinned to the floor, an optional payload at the grasp centre, and the
STS3215 numbers every study shares.

All torques are at the joint output, in N·m. Servo figures are Feetech's for the
12 V STS3215 (C018, 1:345); the parts list's Waveshare ST3215 is the same servo.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MODEL_XML = HERE.parent / "mujoco" / "model" / "moss_robot.xml"
POSES_JSON = REPO / "config" / "arm_drop_poses.json"
FLOOR_REACH_JSON = REPO / "config" / "arm_floor_reach.json"
OUT = HERE / "out"

ARM = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")
G = 9.81

# STS3215 C018, 12 V, 1:345. Stall and rated torque are the maker's figures
# (30 and 10 kg·cm); stall current 2.7 A. The no-load speed 0.222 s/60° gives w0.
STALL_NM = 30 * 0.0980665          # 2.94
RATED_NM = 10 * 0.0980665          # 0.98: the continuous figure; heat scales with (tau/rated)^2
STALL_A = 2.7
W0_RAD_S = (math.pi / 3) / 0.222    # 4.72
KT_NM_PER_A = STALL_NM / STALL_A    # 1.09 at the output
R_OHM = 12.0 / STALL_A              # 4.4: the winding, from 12 V / stall current
TICK_RAD = 2 * math.pi / 4096
# Position stiffness of the servo's P loop at the output. The model's kp 998 N·m/rad
# is MuJoCo Menagerie's SO101 value (firmware P=32); LeRobot writes P=16 on followers.
# Not measured: the bench note in issue #2 says the real loop is much softer near its
# goal, so s3 sweeps it.
KP_P32 = 998.22
KP_P16 = KP_P32 / 2

# Issue #2: arm and gripper weighed together off the rover, 27 Sept 2026.
MEASURED_ARM_KG = 0.768
# MOSS's own reference litter: the empty soda can in simulation/mujoco/model/scene.xml
# (body "litter": 66 mm x 115 mm, 20 g); the keep-out sweeps the same 66 mm can.
MOSS_CAN_KG = 0.020
# The detector picks its "glass" class by default: an empty 0.33 l glass bottle.
GLASS_BOTTLE_KG = 0.250


@dataclass
class Arm:
    model: mujoco.MjModel
    data: mujoco.MjData
    payload_kg: float

    @property
    def qadr(self) -> list[int]:
        return [self.model.jnt_qposadr[self.model.joint(j).id] for j in ARM]

    @property
    def dadr(self) -> list[int]:
        return [self.model.jnt_dofadr[self.model.joint(j).id] for j in ARM]

    def set_q(self, q) -> None:
        self.data.qpos[:] = 0
        self.data.qvel[:] = 0
        for a, v in zip(self.qadr, q):
            self.data.qpos[a] = v
        mujoco.mj_forward(self.model, self.data)

    def hold_torque(self, q) -> np.ndarray:
        """Joint torques that hold the arm still at q against gravity (incl. payload)."""
        self.set_q(q)
        return self.data.qfrc_bias[self.dadr].copy()

    def tcp_z_jac(self, q) -> np.ndarray:
        """d(tcp z)/dq for the arm joints: a point mass m at the tcp adds m*g*this to the hold torque."""
        self.set_q(q)
        jacp = np.zeros((3, self.model.nv))
        mujoco.mj_jacSite(self.model, self.data, jacp, None, self.model.site("tcp").id)
        return jacp[2, self.dadr].copy()

    def tcp(self, q) -> np.ndarray:
        self.set_q(q)
        return self.data.site("tcp").xpos.copy()

    def shoulder_axis_pos(self) -> np.ndarray:
        return self.data.xanchor[self.model.joint("shoulder_lift").id].copy()


def build_spec(payload_kg: float = 0.0, match_measured_mass: bool = True,
               pin_rover: bool = True) -> mujoco.MjSpec:
    spec = mujoco.MjSpec.from_file(str(MODEL_XML))
    if pin_rover:
        for name in ("base_x", "base_y", "base_yaw"):
            spec.delete(spec.joint(name))
        for name in ("base_vx", "base_vy", "base_wz"):
            spec.delete(spec.actuator(name))
        for s in list(spec.sensors):
            if s.name.startswith("base_"):
                spec.delete(s)
        for k in list(spec.keys):
            spec.delete(k)
    tool = spec.body("nc90_tool")
    tcp = spec.site("tcp")
    if match_measured_mass:
        # The model's arm (base link down) is 753 g against 768 g weighed. Put the
        # missing 15 g at the hand, where it loads the shoulder most (wrist camera, cable).
        extra = MEASURED_ARM_KG - 0.753
        if extra > 0:
            tool.add_body(name="unmodelled_hand_mass", pos=[0, 0, -0.02], mass=extra,
                          inertia=[1e-6, 1e-6, 1e-6])
    if payload_kg > 0:
        tool.add_body(name="payload", pos=list(tcp.pos), mass=payload_kg,
                      inertia=[2e-5 * payload_kg / 0.1] * 3)
    return spec


def load(payload_kg: float = 0.0, **kw) -> Arm:
    model = build_spec(payload_kg, **kw).compile()
    return Arm(model, mujoco.MjData(model), payload_kg)


def moss_poses() -> dict[str, list[float]]:
    d = json.loads(POSES_JSON.read_text())
    return {k: v["rad"] for k, v in d["poses"].items()}


def moss_sequence() -> list[dict]:
    return json.loads(POSES_JSON.read_text())["sequence"]


def floor_reach_poses() -> list[dict]:
    return json.loads(FLOOR_REACH_JSON.read_text())["poses"]


# moss_dimos/arm.py DRIVE_TICKS: the pose the arm rests in while the rover drives
# (folded down over the base). ticks -> rad: (t - 2048) * 2 pi / 4096.
DRIVE_TICKS = (2857, 860, 3206, 868, 3221)


def drive_pose() -> list[float]:
    return [(t - 2048) * TICK_RAD for t in DRIVE_TICKS]


def heat_ratio(tau_nm: float) -> float:
    """Copper heat at a steady holding torque, as a multiple of the heat at the rated torque."""
    return (abs(tau_nm) / RATED_NM) ** 2


def save(name: str, obj) -> Path:
    OUT.mkdir(exist_ok=True)
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1, default=float))
    return p
