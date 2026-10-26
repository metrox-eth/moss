"""Small standalone MuJoCo runner. No MOSS hardware imports or cloud services."""
from pathlib import Path
import json
import math

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parent
ARM_JOINTS=('shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll')


class MossSimulation:
    def __init__(self, model_path=None):
        self.model=mujoco.MjModel.from_xml_path(str(model_path or ROOT/'model/scene.xml'))
        self.data=mujoco.MjData(self.model)
        p=json.loads((ROOT/'model/parameters.json').read_text())
        self.track_separation=p['track_center_separation_m']['value']
        self.left_m_s=self.right_m_s=0.
        self.reset()

    def reset(self):
        mujoco.mj_resetDataKeyframe(self.model,self.data,self.model.key('home').id)
        self.left_m_s=self.right_m_s=0.
        mujoco.mj_forward(self.model,self.data)

    def drive(self,left_m_s,right_m_s):
        if not all(math.isfinite(v) and abs(v)<=.30 for v in [left_m_s,right_m_s]):
            raise ValueError('Track speed must be finite and within +/-0.30 m/s')
        self.left_m_s,self.right_m_s=float(left_m_s),float(right_m_s)

    def arm_pose(self,**angles):
        commands=[]
        for name,value in angles.items():
            if name not in ARM_JOINTS or not math.isfinite(value):
                raise ValueError('Unknown arm joint or invalid angle: '+name)
            i=self.model.actuator(name).id
            low,high=self.model.actuator_ctrlrange[i]
            if not low<=value<=high:raise ValueError('Angle outside model limits: '+name)
            commands.append((i,value))
        for i,value in commands:self.data.ctrl[i]=value

    def jaw_gap(self,gap_m):
        if not math.isfinite(gap_m) or not 0<=gap_m<=.09:
            raise ValueError('Jaw gap must be between 0 and 0.09 m')
        self.data.ctrl[self.model.actuator('nc90_close').id]=(.09-gap_m)/2

    def step(self):
        yaw=float(self.data.joint('base_yaw').qpos[0])
        v=(self.left_m_s+self.right_m_s)/2
        w=(self.right_m_s-self.left_m_s)/self.track_separation
        for actuator,value in [('base_vx',v*math.cos(yaw)),('base_vy',v*math.sin(yaw)),('base_wz',w)]:
            self.data.ctrl[self.model.actuator(actuator).id]=value
        mujoco.mj_step(self.model,self.data)
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            raise RuntimeError('Simulation produced non-finite state')

    def advance(self,seconds):
        if not math.isfinite(seconds) or seconds<0:raise ValueError('Invalid duration')
        for _ in range(round(seconds/self.model.opt.timestep)):self.step()
        return self.observe()

    def observe(self):
        return {'sim_seconds':float(self.data.time),
                'base_xy_yaw':[float(self.data.joint(n).qpos[0]) for n in ['base_x','base_y','base_yaw']],
                'arm_rad':{n:float(self.data.joint(n).qpos[0]) for n in ARM_JOINTS},
                'jaw_gap_m':float(.09-self.data.joint('nc90_jaw_left_slide').qpos[0]-self.data.joint('nc90_jaw_right_slide').qpos[0]),
                'contacts':self.data.ncon,
                'base_model':'ideal planar differential-drive approximation',
                'calibrated':False}
