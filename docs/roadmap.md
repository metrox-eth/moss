# Roadmap

- **Now (V0.3 prototype)**: the print set is essentially complete and the power and control harness ran both motors on the bench (20 September). Integrate the harness into the chassis, set the installed motor and encoder directions, measure ticks per revolution, write the Jetson–ESP32 interface then speed control; assemble, fit and check every part on the real thing. What turns out wrong is logged in [assembly_feedback.md](assembly_feedback.md); some fixes go on the prototype, the others into the next hardware revision (not numbered yet), which also gets mounts for the ESP32-S3, the servo adapter and the real power distribution. Manufacturing files are published part by part once their validation is decided.
- **Next**: first roadside run, teleoperated with a gamepad through dimOS; first recordings.
- **Then**: mount the arm and gripper; collect pick-up demonstrations; publish the first pooled dataset.
- **Later**: first policy; first autonomous pick on video; kits so the first hundred builders do not have to source parts themselves.

No dates. Each step is posted when it is real.
- **MOSS Lite**: the same base with a Raspberry Pi in the compute cartridge instead of the Jetson, teleop and data collection only, for builders without a Jetson.
