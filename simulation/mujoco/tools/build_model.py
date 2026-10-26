#!/usr/bin/env python3
"""Build the standalone R92 MJCF from the included geometry and joint reference.

No CAD runtime, network, API key or robot connection is needed to rebuild XML.
Physical parameters marked estimated in model/parameters.json are not calibrated.
"""
from pathlib import Path
import copy
import json
import math
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def nums(values):
    return ' '.join(f'{float(x):.12g}' for x in np.asarray(values).ravel())


def build():
    manifest = json.loads((ROOT/'model/manifest.json').read_text())
    kin = json.loads((ROOT/'reference/kinematics.json').read_text())
    parameters = json.loads((ROOT/'model/parameters.json').read_text())
    source = ET.parse(ROOT/'reference/arm_skeleton.xml').getroot()
    root = ET.Element('mujoco', model='MOSS V0.6 R92 — preliminary simulation')
    root.append(ET.Comment('R92 geometry; upstream SO101 joints; uncalibrated dynamics. See README.md.'))
    ET.SubElement(root,'compiler',angle='radian',meshdir='meshes',autolimits='true',inertiafromgeom='false')
    opt = ET.SubElement(root,'option',timestep='.002',integrator='implicitfast',cone='elliptic',iterations='50')
    ET.SubElement(opt,'flag',filterparent='disable')
    root.append(copy.deepcopy(source.find('default')))
    visual = ET.SubElement(root,'visual')
    ET.SubElement(visual,'global',offwidth='1280',offheight='960')
    ET.SubElement(visual,'headlight',ambient='.35 .35 .35',diffuse='.7 .7 .7',specular='.15 .15 .15')
    ET.SubElement(visual,'rgba',haze='.9 .92 .94 1')
    ET.SubElement(root,'statistic',center='.04 0 .17',extent='.8')
    asset = ET.SubElement(root,'asset')
    world = ET.SubElement(root,'worldbody')
    rover = ET.SubElement(world,'body',name='rover')
    for name,kind,axis in [('base_x','slide','1 0 0'),('base_y','slide','0 1 0'),('base_yaw','hinge','0 0 1')]:
        ET.SubElement(rover,'joint',name=name,type=kind,axis=axis,limited='false',damping='0',armature='.001')
    ET.SubElement(rover,'inertial',mass=str(parameters['base_mass_kg']['value']),pos='0 0 .075',
                  diaginertia=nums(parameters['base_inertia_kg_m2']['value']))
    base = copy.deepcopy(source.find("worldbody/body[@name='base']"))
    base.set('pos',nums(np.asarray(kin['arm_base_transform'])[:3,3]))
    # Rotation remains the pinned SO101 mount rotation from the source.
    for parent in list(base.iter()):
        for child in list(parent):
            if child.tag in ['geom','site','camera']:
                parent.remove(child)
    rover.append(base)
    # The old pose inspector inherited SO101 hinge friction on the tiny rack
    # pinion. With its transmission ratio that prevents any closure. Use an
    # explicit, documented preliminary jaw/gear model instead of that inheritance.
    for name in ['nc90_jaw_left_slide','nc90_jaw_right_slide']:
        base.find(f".//joint[@name='{name}']").set('frictionloss','.02')
    pinion=base.find(".//joint[@name='nc90_pinion']")
    pinion.attrib.update(frictionloss=str(parameters['gripper']['pinion_friction_nm']),
        damping=str(parameters['gripper']['pinion_damping_nm_s_rad']),armature='.000001')
    aliases={'static':'rover','base_link':'base','shoulder_link':'shoulder',
             'upper_arm_link':'upper_arm','lower_arm_link':'lower_arm','wrist_link':'wrist',
             'gripper_link':'gripper','nc90_tool':'nc90_tool','nc90_drive':'nc90_drive',
             'nc90_jaw_left':'nc90_jaw_left','nc90_jaw_right':'nc90_jaw_right'}
    bodies={rig:rover if name=='rover' else rover.find(f".//body[@name='{name}']") for rig,name in aliases.items()}
    loaded=set()
    def mesh_asset(name,file):
        if name not in loaded:
            ET.SubElement(asset,'mesh',name=name,file=file.removeprefix('meshes/'),inertia='convex',maxhullvert='128')
            loaded.add(name)
        return name
    for row in manifest['parts']:
        name,rig=row['name'],row['rig']
        mesh_asset(name,row['file'])
        ET.SubElement(bodies[rig],'geom',name='visual_'+name,type='mesh',mesh=name,
                      rgba=nums(row['rgba']),contype='0',conaffinity='0',group='2',mass='0')
        if rig=='nc90_drive':continue  # intentional gear engagement, geometric coupling below
        static=rig in ['static','base_link']
        mask={'contype':'1' if static else '2','conaffinity':'6' if static else '15'}
        files=row['collision_files'] or [row['file']]
        if name.startswith('14_Bin') and not row['collision_files']:
            raise RuntimeError('Bin needs decomposed collision pieces; a solid convex hull would close its opening')
        for i,file in enumerate(files):
            meshname=name if file==row['file'] else mesh_asset(f'collision_{name}_{i}',file)
            ET.SubElement(bodies[rig],'geom',name=f'collision_{name}_{i}',type='mesh',mesh=meshname,
                          rgba='.2 .9 .6 .35',group='3',mass='0',friction='.8 .005 .0001',**mask)

    # Manufacturer CAD is not redistributed. Simple sensor/servo envelopes are
    # placed at saved R92 assembly bounds and explicitly identified as estimates.
    ET.SubElement(rover,'geom',name='lidar_envelope',type='cylinder',pos='.1294 .084 .137',
                  size='.0278 .0143',rgba='.06 .07 .075 1',mass='0',contype='1',conaffinity='6')
    ET.SubElement(rover,'geom',name='front_camera_envelope',type='box',pos='.147 0 .075',
                  size='.013 .062 .0145',rgba='.09 .1 .11 1',mass='0',contype='1',conaffinity='6')
    for y in [-.047,.047]:
        ET.SubElement(rover,'geom',name=f'front_lens_{y}',type='cylinder',pos=nums([.1605,y,.075]),
                      quat=nums([math.sqrt(.5),0,math.sqrt(.5),0]),size='.007 .001',
                      rgba='.12 .2 .25 1',mass='0',contype='0',conaffinity='0')
    ET.SubElement(rover,'geom',name='emergency_stop_envelope',type='cylinder',pos='.057 .068 .131',
                  size='.01175 .006',rgba='.85 .04 .025 1',mass='0',contype='1',conaffinity='6')
    # The CF35-12 visual is a nominal housing, not an imported manufacturer mesh.
    ET.SubElement(bodies['nc90_tool'],'geom',name='gripper_servo_envelope',type='box',
                  pos='-.01 0 -.005',size='.0225 .0125 .0185',rgba='.12 .13 .14 1',
                  mass='0',contype='0',conaffinity='0')
    ET.SubElement(rover,'camera',name='front_camera_ideal',pos='.161 0 .075',xyaxes='0 -1 0 0 0 1',fovy='60')
    ET.SubElement(bodies['nc90_tool'],'camera',name='wrist_camera_ideal',pos='-.064 0 .005',fovy='100')
    ET.SubElement(bodies['nc90_tool'],'site',name='tcp',pos='0 0 -.055',size='.002',rgba='1 .5 0 1',group='4')
    ET.SubElement(bodies['nc90_tool'],'site',name='wrist_camera_lens_reference',pos='-.064 0 .005',size='.001',group='4')
    root.append(copy.deepcopy(source.find('contact')))
    root.append(copy.deepcopy(source.find('equality')))
    actuator=copy.deepcopy(source.find('actuator'))
    actuator.find("position[@name='nc90_close']").attrib.update(
        kp=str(parameters['gripper']['servo_kp_n_per_m']),
        kv=str(parameters['gripper']['servo_kv_n_s_per_m']),
        forcerange=nums([-parameters['gripper']['force_limit_n'],parameters['gripper']['force_limit_n']]))
    for name,joint,kv,ctrl,force in [('base_vx','base_x',60,'.35','20'),('base_vy','base_y',60,'.35','20'),('base_wz','base_yaw',8,'2.6','8')]:
        ET.SubElement(actuator,'velocity',name=name,joint=joint,kv=str(kv),ctrlrange=f'-{ctrl} {ctrl}',forcerange=f'-{force} {force}')
    root.append(actuator)
    sensor=ET.SubElement(root,'sensor')
    for joint in ['base_x','base_y','base_yaw',*kin['cad_joint_values_rad'],'nc90_jaw_left_slide','nc90_jaw_right_slide']:
        ET.SubElement(sensor,'jointpos',name=joint+'_position',joint=joint)
        ET.SubElement(sensor,'jointvel',name=joint+'_velocity',joint=joint)
    armq=list(kin['cad_joint_values_rad'].values())
    keys=ET.SubElement(root,'keyframe')
    ET.SubElement(keys,'key',name='home',qpos=nums([0,0,0]+armq+[0,0,0]),ctrl=nums(armq+[0,0,0,0]))
    ET.indent(root,space='  ')
    ET.ElementTree(root).write(ROOT/'model/moss_robot.xml',encoding='utf-8',xml_declaration=True)
    scene=copy.deepcopy(root);scene.set('model','MOSS V0.6 R92 — manipulation sandbox')
    w=scene.find('worldbody')
    ET.SubElement(w,'geom',name='floor',type='plane',size='3 3 .01',rgba='.87 .89 .91 1',contype='8',conaffinity='6')
    ET.SubElement(w,'light',name='key_light',pos='.5 -.6 1.5',dir='-.3 .4 -1',diffuse='.8 .8 .8')
    ET.SubElement(w,'camera',name='overview',pos='.8 -.9 .65',xyaxes='.747 .664 0 -.319 .359 .877')
    can=ET.SubElement(w,'body',name='litter',pos='.48 0 .0575')
    ET.SubElement(can,'freejoint',name='litter_free')
    ET.SubElement(can,'inertial',pos='0 0 0',mass='.02',diaginertia='.0000275 .0000275 .0000109')
    ET.SubElement(can,'geom',name='can',type='cylinder',size='.033 .0575',rgba='.8 .055 .035 1',
                  contype='4',conaffinity='11',friction='.8 .005 .0001',condim='4')
    scene.find('keyframe/key').set('qpos',nums([0,0,0]+armq+[0,0,0]+[.48,0,.0575,1,0,0,0]))
    ET.indent(scene,space='  ')
    ET.ElementTree(scene).write(ROOT/'model/scene.xml',encoding='utf-8',xml_declaration=True)
    print('Built model/moss_robot.xml and model/scene.xml')


if __name__=='__main__':build()
