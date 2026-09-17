# Software notes

MOSS runs on dimOS. The software here starts as a scaffold derived from vector-dimos, the external dimOS blueprint written for VECTOR (a mecanum rover on the same Jetson Orin Nano 8 GB).

What carries over as is: gamepad teleop publishing a Twist, the rig/onboard split over zenoh, the recording tooling.

What changes: VECTOR is holonomic (mecanum), MOSS is a differential-drive tracked rover. The strafe axis of the pad is ignored, and the motor layer is two Cytron MD10C drivers with encoder feedback instead of RS485 servo drives. `moss_dimos/diffdrive.py` holds the kinematics; the driver module is not written yet.

Everything in `moss_dimos/` is cold-tested only until the base runs.
