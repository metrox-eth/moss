"""The arm's kinematics without MuJoCo: where the tool point is for a pose, and the
pose that moves it straight up or down.

The chain comes from the robot's CAD model, extracted once by tools/moss_arm_chain.py
into config/arm_chain.json: one link per body from the arm's mount to the tool, each
with its offset from its parent (position, quaternion) and, for the five arm joints,
a hinge axis at the body's origin. The tool point (TCP) is 35 mm along the approach
from the gripper's tool frame, as everywhere else in this package; the jaws' lowest
point is 20 mm below it when the gripper is vertical. Frames and angles are the
model's: the chassis frame (x forward, y left, floor at z = 0) and model radians (the
keep-out table's joint_map turns servo ticks into them).

    from moss_dimos.arm_kin import ArmKin
    kin = ArmKin.load()
    p, R = kin.tcp(q)                 # q = [pan, lift, elbow, wrist_flex, roll] model radians
    q2 = kin.shift(q, (0, 0, -0.02))  # the pose 2 cm lower, same tool orientation, pan and roll untouched
    kin.tilt_deg(R)                   # how far the gripper is from vertical

shift() is a damped least-squares solve on the three pitch joints (lift, elbow,
wrist_flex): their axes are parallel, so a vertical move with the orientation
kept is exactly their job; the pan and the roll never move. None when the move
cannot be reached (the arm is at the end of its range, or the residual stays
over the tolerance). Pure numpy, cold-testable: the FK of every pose of
config/arm_drop_poses.json must land on the tcp_m written there.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CHAIN_PATH = ROOT / "config" / "arm_chain.json"
FORMAT = "moss-arm-chain/1"
JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")
PITCH_JOINTS = (1, 2, 3)            # lift, elbow, wrist_flex: the parallel-axis joints a vertical move uses
TCP_IN_TOOL_M = (0.0, 0.0, -0.035)
JAWS_BELOW_TCP_M = 0.020
POS_TOL_M = 0.001                   # shift(): converged when the tool point is within this ...
ROT_TOL_RAD = math.radians(0.5)     # ... and the orientation within this
IK_ITERS = 60
IK_DAMPING = 0.02
IK_STEP_MAX_RAD = 0.25              # no single iteration turns a joint more than this
FD_EPS = 1e-5


def quat_to_mat(q) -> np.ndarray:
    """MuJoCo's (w, x, y, z) unit quaternion as a rotation matrix."""
    w, x, y, z = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def axis_angle(axis, angle: float) -> np.ndarray:
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    c, s = math.cos(angle), math.sin(angle)
    k = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    return np.eye(3) * c + s * k + (1 - c) * np.outer(a, a)


def rotvec(R: np.ndarray) -> np.ndarray:
    """The rotation vector of a rotation matrix (angle * unit axis)."""
    c = max(-1.0, min(1.0, (np.trace(R) - 1.0) / 2.0))
    angle = math.acos(c)
    if angle < 1e-9:
        return np.zeros(3)
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    s = 2.0 * math.sin(angle)
    if s < 1e-9:   # angle near pi: fall back to the symmetric part
        d = np.diag(R)
        k = int(np.argmax(d))
        v = np.sqrt(np.maximum(0.0, (d + 1.0) / 2.0))
        v = v * np.sign(R[k, :] + 1e-12)
        return angle * v / max(np.linalg.norm(v), 1e-9)
    return angle * v / s


class ArmKin:
    def __init__(self, chain: dict):
        if chain.get("format") != FORMAT:
            raise ValueError(f"not a {FORMAT} file: {chain.get('format')!r}")
        self.chain = chain
        self.links = chain["links"]
        self.joints = [lk["joint"] for lk in self.links if lk.get("joint")]
        if tuple(self.joints) != JOINTS:
            raise ValueError(f"the chain's joints {self.joints} are not {list(JOINTS)}")
        self._pos = [np.asarray(lk["pos"], dtype=float) for lk in self.links]
        self._rot = [quat_to_mat(lk["quat"]) for lk in self.links]
        self._axis = [np.asarray(lk["axis"], dtype=float) if lk.get("joint") else None for lk in self.links]
        self._jidx = {}
        k = 0
        for i, lk in enumerate(self.links):
            if lk.get("joint"):
                self._jidx[i] = k
                k += 1
        self.ranges = {lk["joint"]: tuple(lk["range"]) for lk in self.links if lk.get("joint") and lk.get("range")}
        self.tcp_in_tool = np.asarray(chain.get("tcp_in_tool_m", TCP_IN_TOOL_M), dtype=float)
        self.jaws_below_tcp = float(chain.get("jaws_below_tcp_m", JAWS_BELOW_TCP_M))

    @classmethod
    def load(cls, path=CHAIN_PATH) -> "ArmKin":
        return cls(json.loads(Path(path).read_text()))

    # ── forward ──

    def frames(self, q) -> list[tuple[np.ndarray, np.ndarray]]:
        """(position, rotation) of every link frame, joint angles applied."""
        q = [float(v) for v in q]
        if len(q) != len(JOINTS):
            raise ValueError(f"{len(q)} angles for {len(JOINTS)} joints")
        p, R = np.zeros(3), np.eye(3)
        out = []
        for i in range(len(self.links)):
            p = p + R @ self._pos[i]
            R = R @ self._rot[i]
            if i in self._jidx:
                R = R @ axis_angle(self._axis[i], q[self._jidx[i]])
            out.append((p, R))
        return out

    def tool(self, q) -> tuple[np.ndarray, np.ndarray]:
        """The tool frame (position, rotation) in the model's world frame."""
        return self.frames(q)[-1]

    def tcp(self, q) -> tuple[np.ndarray, np.ndarray]:
        """The tool point and the tool rotation. The approach runs along the
        tool frame's -z: the gripper is vertical, pointing down, when R[:, 2]
        points up."""
        p, R = self.tool(q)
        return p + R @ self.tcp_in_tool, R

    def jaws_z(self, q) -> float:
        """Height of the jaws' lowest point above the floor (z = 0), gripper taken vertical."""
        return float(self.tcp(q)[0][2]) - self.jaws_below_tcp

    @staticmethod
    def tilt_deg(R: np.ndarray) -> float:
        """How far the approach axis is from vertical, degrees (0 = pointing straight down)."""
        return math.degrees(math.acos(max(-1.0, min(1.0, float(R[2, 2])))))

    # ── inverse: a straight move of the tool point, orientation kept ──

    def _error(self, q, p_t: np.ndarray, R_t: np.ndarray) -> np.ndarray:
        p, R = self.tcp(q)
        return np.concatenate([p_t - p, rotvec(R_t @ R.T)])

    def _jacobian(self, q, p_t, R_t, idx) -> np.ndarray:
        e0 = self._error(q, p_t, R_t)
        J = np.zeros((6, len(idx)))
        for c, j in enumerate(idx):
            q2 = list(q)
            q2[j] += FD_EPS
            J[:, c] = (self._error(q2, p_t, R_t) - e0) / FD_EPS
        return -J

    def shift(self, q, dp, joints=PITCH_JOINTS, keep_orientation: bool = True) -> list[float] | None:
        """The pose that moves the tool point by dp (metres, world frame), the
        tool orientation kept, moving only `joints` (by index). None when no
        pose within the joint ranges brings the residual under the tolerances."""
        q = [float(v) for v in q]
        p0, R0 = self.tcp(q)
        p_t = p0 + np.asarray(dp, dtype=float)
        idx = list(joints)
        for _ in range(IK_ITERS):
            e = self._error(q, p_t, R0)
            if not keep_orientation:
                e[3:] = 0.0
            if np.linalg.norm(e[:3]) < POS_TOL_M and np.linalg.norm(e[3:]) < ROT_TOL_RAD:
                return q
            J = self._jacobian(q, p_t, R0, idx)
            if not keep_orientation:
                J[3:, :] = 0.0
            JJt = J @ J.T + (IK_DAMPING ** 2) * np.eye(6)
            dq = J.T @ np.linalg.solve(JJt, e)
            m = float(np.max(np.abs(dq)))
            if m > IK_STEP_MAX_RAD:
                dq = dq * (IK_STEP_MAX_RAD / m)
            for c, j in enumerate(idx):
                q[j] += float(dq[c])
                lo, hi = self.ranges.get(JOINTS[j], (-math.inf, math.inf))
                q[j] = min(hi, max(lo, q[j]))
        e = self._error(q, p_t, R0)
        if np.linalg.norm(e[:3]) < POS_TOL_M and (not keep_orientation or np.linalg.norm(e[3:]) < ROT_TOL_RAD):
            return q
        return None

    def lift(self, q, dz: float) -> list[float] | None:
        """shift() straight up (dz > 0) or down (dz < 0)."""
        return self.shift(q, (0.0, 0.0, float(dz)))
