# Does the MOSS shoulder want a second servo?

MuJoCo studies on the R92 model (`../mujoco/model/moss_robot.xml`) for
[issue #2](https://github.com/metrox-eth/moss/issues/2): the shoulder's load at
every pose MOSS uses, the pick-and-drop cycle under full dynamics, two STS3215 on
one shaft, a spring instead, and tipping. The full write-up with charts and
tables is `out/report.html` (download it and open it in a browser).

**Status: simulation evidence, not a bench result.** The arm is the model's,
scaled to the 768 g weighed in issue #2; servo figures are Feetech's; how
stiffly the servo holds its goal, bracket stiffness, encoder offsets and the
follower's behaviour are modelled, not measured. The bench steps at the end
are what would settle them.

## Findings

The litter is MOSS's own test object: the can in `../mujoco/model/scene.xml`
(66 × 115 mm, 20 g), the one the keep-out table sweeps. The heavier case is an
empty 0.33 l glass bottle (250 g), since the detector picks glass by default.
Heat is (torque / 0.98 N·m)², the servo's continuous rating (10 kg·cm); stall is
30 kg·cm at 12 V, about 2.65 N·m on the 3S pack.

1. **The litter barely counts.** The can adds 0.04 N·m at the pick. Over a whole
   cycle the shoulder peaks at 50 % of stall and averages 0.15× its rating; the
   elbow stays under its rating throughout.
2. **The weak moment is holding still at the pick.** MOSS picks every object at
   one pose (`pick_low`), where the shoulder holds 0.92 N·m, 0.89× its rating,
   with the can or without it. Over all 645 floor picks of the reach table the
   median is 1.00× and 40 % are over. The cycle spends about 3 s above the rating
   there today; a wrist-camera check before the grasp, or a re-grasp, adds time
   exactly there. Issue #2's test (a can at full reach for a minute) is 2.1× the
   rating: it can pass without drift while the servo heats.
3. **The cheapest fix is where the arm picks.** The arm sits on top of the
   rover behind its nose, so today's pick is a stretched reach 0.18 m past the
   tracks' front end (tool at x 0.346 m). The mission drives the object to one
   pick point, so moving it closer is a config change (`MOSS_PICK_XY_M` and the
   pick pose): at x 0.29 m the shoulder runs at 0.46× instead of 0.89×. The pose
   matters too: at x 0.31 m the reach table's poses range from 0.46× to 1.19×,
   and its tie-break picks the pose nearest `pick_low`, not the lightest. Whether
   the nose camera still sees the object that close is a check on the robot
   (`s6_pick_point`).
4. **Whether two servos given the same goal share depends on how stiffly the
   servo holds its goal.** With the model's servo (Menagerie's 998 N·m/rad: full
   torque about 2 ticks, 0.17°, off its goal), the second servo takes 14 % of the
   load through a printed bracket when perfectly calibrated, and at 4 ticks of
   encoder offset the hotter one runs at 2.9×, against 0.89× for one servo; same
   goal was hotter than one servo in 47 of 84 variants at the pick. The bench
   note in issue #2 says the real loop is much softer near its goal: under load,
   a goal a few ticks away does not move the arm, which a 998 N·m/rad servo
   cannot do. With a servo soft enough that one alone sags 0.5° at the pick
   (100 N·m/rad), same goal with RoArm's zero at boot beats one servo at any
   offset up to ±4 ticks (0.74× at worst); at a 1° sag it is 0.53× at worst. One
   reading on today's arm decides it: one servo at `pick_low`,
   `Present_Position` minus the goal. About 6 ticks or more and same goal will
   share; 1–2 ticks and it fights.
5. **If the loop is stiff, a follower shares evenly.** Servo A holds position; servo B runs open-loop
   PWM (mode 2) and copies A's `Present_Load` over the bus. That splits 50/50 at
   any offset: 0.22× each at the pick. B has to follow with a time constant of
   about 0.1 s (at 50 Hz, 20-30 % of the gap per update); faster, it rings
   against A's loop.
6. **For a load that is all arm weight, a spring fits better.** A gravity-balance
   spring of 0.66 N·m peak (zero free length, torque A·sin(θ − φ)) brings the
   pick pose to 0.08×, with nothing to sync. With a 250 g glass bottle at the
   pick: one servo 2.0×, spring 0.57×, two servos sharing evenly 0.50× each.
7. **Tipping is not a risk** at these weights: 1.09 kg held stretched out to the
   side before the rover tips on flat ground.

A model note: the XML's shoulder range (±100°) stops short of the drive pose
(−104.4°, ticks 860, the calibrated end stop). `moss_dimos` widens the ranges
when it writes its own scene; the XML alone does not.

## Bench steps that would settle it

1. How stiffly one servo holds, on today's arm: at `pick_low`, the shoulder's
   `Present_Position` minus its goal, arriving from above; then step the goal by
   2, 4 and 8 ticks and note when the arm moves. About 6 ticks of sag or more:
   same goal will share. 1–2 ticks: expect a fight, use the follower.
2. Encoder offset across the travel: both servos on the joint, torque off,
   swing the arm by hand end to end, log both `Present_Position`.
3. Idle fight: torque on, arm in the drive pose, log `Present_Load` and
   `Present_Current` on both for 30 s. Opposite signs mean they fight.
4. Issue #2's hold with the can, 60 s at `pick_low` and at full reach, logging
   `Present_Temperature` on both: one servo, same goal, follower, spring.
5. The pick point a few cm closer: does the nose camera still see the object,
   and does the approach land it there?

## Run

The same environment as `../mujoco`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make all        # about 25 minutes; writes out/*.json and out/report.html
```

| Study | Question |
|---|---|
| `s1_torque_budget` | Holding torque per joint at every pose MOSS uses (cycle, drive, 645 floor picks, worst stretch), against the servo's continuous and stall torque |
| `s2_cycle` | The pick-and-drop sequence of `config/arm_drop_poses.json` under full dynamics, one vs two shoulder servos, payload and a 20 s wait at the pick |
| `s3_two_servos` | Two STS3215 on one shaft: same goal vs follower, encoder offset × bracket stiffness × play × P; the follower's gain and bus rate; same goal against how stiffly the servo holds its goal |
| `s4_tipping` | Least payload that tips the rover, and the slope margin |
| `s5_spring` | A gravity-balance spring instead of (or with) a second servo |
| `s6_pick_point` | Shoulder load against where the arm picks, straight ahead, from the reach table |

`moss_arm.py` holds the shared model edits (rover pinned, arm scaled to 768 g,
payload at the tcp) and the servo figures. Contacts are off in the dynamic
studies: they measure what the servos must give, not grasp success.
