#!/usr/bin/env python3
"""Open MOSS V0.6 R92, or run a local headless drive/turn check.

Linux: python viewer.py
macOS: mjpython viewer.py
Offline check: python viewer.py --headless --seconds 3 --drive .08 .08
"""
import argparse
import json
from pathlib import Path
import time

import mujoco
from runtime import MossSimulation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--seconds',type=float,default=3.)
    parser.add_argument('--drive',nargs=2,type=float,default=[0.,0.],metavar=('LEFT_M_S','RIGHT_M_S'))
    parser.add_argument('--model',type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    sim=MossSimulation(args.model);sim.drive(*args.drive)
    if args.headless:
        result=sim.advance(args.seconds)
    else:
        from mujoco import viewer as mujoco_viewer
        with mujoco_viewer.launch_passive(sim.model,sim.data) as view:
            view.cam.lookat[:]=[.12,0,.15]
            view.cam.distance=1.05;view.cam.azimuth=135;view.cam.elevation=-25
            view.opt.geomgroup[3]=0
            while view.is_running():
                started=time.monotonic();sim.step();view.sync()
                time.sleep(max(0,sim.model.opt.timestep-(time.monotonic()-started)))
        result=sim.observe()
    if args.screenshot:
        from PIL import Image
        camera=mujoco.MjvCamera()
        camera.lookat[:]=[.12,0,.15];camera.distance=1.05;camera.azimuth=135;camera.elevation=-25
        option=mujoco.MjvOption();option.geomgroup[3]=0
        with mujoco.Renderer(sim.model,height=720,width=960) as renderer:
            renderer.update_scene(sim.data,camera=camera,scene_option=option)
            args.screenshot.parent.mkdir(parents=True,exist_ok=True)
            Image.fromarray(renderer.render()).save(args.screenshot)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
