# The arm

MOSS carries an SO-101 arm: five joints and a gripper, six Feetech servos
on one bus (protocol 0, 1 Mbps, the port in `MOSS_ARM_PORT`).

| Joint | Servo ID | What it does |
|---|---|---|
| `shoulder_pan` | 1 | the base: turns the whole arm about the vertical |
| `shoulder_lift` | 2 | the shoulder: tips the upper arm |
| `elbow_flex` | 3 | the elbow |
| `wrist_flex` | 4 | the wrist, up and down |
| `wrist_roll` | 5 | the wrist, turning the gripper about its axis |
| `gripper` | 6 | a CF35-12 force-controlled gripper, with its own register map |

## Calibration

`tools/moss_arm_calibrate.py --sweep`, with the torque off: move every joint
by hand from one end stop to the other, then stop the tool. For each joint
the middle of its travel becomes 2048 (the servo's homing offset, register
31) and the end stops become its position limits (registers 9 and 11). The
gripper gets its limits only. `--show` prints what the servos hold.

The servos' EEPROM holds the calibration; `config/arm_calibration.json`
mirrors it, one entry per joint:

```json
"shoulder_lift": {"id": 2, "homing_offset": -1369, "range_min": 860, "range_max": 3236, "travel_ticks": 2376}
```

A servo reports `raw - homing_offset`: every position in this document and
in the code is that reported value, in ticks (4096 per turn, 0.088 degrees
each). The file describes one arm, so it lives in that robot's checkout.

### A joint with two servos

The shoulder can carry a second servo back to back with the first, on the
same axis (the dual-servo bracket). The second one counts the other way,
so the two are set to read mirror positions about the middle: at every
pose `twin + joint = sum_ticks` (4094: 2047 + p and 2047 - p, the way the
RoArm-M3 firmware runs its two shoulder servos). The calibration file
declares it:

```json
"shoulder_lift_twin": {"id": 7, "of": "shoulder_lift", "sum_ticks": 4094, "homing_offset": -230, "range_min": 839, "range_max": 3234}
```

`tools/moss_arm_twin_setup.py` sets it up: `rename OLD NEW` gives a servo
its bus id; `zero`, with the arm resting at the joint's rear stop and the
torque off, writes both homing offsets so the stop reads the joint's
`range_min` on one and `sum_ticks - range_min` on the other, mirrors the
position limits, copies P/D/I, dead band and torque limit from the joint to
the twin, and records it all in the calibration file; `rest` holds torque
on for a while with nothing moving and prints both loads. Each servo signs
its load in its own direction of count and the twin counts the other way,
so the same physical torque reads with opposite signs on the two: that is
the share. The same sign on both is the two pushing against each other
through the bracket. `tools/moss_bus_scan.py` lists what answers on
the bus, `tools/moss_servo_log.py` logs positions while the arm is moved by
hand (which way each servo counts, where the stops are).

The adapter then drives the twin by itself: the joint's goal mirrored, in
the same sync-write packet as every goal, the same speed and acceleration
per move, torque on and off together, its goal latched to its own reading
before torque goes on. It refuses to connect, or to enable torque, when the
twin reads more than 25 ticks off its mirror (a stale zero would make the
two push against each other through the bracket), and reports an error
when they drift more than 40 ticks apart under torque. The preflight and
every move report the twin's load next to the shoulder's.

## Named poses

The same file keeps named poses under `"poses"`, each a tick per servo and a
note. They are recorded by reading the six servos with the arm placed by
hand (torque off), and replayed by commanding the same ticks.

| Name | Pose |
|---|---|
| `drive` | driving: the arm folded, a few millimetres past the nose, the wrist camera looking up. The pose for driving, and the one to return to whenever a collision is possible. |
| `look` | observation: from `drive`, the shoulder a little higher and the wrist tilted, so the wrist camera, higher than the RealSense, looks ahead for litter. |

## Keep-out zones

The arm can hit its own robot: the lidar and its quick-release mount, the
bin behind the arm, the upper cover, the hull, the arm mounting plate, the
front camera's window, the E-stop, the tracks and their frames, and
the arm's own base. The keep-out table says, for every pose of the five
joints on a grid, whether the arm comes closer than the margin to one of
them, and to which. `moss_dimos/arm_guard.py` reads it and refuses the
poses it forbids.

### The model to sweep

The table comes from the CAD scene of the whole robot, `MOSS_R31.xml` with
its `meshes/` folder and its `parts_manifest.json`: the exterior and the
articulated arm of the current assembly, every part with its own collision
geometry. The CAD gives each part one convex hull, or, for a concave part
(the bin, the cover, the arm mounting plate, the lidar carriage, the arm's
links), the convex pieces of a decomposition, named `<part>_000`,
`<part>_001` and so on. Its visual meshes do not collide.

```sh
pip install mujoco numpy scipy
python tools/moss_arm_keepout.py --model MOSS_R31.xml --names parts_manifest.json \
    --calibration config/arm_calibration.json
```

This writes `config/arm_keepout.json`. The default grid takes about two
minutes on 16 processes (the JSON records the run time and the cost per
pose); the can in the gripper (below) adds about 70 s in one process. The table records the model by its file name and its sha256 (and
the manifest's), never by its path. `--calibration` is the arm's own
calibration file (above): the grid then covers every pose the arm can
reach (below).

The simulation model of the earlier rover (a body `rover`, primitives for
the hull, the bin and the tracks) still sweeps the same way; the tool tells
the two apart by their body names (`--layout auto`):

| | CAD scene (`cad`) | simulation model (`sim`) |
|---|---|---|
| found by | a body `rover_exterior` | anything else |
| `--rover-body` | `rover_exterior,base` | `rover` |
| `--arm-root` | `shoulder` | `shoulder_link` |
| `--rover-parts` (count as they are) | `*`: every collision geom | `hull,bin_*,track_*,tread_*,lidar`, other meshes through stand-ins |
| `--visual` | `skip`: the visual meshes are left out, except on a body with no collision geom | `count`: a visual mesh is a part too |
| `--root-voxel` | `0`: the shoulder's geoms as they are | `0.001`: surface stand-ins |
| lidar | none added: the scene has it | a cylinder added at the profile's pose |
| `--margin` | `0.002` | `0.01` |
| `--payload` | `can`: a soda can in the gripper | `none` |

A flag given on the command line wins over the layout.

### What counts

* **The rover** is every collision geom of the bodies `--rover-body` lists
  and of the bodies under them, except the arm. In the CAD scene the arm's
  own base (`base`) hangs from the world, not from the rover, so it is
  listed: the forearm and the gripper can hit the SO-101 base and the
  plate under it. In the simulation model the bodies between the rover and
  the arm (`base_link`) are the arm's mount and are left out.
* **Parts.** The pieces of one CAD part count as one part: `col_part_0996_017`
  is a piece of `col_part_0996`. `--names parts_manifest.json` gives every
  part its CAD name (`col_part_0996` shows as "Lidar dovetail carriage
  R21"); a name the CAD exporter made up takes the name of the component
  that holds it (the lidar's body shows as "RPLIDAR C1 - R21 position -
  manufacturer model"), and a name several parts share gets the part id in
  brackets. The CAD names the gripper's parts after its working code (their
  first word, two capitals and two digits): the table says "gripper"
  instead ("gripper base - original profile rails extended 22mm each
  end"). The counts, the summary and `why()` use those names. Without
  `--names` the part is named by its geom name.
* **Every rover geom is accounted for.** Each collision geom of the rover
  bodies counts as it is, goes through stand-ins (the simulation model),
  is held inside another (below) or is left out by name (`--exclude`); the
  JSON gives the four numbers (`rover_geoms_counted`,
  `rover_stand_in_meshes`, `rover_inside`, `rover_left_out`), and the bench
  counts the model's collision geoms on its own and checks the sum. In the
  CAD scene: 613 = 440 counted + 173 held inside another.
* **Hulls.** MuJoCo collides a mesh as its convex hull. The scene caps
  every hull at 128 vertices, which cuts corners off the part (up to 5 mm
  on the SO-101 base); the tool lifts the cap, so every hull holds its
  whole piece.
* **Pieces held inside another.** A rover piece held whole inside another
  one that counts as it is (the wheels inside a track's envelope, the
  hardware inside the hull's envelope) adds no forbidden pose: an arm geom
  near it is nearer the other. The tool leaves those out and lists them
  (`rover_inside`); `--keep-inside` keeps them, with the same verdicts.
* **The arm** is every collision geom from `--arm-root` down. The fingers
  take every position: each jaw piece is replaced by its swept volume, the
  convex hull of the piece at both ends of its slide, so a closed, open or
  half-open gripper is inside it. The base pose of the sweep holds the
  gripper open, both jaw slides at 0 (90 mm, the widest) and the pinion at
  0: the tool picks the end of each finger joint that spreads the gripper
  the most, and sets the right jaw and the pinion from the left jaw through
  the scene's joint equalities (MuJoCo applies those only when it steps).
  The JSON says so under `fingers`. `--fix name=value` holds a finger joint
  at one value instead.
* **The gripper's drive** (its gear, the servo horn and their four screws)
  has no collision geom in the scene: it turns with the pinion, inside the
  gripper. Its two visual meshes stick out of the gripper's collision
  hulls, so they count as arm geoms, swept over the pinion's whole range
  like the jaws (`visual_kept`). The rule is general: with `--visual skip`,
  a body with no collision geom keeps its visual meshes, since nothing else
  stands for them.
* **The model's exclusions.** The scene excludes the base and the shoulder
  (one turns on the other): that exclusion is kept. Its other exclusions,
  between links of the arm, mean nothing here: the arm is never collided
  with itself.
* **The shoulder** (the root link, which only the pan moves) is placed every
  degree of pan; a contact there forbids every pan value of the grid within
  half a step, whatever the other joints do. It counts where it meets the
  rover (`--root-margin` 0): it turns in place at a clearance the build
  sets. In the CAD scene it clears every part at every pan by 8 mm or more.

### The payload

The robot's rule is that a pose the table allows must stay clear with a
soda can in the gripper, so the CAD layout sweeps one (`--payload can`, the
default there; `--payload none` leaves it out, `cyl:<diameter mm>x<height
mm>` gives another cylinder): 66 mm across and 120 mm tall, added to the
gripper's body as an arm geom that meets the rover parts only, like the
arm. The tool reads the two finger pads from the jaws' collision geoms
(the parts of each jaw past the gripper's own body) and closes the jaws
until the pads' inner faces are the can's diameter apart: 12 mm of slide
each, the two TPU pads 66 mm apart. The can is centred between the pads
and across them; along the approach (where the fingers point) its centre
starts at the pads' middle and moves out until it clears the gripper's
own geoms, since a can cannot go into the palm. It is held two ways:
upright, its axis along the approach (a can standing on the floor, picked
from above: centred 67.5 mm out, past the rails), and across, its axis
across both the slide and the approach (a can lying down, picked from the
side: 44.9 mm out, against the wrist camera's lens). The table is the
union of three sweeps: the empty gripper over every jaw position, as
above, and the can held each way, swept alone (the arm at the holding gap
lies inside the jaws' swept volumes). In the CAD scene the can adds 6296
forbidden poses to the empty gripper's 147653 (4447 upright, 4407 across,
some in both); `drive` and `look` stay allowed, the can more than 100 mm
from every rover part in both. The JSON records it under `payload` (its
size, the finger values that hold it, the pads, its pose in the gripper's
frame each way, what pushed it out, the forbidden poses of each sweep);
`occupancy_empty_bits_hex` keeps the empty gripper's own, so
`--reuse-empty <table>` takes them from an earlier table of the same model
(both hashes), grid and settings and sweeps only the can. The guard's rule
asks every grid point around a pose, so the can also refuses poses it
clears where a neighbouring grid point folds the wrist further (one step of
the wrist flex is 19 degrees); a finer `--steps` on the wrist narrows that.
The limits: one can and nothing bigger or of another shape, held centred
(never off to one side or by its end), rigid (never squeezed out of shape).

### How the sweep works

* **The grid** spans each joint's model range widened by 10 degrees on both
  sides (`--pad-deg`): the arm's calibrated travel ends a few degrees past
  the model's limits (the `drive` pose sits on the lift and elbow end
  stops, 4 to 5 degrees past the model's, and its wrist 9 degrees past).
  With `--calibration` the grid also reaches 3 degrees past each end of
  every joint's calibrated travel, read through the `joint_map` (the JSON
  keeps it under `travel`). The guard refuses a pose outside the table, so
  a pose the arm can reach must lie inside it: on this arm the wrist
  flex's travel ends at -105.3 degrees, past the pad's -105.0, and its
  grid starts at -108.3; the pan's grid runs to 121.3 degrees either way,
  the roll's from -168.0. The default grid is
  16 x 16 x 16 x 12 x 8 points (pan, lift, elbow, flex, roll): one step is
  14 to 19 degrees on the first four joints, 49 on the roll.
* **Each grid point** is placed on the model (`mj_kinematics`), then
  `mj_collision` lists every contact closer than the margin between an arm
  geom and a rover part. One contact makes the point forbidden. Nothing is
  simulated. The margin is MuJoCo's geom margin, set on the rover parts
  only. The collider is libccd's: MuJoCo's own one misses a geom held whole
  inside a mesh's hull. libccd says reliably whether two geoms come within
  the margin; the distance it reports with a contact is approximate, and
  the table uses only the first. A pose deep in the rover makes 10000
  contacts and more: the arena is raised for them. A pose where MuJoCo's
  collision code fails anyway is forbidden and counted (`collision_errors`).
* **Before writing**, 64 grid points are done again with a full
  `mj_forward` and must agree (the empty gripper's own poses, then the
  table with the can held each way), and 64 free grid points are done
  again with the real jaws closed, half open, open and at a random
  opening: none may touch.

### The margin

In the CAD scene the margin is 2 mm. The collision hulls are the parts
themselves, and the arm folded in `drive` rests close to the bin's front
wall: in the model, at the first alignment (below), the upper arm is 4 to
5 mm from the wall in `drive`, and its cable boss 3 to 4 mm in `look`.
With a 10 mm margin the table forbids both poses, at every one of the 32
grid points around each. With 2 mm every one of those grid points is free
(the closest clears 2 mm), and the guard allows both poses. The near
contact stays in the table: the bin is the part the arm hits most. The
bench holds the margin at 2 mm, and checks that it forbids cells a 0 mm
margin leaves free (the arm within 2 mm of the rover without touching it).

### The JSON

It holds the joint order, each joint's grid (radians), the model's ranges,
the occupancy (one bit per pose, 1 = forbidden, row-major with the last
joint fastest, packed 8 to a byte and written in hex), `cell_part` (one
number per pose: 0 = free, k = the k-th name of `part_names`, the part with
the most contacts there; one byte per pose while `part_names` holds 255
parts or fewer, two beyond: `cell_part_dtype`), the parts hit (only those:
`part_names` is built from the sweep), the poses per part, the 100 most
frequent pairs of arm part and rover part by name (`pair_counts`) and all
of them by number (`pair_cells`), the payload and the empty gripper's own
occupancy (`payload`, `occupancy_empty_bits_hex`), the pieces held inside
another, the count of every rover geom, the visual meshes kept, the
fingers, the calibrated travel the grid covers (`travel`), the layout and
its settings, the model's file name with two hashes (the file, and the
compiled geometry with every mesh), the manifest's file name and hash, the
margin, the run time and the `joint_map` with its basis (below). It is
about 1.1 MB at the default grid.

### The knobs

| Option | Default | What it changes |
|---|---|---|
| `--model` | (required) | the MJCF to sweep |
| `--names` | none | a parts manifest: the parts' CAD names |
| `--out` | `config/arm_keepout.json` | where the table goes |
| `--layout` | `auto` | `cad` or `sim`: the defaults in the table above |
| `--steps` | `16,16,16,12,8` | grid points per joint: more is finer and slower (the time grows with the product) |
| `--margin` | by layout | metres: an arm geom closer than this to a rover part counts as a contact |
| `--pad-deg` | `10` | degrees added past each end of every joint's model range |
| `--calibration` | none | the arm's calibration file: the grid covers each joint's calibrated travel plus 3 degrees |
| `--rover-body`, `--arm-root`, `--rover-parts`, `--visual` | by layout | the rover's bodies, the arm's first moving body, the geoms that count as they are, the visual meshes |
| `--exclude` | none | geom names (patterns) that are not rover parts |
| `--keep-inside` | off | keep the rover pieces held whole inside another |
| `--stand-in-voxel` | `0.004` | metres: the box grid of the stand-ins of a rover mesh that `--rover-parts` does not name (0 leaves those meshes out) |
| `--cover-tol` | `0.002` | metres: mesh surface this close to a named part needs no stand-in |
| `--root-voxel` | by layout | metres: the box grid of the shoulder's stand-ins (0: its geoms as they are) |
| `--root-margin` | `0` | metres: the shoulder's contacts count closer than this (at most `--margin`) |
| `--root-step-deg` | `1` | degrees between the shoulder's samples along the pan |
| `--lidar-xyz` / `--no-lidar` | by layout | add a lidar cylinder at this centre, or none |
| `--joints` | the five joints | for a model with other names |
| `--fix` | the fingers swept | `name=value,...` holds a finger joint at one value |
| `--payload` | by layout | what the gripper holds, swept upright and across: `none`, `can` or `cyl:<diameter mm>x<height mm>` |
| `--reuse-empty` | none | an earlier table of the same model, grid and settings: its empty-gripper poses are taken as they are, only the payload is swept |
| `--check` | `64` | grid points done again with `mj_forward`, and free ones with the real fingers |
| `--jobs` | one per core, up to 16 | processes for the sweep |

### What the guard refuses

```python
from moss_dimos.arm_guard import ArmGuard
guard = ArmGuard.load()                       # the table + config/arm_calibration.json
guard.allowed_ticks(pose["ticks"])            # servo positions; the gripper is ignored
guard.allowed(q)                              # q = {joint: model radians}
guard.why(q)                                  # "forbidden: the arm touches R8H reference - bin ..."
guard.nearest_allowed(q)                      # the nearest pose that stays allowed in ticks
guard.nearest_allowed_ticks(pose["ticks"])    # the same, read and returned in ticks
guard.segment_allowed(q_from, q_to)           # a straight move, through every cell it crosses
```

* A pose any of whose surrounding grid points is forbidden. Between grid
  points the table knows nothing, so a pose is allowed only when every grid
  point its interpolation touches is free: along each joint the grid value
  below it and the one above (the value itself when the pose sits on it).
  A pose on the free grid point next to a forbidden one passes; a pose
  halfway between the two does not.
* A pose outside the table on any joint.
* A pose missing a joint is an error, not a verdict.

`why` names the rover part by its CAD name. `nearest_allowed` gives the
nearest pose, in grid steps, among those that stay allowed when rounded to
servo ticks: the centre of a cell whose corners are all free, or a grid
point whose neighbours are all free. A bare free grid point is not enough,
since a tick of rounding moves it off the grid and the rule then asks its
neighbours too. The way there is not checked; `segment_allowed` checks a
move: it cuts the move where it crosses a grid value on any joint and
applies the rule in every piece, so a move that only clips the corner of a
forbidden cell is refused. The guard needs numpy only: no MuJoCo on the
robot.

### What the table does not see

* The collision geometry is convex: one hull per part, or the pieces of a
  decomposition made with a 1 mm concavity target that was not always
  reached. A single hull is larger than its part: small holes, recesses
  and clearances are filled. A decomposition can also fall short of its
  part: measured against the part's own mesh, its pieces leave the
  surface uncovered by up to 1.6 mm on the upper arm's cable boss, 0.7 mm
  on the bin, 0.6 mm on the upper cover and on the wrist, 0.5 mm on the
  forearm's cable boss, and 0.25 mm or less on every other decomposed
  part. That uses up part of the 2 mm margin where those parts meet: the
  upper arm's cable boss and the bin together reach 2.3 mm, more than the
  margin, so a real contact between those two can pass as free in the
  table. At `drive` and `look` the parts' own meshes stay about 5 mm apart
  (the closest: that cable boss and the bin, in `look`), so the two daily
  poses do not depend on it.
  The hull of the rover's body is one convex envelope: the arm cannot
  reach into the battery bay or under the deck's edges in the model,
  whatever the real openings.
* Loose cables, a load other than the can (above) and anything fixed to
  the robot after the CAD are not modelled. Nor is the arm hitting itself, or the ground.
* Between two free grid points the table knows nothing, for every link but
  the shoulder: one grid step of the pan, the lift or the elbow moves the
  jaws 12 to 14 cm, and a wall thinner than that between two free samples
  is not seen. A finer `--steps` narrows that gap; the margin and the
  guard's rule cover part of it.
* The grid's outer band (past the model's limits) uses the model's
  kinematics past its own range: the geometry there is right, the real end
  stops are the arm's.

### Ticks and the model's angles

The table is in the model's radians; the servos speak ticks. Per joint:

    rad = sign * (ticks - model_zero_ticks) * 2 pi / 4096

`model_zero_ticks` and `sign` live in the table's `"joint_map"`, and
`"joint_map_basis"` says where they come from. A new sweep keeps both.

**The first alignment** is 2048 and +1 on all five joints: the middle of
each calibrated travel on the model's zero, every joint turning the model's
way. Rendered in the CAD scene with that map, the two poses recorded on the
arm look right:

| Pose | Ticks (pan, lift, elbow, flex, roll) | Model angles (degrees) | In the model |
|---|---|---|---|
| `drive` | 2857, 860, 3206, 868, 3221 | +71.1, -104.4, +101.8, -103.7, +103.1 | folded: the upper arm back, the forearm back over it, the gripper straight up |
| `look` | 2869, 1057, 3208, 2018, 3220 | +72.2, -87.1, +102.0, -2.6, +103.0 | the forearm level, pointing ahead, the gripper forward and down |

`drive` sits past the model's limits on the lift (4 degrees), the elbow
(5) and the wrist flex (9), `look` on the elbow (5): the real end stops
lie past the model's, the reason for the pad. The pan's zero is the least
certain of the five, about 15 degrees either way.

**The operator's check.** Place the arm in `drive`, then in `look` (replay
the named poses), and show the model at the same ticks, through the map
the table carries. The viewer's joint sliders stop at the model's limits,
so set the angles from a script:

```python
import time, mujoco, mujoco.viewer
from moss_dimos.arm_guard import JointMap
m = mujoco.MjModel.from_xml_path("MOSS_R31.xml")
d = mujoco.MjData(m)
ticks = {"shoulder_pan": 2857, "shoulder_lift": 860, "elbow_flex": 3206,
         "wrist_flex": 868, "wrist_roll": 3221}                 # drive
for joint, rad in JointMap.load().pose_to_rad(ticks).items():
    d.joint(joint).qpos = rad
mujoco.mj_kinematics(m, d)
with mujoco.viewer.launch_passive(m, d) as viewer:              # nothing steps
    while viewer.is_running():
        viewer.sync()
        time.sleep(0.1)
```

For each pose the robot and the model should match: the direction of the
upper arm and of the forearm, the gripper's direction and its turn. The pan
is the joint to watch: the arm's heading over the rover. When they match,
the first alignment holds. When a joint differs, align it with two measured
poses (below), write the result into `"joint_map"` with a new
`"joint_map_basis"`, and check `drive` and `look` again with
`guard.why_ticks(...)`.

**Two-pose alignment.** Place the arm (torque off) in two poses whose model
angles are known, read the five positions in both
(`tools/moss_arm_calibrate.py --show`), then:

```python
from moss_dimos.arm_guard import align_joint_map
joint_map = align_joint_map(ticks_a, ticks_b)   # {joint: ticks} read in pose A and in pose B
```

`align_joint_map` takes each joint's angle from `POSE_A` (all joints 0)
and `POSE_B` (+1.571, +1.571, -1.571, +1.571, +1.571 for pan, lift, elbow,
flex, roll; the elbow negative), so no sign is typed by hand; it takes
other poses too (`pose_a`, `pose_b`). `align_from_two_poses(ticks_a,
rad_a, ticks_b, rad_b)` does one joint. Both refuse two poses less than
0.2 rad apart, and a slope more than 15 % off 652 ticks per radian (a wrong
pose or a wrong joint).

### When a new CAD scene arrives

1. Sweep it: `python tools/moss_arm_keepout.py --model <scene.xml> --names
   <its parts_manifest.json> --calibration config/arm_calibration.json`.
   Read what it prints: the layout, the visual meshes kept, the exclusions
   kept, the parts held inside others, the fingers' open pose, the
   calibrated travel covered, the parts hit and the worst pairs.
2. Check the daily poses: `guard.why_ticks(...)` on `drive` and `look` must
   say free. When one is refused, the message names the part; measure how
   close it is in the model before changing the margin, and say why in the
   documentation.
3. Bench: `python benches/bench_arm_guard_cold.py` (`MOSS_ARM_CAD=<scene.xml>`
   points it at the scene, `MOSS_ARM_MODEL=<robot.xml>` at the simulation
   model, `MOSS_ARM_CALIBRATION=<file>` at the arm's calibration when it is
   not in `config/`).
4. Commit `config/arm_keepout.json`. Its `model.sha256` and
   `model.geometry_sha256` say which scene it came from (the second one
   changes with any mesh); its `joint_map` is the one it replaced.

## Drop

`config/arm_drop_poses.json` holds a pick-and-drop sequence (format
`moss-arm-drop/1`): drive, travel, pick (the gripper closes), lift, clear
(the arm folded high over the base: the pose to wait in), drop over the bin
(the gripper opens), clear, drive. Each pose is five model radians (`rad`),
its ticks through the table's `joint_map` (`ticks`, recomputed by the tool)
and its tool point in the model's world frame (`tcp_m`). Each move of
`sequence` names its poses, its duration, the jaw gap at both ends
(`gap_mm`, turned into gripper ticks by the line through `open` and
`grasp` of `gripper`) and whether the can is held. A move is a straight line
in joint space timed by a quintic smootherstep; the pan is never wrapped.
`shift_deg` on a pose and `via` on a move are the smallest changes that pass
the guard at clearance 1; `--as-delivered` leaves them out.

```sh
python tools/moss_arm_drop.py plan [--as-delivered] [--clearance 1] [--suggest] [--mujoco auto]
python benches/bench_arm_drop_cold.py
```

`plan` moves nothing: it checks every sample of every move (a quarter of a
grid step apart at most) with the guard, `segment_allowed` and the sweep's
box rule, prints one line per move with the reason of a refusal, and with
`--mujoco` counts the contacts of the whole sequence in the CAD scene.

## The floor the gripper reaches

`tools/moss_arm_reach.py scan` poses every allowed cell of the keep-out table in
the CAD scene and keeps the poses whose gripper points down (within 25 degrees
of vertical) with the jaws' lowest point 8 to 40 mm above the floor. The result,
`config/arm_floor_reach.json`, is the floor the arm can pick at, in base_link
(from the lidar's floor point, x forward, y left) and in the chassis frame, one
pose (ticks) per point. `near X Y` prints the pose nearest to a point on the
floor and how far its tool point is from it. On the R31 scene the reach ends
31 cm ahead of the lidar's point and spans 34 cm to the right and 24 cm to the
left; a piece of litter farther than that needs one base move first, by the
difference, not a fine approach.

```sh
python3 tools/moss_arm_reach.py scan              # mujoco and the CAD scene; a few seconds
python3 tools/moss_arm_reach.py near 0.40 -0.11   # today's can: 10 cm beyond the reach
```

`tools/moss_arm_pick_at.py X Y` aims the cycle at a point on the floor (base_link
metres): the floor pose nearest to it becomes `pick`, a pose 5 to 12 cm above it
with the same pan becomes `travel` and `lift`, the rest of the cycle is the
delivered one, written to `config/arm_pick_at.json`. It refuses a point more
than 4 cm beyond the reach and says how far the base has to move first. Check
the file before playing it, as any cycle: `tools/moss_arm_drop.py plan --poses
config/arm_pick_at.json --mujoco auto` must report zero contact in the CAD
scene (the coarse table refuses the moves near the hull and the lidar base at
clearance 1, as it does for the delivered cycle; `--suggest` proposes the
shifts and vias). Then `tools/moss_arm_direct.py --poses config/arm_pick_at.json
--pick-pose pick` plays it.

`tools/moss_arm_direct.py` plays the pick-and-drop cycle straight on the servo
bus, without the coordinator (the trajectory, the goto and the pick pose are the
same as `moss_arm_play.py`; what is missing is the RPC and the lag cancel, the
worst following error is printed at the end). It is the player that ran the
cycle on the robot first, on 25 October: 57 s, back at drive, pan 491 and lift
145 ticks of worst lag.

## The arm in dimOS

`moss_dimos/arm.py` puts the arm under dimOS's control coordinator: one
hardware component (`arm/shoulder_pan` … `arm/wrist_roll`, `arm/gripper`),
one joint-trajectory task capped at the sweep's 400 ticks per second, and
the cycle of `config/arm_drop_poses.json` sampled into one `JointTrajectory`
(the quintic on the joints, the cubic on the jaw gap, every move stretched
to the cap). Units are the model's radians and the jaw gap in metres; the
adapters speak ticks.

```sh
dimos --simulation mujoco run moss-dimos.moss-arm   # the CAD scene in MuJoCo, dimOS's sim adapter
dimos run moss-dimos.moss-arm                        # the arm on its port (MOSS_ARM_PORT), the Feetech adapter
tools/moss_arm_play.py [--sim] [--stop-after release] [--from back_to_clear] [--dry-run]
```

`moss-arm` is a coordinator alone; `tools/moss_arm_play.py` sends the cycle
over RPC from wherever the arm is (a `goto` move first when it is not at
the cycle's first pose), reads the joints back every 50 ms and prints the
worst following error per joint; a joint more than `--max-lag` ticks behind
for `--lag-seconds` cancels the trajectory and the run ends with `ARM LAG`.
`--stop-after release` leaves the arm over the bin; `--from back_to_clear`
is the return. At the video's `pick` the jaws' lowest point is 62 mm above
the floor: right for an object standing, too high for a can lying down;
`--pick-pose pick_low` (or `MOSS_ARM_PICK_POSE=pick_low`) plays the
`pick_low` pose instead, the jaws 21 mm above the floor at the same spot,
checked in the CAD scene with the can held.

**Simulation.** `arm.sim_scene` writes a simulation scene from the CAD
scene into the MOSS state directory: the mesh directory made absolute, the
arm joints' ranges and the actuators' control ranges set to the
calibration's measured end stops (the delivered scene carries the upstream
model's nominal ranges, which stop short of the drive pose: the lift 4,
the elbow 5 and the wrist flex 9 degrees), the jaw actuator stiffened (the
delivered one crawls), and the three self-contact pairs of the folded arm
left out (in the delivered scene the forearm's collider sinks 16 mm into
the shoulder's at the drive pose, where the real arm rests). Arm-rover
contacts stay: `benches/bench_moss_arm_sim_cold.py` runs the whole cycle in
this process and counts them (none), checks the joints read back what was
commanded (the pan +30 degrees reads +30.00) and the jaws measure their
gap (53 mm, 90 mm). The sim adapter's gripper value is inverted over the
joint's range in both directions; `sim_gripper_command` and
`sim_gripper_gap` are the only places that know it. The calibration file
lives on the robot (`config/arm_calibration.json`); elsewhere point
`MOSS_ARM_CALIB` at a copy.

**The robot.** `moss_dimos/arm_feetech.py` is the `feetech_so101` adapter:
scservo_sdk on the arm's port, one read of the six present positions per
tick and a goal write for every servo whose target moved by a tick; goal
speed 400 and acceleration 50 set once, the gripper's force limit 400 on
registers 44 and 48, torque on at activate and off at deactivate. It
watches what the coordinator does not: a servo more than 150 ticks from
its goal and not moving for a second sets `FOLLOWING_ERROR` in
`read_error()`; a bus that stops answering keeps the last positions and
turns `has_live_state()` off, which stops the coordinator's commands.
`benches/bench_moss_arm_feetech_cold.py` runs it on a fake bus, under the
coordinator too. The coordinator ticks at 50 Hz on the robot: six reads
and six writes at about 1.2 ms each fit in a tick.

What the scene check found on the way: the keep-out table refuses the
delivered travel and drop poses, but the CAD scene posed at one degree per
joint between samples finds no contact along the whole sequence (1 021
poses, 2 mm margin, the can held). The refusals are the table's grid
(steps of 14 to 19 degrees, 49 on the roll: a forbidden neighbour 16 to
31 degrees away), not the poses. The cycle therefore runs as delivered;
the table stays the veto for moves the scene check has not seen.
