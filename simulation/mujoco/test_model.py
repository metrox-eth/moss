"""Offline model/drive checks. They establish no real-world accuracy."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from runtime import MossSimulation,ARM_JOINTS


def test_every_visual_asset_is_present_and_matches_manifest():
    manifest=json.loads((ROOT/'model/manifest.json').read_text())
    assert manifest['revision']=='V0.6 / R92'
    names={r['name'] for r in manifest['parts']}
    assert {'Hull_R92','Motor_Mount_Left_R90','RealSense_Insert_R72','NC90_Base_extended_rails'}<=names
    for row in manifest['parts']:
        assert hashlib.sha256((ROOT/'model'/row['file']).read_bytes()).hexdigest()==row['sha256']
        for file in row['collision_files']:assert (ROOT/'model'/file).is_file()


def test_robot_import_is_portable_and_independent_of_scene():
    model=mujoco.MjModel.from_xml_path(str(ROOT/'model/moss_robot.xml'))
    assert model.nq==11 and model.nu==9
    assert model.key('home').id>=0
    assert all(model.joint(n).id>=0 for n in ARM_JOINTS)
    assert model.camera('front_camera_ideal').id>=0
    assert model.camera('wrist_camera_ideal').id>=0


def test_r92_bounds_and_arm_placement():
    manifest=json.loads((ROOT/'model/manifest.json').read_text())
    parts={r['name']:r for r in manifest['parts']}
    bounds=np.array(parts['Hull_R92']['world_bounds_m'])
    np.testing.assert_allclose(bounds[1]-bounds[0],[.328,.237,.066],atol=.0002)
    left=np.array(parts['Track_Left']['world_bounds_m']).mean(0)
    right=np.array(parts['Track_Right']['world_bounds_m']).mean(0)
    assert abs((left[1]-right[1])-.270)<.0001
    for row in manifest['parts']:
        if row['name'].startswith('SO101_'):
            assert row['assembly_bounds_error_m']<.0001
            assert row['print_volume_relative_error']<.005


@pytest.fixture(scope='module')
def sim():return MossSimulation()


def test_compiled_mesh_poses_match_r92_assembly_bounds(sim):
    sim.reset()
    manifest=json.loads((ROOT/'model/manifest.json').read_text())
    for row in manifest['parts']:
        geom=sim.model.geom('visual_'+row['name']).id
        mesh=int(sim.model.geom_dataid[geom])
        first=int(sim.model.mesh_vertadr[mesh]);count=int(sim.model.mesh_vertnum[mesh])
        vertices=sim.model.mesh_vert[first:first+count]
        world=vertices@sim.data.geom_xmat[geom].reshape(3,3).T+sim.data.geom_xpos[geom]
        actual=np.array([world.min(0),world.max(0)])
        np.testing.assert_allclose(actual,row['world_bounds_m'],atol=.0002,err_msg=row['name'])


def test_stationary_model_remains_finite(sim):
    sim.reset();initial=sim.data.qpos.copy();sim.advance(2.)
    assert np.isfinite(sim.data.qpos).all()
    assert np.max(np.abs(sim.data.qpos[:3]-initial[:3]))<.005
    assert all(w.number==0 for w in sim.data.warning)


def test_two_track_commands_can_drive_and_turn(sim):
    sim.reset();sim.drive(.08,.08);sim.advance(2.)
    x,y,yaw=sim.observe()['base_xy_yaw']
    assert x>.10 and abs(y)<.01 and abs(yaw)<.05
    sim.reset();sim.drive(-.04,.04);sim.advance(2.)
    x,y,yaw=sim.observe()['base_xy_yaw']
    assert yaw>.35 and abs(x)<.02 and abs(y)<.02


def test_turning_changes_forward_direction(sim):
    sim.reset();sim.data.joint('base_yaw').qpos[0]=np.pi/2
    mujoco.mj_forward(sim.model,sim.data)
    sim.drive(.08,.08);sim.advance(2.)
    x,y,_=sim.observe()['base_xy_yaw']
    assert y>.10 and abs(x)<.02


def test_jaws_are_coupled_and_opening_is_90_mm(sim):
    sim.reset();assert abs(sim.observe()['jaw_gap_m']-.09)<1e-8
    sim.jaw_gap(.06);sim.advance(2.)
    a=float(sim.data.joint('nc90_jaw_left_slide').qpos[0])
    b=float(sim.data.joint('nc90_jaw_right_slide').qpos[0])
    assert abs(a-b)<.001
    assert abs((.09-a-b)-.06)<.006


def test_bin_collision_has_an_open_cavity(sim):
    sim.reset()
    sim.data.joint('litter_free').qpos[:3]=[-.083,0,.170]
    mujoco.mj_forward(sim.model,sim.data)
    touching=[]
    for c in sim.data.contact:
        names=[sim.model.geom(i).name for i in c.geom]
        if 'can' in names and any('Bin_' in n for n in names) and c.dist<-.001:touching.append(names)
    assert not touching,touching


def test_released_object_falls_and_settles_inside_bin(sim):
    sim.reset()
    sim.data.joint('litter_free').qpos[:3]=[-.083,0,.30]
    mujoco.mj_forward(sim.model,sim.data)
    sim.advance(2.)
    position=sim.data.joint('litter_free').qpos[:3]
    assert -.14<position[0]<-.02 and abs(position[1])<.06
    assert .13<position[2]<.20
    assert np.linalg.norm(sim.data.joint('litter_free').qvel[:3])<.03


def test_arm_responds_to_a_small_position_command(sim):
    sim.reset()
    goal=float(sim.data.joint('shoulder_pan').qpos[0])-.12
    sim.arm_pose(shoulder_pan=goal)
    sim.advance(1.)
    assert abs(float(sim.data.joint('shoulder_pan').qpos[0])-goal)<.03


def test_commands_reject_invalid_values_without_partial_update(sim):
    sim.reset();before=sim.data.ctrl.copy()
    with pytest.raises(ValueError):sim.arm_pose(shoulder_pan=.1,elbow_flex=100.)
    np.testing.assert_array_equal(sim.data.ctrl,before)
    with pytest.raises(ValueError):sim.drive(float('nan'),0.)
    with pytest.raises(ValueError):sim.jaw_gap(.1)
