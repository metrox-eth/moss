# Roadmap

- **Now (V0.3 prototype)**: the print set is complete and the rover rolled for the first time on 22 September. Fix the track tension (second tensioner per track), measure ticks per revolution, write the Jetson–ESP32 interface then speed control; fit the arm. What turns out wrong is logged in [assembly_feedback.md](assembly_feedback.md); some fixes go on the prototype, the others into V0.4, which also gets mounts for the ESP32-S3, the servo adapter and the real power distribution. Manufacturing files are published part by part once their validation is decided.
- **Next**: first roadside run, teleoperated with a gamepad through dimOS; first recordings.
- **Then**: mount the arm and gripper; collect pick-up demonstrations; publish the first pooled dataset.
- **Later**: first policy; first autonomous pick on video; kits so the first hundred builders do not have to source parts themselves.

No dates. Each step is posted when it is real.
- **Lower-cost Pi build (experimental)**: Raspberry Pi 5 8 GB with either Mighty Camera or STEVAL-VL53L9 3D ToF, plus a colour camera. Start with teleop and data collection, then evaluate navigation and detection with dimOS on the Pi. Next: mount and test both sensors with dimOS, teleop and data collection first, then navigation and detection. Nothing is validated until it runs on the rover.

- **V0.4 hull and wiring**: current CAD includes the revised electronics arrangement, Jetson cable route, battery envelope and exterior-access motor fasteners. QT Py, screw-terminal BFF and INA219 STEMMA QT replace the DevKitC and the bare INA module. Reconcile the new INA footprint and real USB connectors, port the controller pin map and validate the printed assembly before release. [Detailed status](hardware_v04.md).
