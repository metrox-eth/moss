# MOSS

Cleaner streets, one maker at a time.

MOSS is a small, mostly 3D-printed litter-picking rover: tracked base, a collection bin, and an arm derived from the SO-101 with a NormaCore parallel gripper. Target parts cost: 500 to 700 USD plus a Jetson (before tax and shipping, labour and tools excluded). The goal is a design any maker can print, build, improve, and run where they live.

![MOSS exploded view, turntable](media/images/moss_exploded_turntable.gif)

This repository is the build log, the design files as they become real, and the software as it gets written. It started on 15 September 2026. Nothing here is finished; everything here is real. The animation above is a CAD visualization from 18 September (the V0.3 exterior, exploded and assembled); newer cover studies are not the physical prototype. The photo below is the bench on 20 September: the power and control harness wired for the first motor tests. The concept video from 15 September (V2.3.1) shows an earlier design: almost everything changed since.

![Power and control harness on the bench, 20 September](media/images/build_harness_bench_20260920.jpg)

## Status — V0.3 prototype, 20 September 2026

- Printing is reported essentially complete for the chassis, bin and cover, track structure, wheels and rollers, tensioners, spacers, interior supports, the SO-101-derived arm and the NC90 gripper. See the [printed-parts inventory](docs/printed_parts.md): 111 pieces in the reconciled print set, plus two camera brackets to confirm.
- One TPU 95A track printed with a 0.8 mm nozzle is too stiff and will be reprinted. The first track has good flexibility and grip in manual floor tests.
- Assembly and fit checks continue. The corrected motor-bracket revision and the two RealSense mounting brackets still have to be confirmed on the bench before the print set is called fully reconciled.
- The unfinished front-cover interface stays on this prototype; its redesign is deferred to the next hardware revision.
- 20 September: the power and control harness is assembled and was bench-tested. Both drive motors and their quadrature encoders ran from an Espressif ESP32-S3-DevKitC-1 through two Cytron MD10C R3 drivers: 15 % single-motor tests, then one 0–100 % PWM ramp cycle in each direction, then the 25 % commissioning limit was restored. Unloaded, on the bench; commanded and timed stops observed. No rover roll, no loaded or stall test. Details, numbers and limits in the [build log](docs/build_log.md#2026-09-20--power-and-control-harness-first-motor-and-encoder-tests); video: [MOSS_motor_encoder_bench_20260920.mp4](media/video/MOSS_motor_encoder_bench_20260920.mp4).
- Electronics as selected now: Jetson Orin Nano 8 GB (in its original plastic base, inside the printed cartridge), Intel RealSense depth camera (IMU inside), ESP32-S3-DevKitC-1 V1.1 as motor controller, 2 × Cytron MD10C R3, 2 × geared motors with encoders, a separate Waveshare Bus Servo Adapter (A) V1.1 for the arm servos (arm not tested yet), an INA219 module used for battery voltage only, fuse holder and positive distribution block. The Waveshare General Driver for Robots is no longer part of the design.
- Ordered: steel shafts (5/6/8 mm), bearings (608, 626), shaft collars, 6 mm couplings, M3 and M4 fasteners.
- Software: the ESP32-S3 commissioning firmware in [`firmware/`](firmware/README.md) (serial commands, disarmed at boot, 300 ms command watchdog, 25 % limit, encoder and voltage telemetry; host logic test passes). On the Jetson side, a scaffold (gamepad teleop logic and differential-drive kinematics, cold-tested, not yet run on the rover). No speed control, no odometry, no drive test on the ground, no autonomous pickup yet.
- Next: integrate the harness into the chassis, set forward direction and encoder signs after the mirrored installation, measure ticks per revolution, write the Jetson–ESP32 interface then speed control; replace the stiff track, assemble and check the drivetrain, fit the arm.

## Demo

A recorded-run 3D demo where Jev (TypeSafe AI's decision model) chooses which litter to pick up: https://www.showrobotics.ai/moss-jev/ (three real API responses, replayed; no live inference). Mirror: https://metrox-eth.github.io/moss-jev/ · Source: https://github.com/metrox-eth/moss-jev

## Data

Teleop data recorded by MOSS builders is meant to be pooled and open, so the shared model gets better with every robot. Details and the rules we propose are in [docs/data.md](docs/data.md).

## Layout

- `docs/` concept, build log, bill of materials, data, roadmap, software notes.
- `hardware/` design files (coming as parts are validated); `hardware/bench/` raw traces of the bench tests.
- `firmware/` ESP32-S3 commissioning firmware, its host test and wiring map.
- `moss_dimos/` software scaffold (dimOS modules).
- `media/` videos and images of the concept and the build.
- `tests/` cold tests (no hardware needed).

## License

Code under Apache-2.0. Hardware files and documentation under CC BY 4.0. See `NOTICE`.

Built in public by [@metrox_eth](https://x.com/metrox_eth).
