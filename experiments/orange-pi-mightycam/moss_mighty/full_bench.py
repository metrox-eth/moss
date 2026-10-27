"""MOSS navigation/mission/arm load variant. All range data and actuators are simulated.

The real Mighty/YOLO modules run inside this same graph. Synthetic room data never
enters the live Mighty trajectory and is not presented as a measured workshop map.
"""
import os
import threading
import time
import numpy as np
# Load the real Open3D bindings before dimOS starts recorder/scan threads.
# The ARM wheel registers open3d.core while importing its parent package;
# concurrent lazy imports otherwise see a partially initialized package.
import open3d.core

# This module cannot open a motor or servo port, even if devices are later added.
os.environ.update(MOSS_MOCK_BUS='1', MOSS_CAMERA='0', MOSS_IMU='0',
                  MOSS_WRIST='0', MOSS_SOUNDS='0', MOSS_RERUN='0',
                  MOSS_MISSION_AUTOSTART='0', MOSS_PICK_CMD='none')
from .paths import STATE_DIR
os.environ['MOSS_STATE_DIR'] = str(STATE_DIR)

from dimos.core.core import rpc
from dimos.core.module import Module
from dimos.core.stream import Out
from dimos.core.coordination.blueprints import autoconnect
from dimos.control.coordinator import ControlCoordinator
from dimos.msgs.sensor_msgs.PointCloud2 import PointCloud2
from moss_dimos import blueprints as B, arm as A, arm_feetech as F
from moss_dimos.mission import LitterMission
from moss_dimos.rplidar_c1 import RPLidarC1
from dimos.hardware.manipulators.registry import adapter_registry


class SyntheticRoom(Module):
    pointcloud: Out[PointCloud2]

    @rpc
    def start(self):
        super().start()
        self.done=threading.Event()
        self.worker=threading.Thread(target=self.feed,daemon=True)
        self.worker.start()

    def feed(self):
        n=180
        x=np.linspace(-4,4,n)
        y=np.linspace(-3,3,n)
        world=np.concatenate([np.c_[x,np.full(n,-3),np.zeros(n)],
                              np.c_[x,np.full(n,3),np.zeros(n)],
                              np.c_[np.full(n,-4),y,np.zeros(n)],
                              np.c_[np.full(n,4),y,np.zeros(n)]])
        t0=time.monotonic()
        while not self.done.wait(.1):
            t=time.monotonic()-t0
            # Small deterministic movement exercises ICP and map updates.
            p=world.copy()
            p[:,0]-=.4*np.sin(t*.12)
            p[:,1]-=.3*np.sin(t*.08)
            self.pointcloud.publish(PointCloud2.from_numpy(p.astype(np.float32),frame_id='lidar_link',timestamp=time.time()))

    @rpc
    def stop(self):
        if hasattr(self,'done'):
            self.done.set();self.worker.join(timeout=2)
        super().stop()


class SimServoBus:
    """Feetech register interface in memory; never owns a serial device."""
    def __init__(self):
        self.pos={1:2857.,2:860.,3:3206.,4:868.,5:3221.,6:3674.}
        self.reg={sid:{F.REG_GOAL:int(p),F.REG_TORQUE:0,F.REG_SPEED:400} for sid,p in self.pos.items()}
        self.last=time.monotonic()
    def open(self): return True
    def close(self): pass
    def tick(self):
        now=time.monotonic();dt=now-self.last;self.last=now
        for sid,p in self.pos.items():
            r=self.reg[sid]
            if r[F.REG_TORQUE]:
                self.pos[sid]+=float(np.clip(r[F.REG_GOAL]-p,-dt*(r[F.REG_SPEED] or 400),dt*(r[F.REG_SPEED] or 400)))
    def read2(self,sid,addr):
        self.tick()
        if sid not in self.pos:return None
        return int(round(self.pos[sid])) if addr==F.REG_PRESENT else self.reg[sid].get(addr,0)
    def write1(self,sid,addr,value):
        self.tick();self.reg[sid][addr]=int(value);return True
    write2=write1


class BenchArmAdapter(F.FeetechSo101Adapter):
    def __init__(self,**kwargs):
        kwargs['bus']=SimServoBus()
        kwargs['address']='memory-only'
        super().__init__(**kwargs)


class BenchArmCoordinator(ControlCoordinator):
    """Import this module in the worker too, so its memory-only adapter is registered."""
    pass


try:adapter_registry.register_path('moss_bench_arm','moss_mighty.full_bench:BenchArmAdapter')
except ValueError:pass


def build():
    from .module import blueprint as camera
    from .vision import blueprint as vision
    profile=B.robot_profile.current()
    parts=B._explore_parts(profile,{'base':'memory-only','lidar':'synthetic-only'})
    parts=[p for p in parts if not any(a.module is RPLidarC1 for a in p.blueprints)]
    parts += [SyntheticRoom.blueprint(),LitterMission.blueprint(autostart=False,pick_cmd='none'),camera,vision]
    hw=A.arm_hardware(sim=False,address='memory-only')
    hw.adapter_type='moss_bench_arm'
    parts.append(BenchArmCoordinator.blueprint(hardware=[hw],tasks=[A.arm_trajectory_task()],
                 tick_rate=50.,instance_name='ArmCoordinator').remappings([
                     (BenchArmCoordinator,'coordinator_joint_state','arm_joint_state'),
                     (BenchArmCoordinator,'twist_command','unused_arm_twist')]))
    return B._jpeg_camera(autoconnect(*parts)).remappings([
        (B.MossControlCoordinator,'twist_command','cmd_vel')])


blueprint=build()
