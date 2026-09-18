# Software notes

MOSS runs on dimOS. The software here starts as a scaffold derived from vector-dimos, the external dimOS blueprint written for VECTOR (a mecanum rover on the same Jetson Orin Nano 8 GB).

What carries over: the idea of a gamepad module publishing a Twist behind a deadman, the rig/onboard split over zenoh, the recording tooling.

What is written for MOSS: `moss_dimos/teleop_logic.py` (pure: two stick axes only, forward and yaw, no lateral input exists; deadzone; deadman with a brake window of zeros; every value validated) and `moss_dimos/diffdrive.py` (differential-drive kinematics, scaling instead of clipping, invalid configs and non-finite commands refused). `moss_dimos/gamepad.py` is the thin dimOS wrapper around them. The motor layer (two Cytron MD10C drivers with encoder feedback behind the Waveshare ESP32 board) is not written yet; neither is the stop on stale command. Both come with a written Jetson–ESP32 contract before the first roll.

Everything in `moss_dimos/` is cold-tested only until the base runs.
