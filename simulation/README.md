# MOSS simulation

The current model lives in **[mujoco/](mujoco/)** alongside the MOSS hardware and
software. It follows the published **V0.6 / R92** assembly.

Start with [the quick start](mujoco/README.md), or import
[`moss_robot.xml`](mujoco/model/moss_robot.xml) with its complete
[`meshes/`](mujoco/model/meshes/) folder. For a floor and a test object, open
[`scene.xml`](mujoco/model/scene.xml).

This is a preliminary model for development. Its geometry, software checks and
remaining physical calibration work are documented together. Dirac Robotics'
calibrated simulation is ongoing work; this package does not claim that result.
