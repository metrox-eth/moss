# Sources and measurement provenance

Session: **27 October 2026**, Show Robotics workshop. Code and screenshot are part of the MOSS experimental collection.

| Component | Revision / version used |
|---|---|
| MOSS runtime | `1590dcb1c4c58181c037738d44a22e3940f982db` |
| [dimOS](https://github.com/dimensionalOS/dimos) | `a7d19f76158b01739b26e7a17390f89764aaef83` (`0.0.14b1`) |
| [Mighty SDK](https://github.com/asadm/mighty-protocol) | `aeb060e36a6cc25edae9153b4806dbfa99c343a4` |
| Mighty camera firmware | `Mighty v.2026-10-01-e2aac61` |
| [A733 NPU example / libraries](https://github.com/ZIFENG278/ai-sdk) | `fc90006d0f6569da2f6726c2d8395877686f5aca` |
| VIPLite runtime reported by the board | `2.0.3.2-AW-2024-08-30` |
| NPU model | Upstream `examples/yolov5/model/v3/yolov5.nb`, COCO classes, 640 × 640 |

The A733 NPU route was taken from the [Radxa A733 documentation](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-vpm-run), then tested on this Orange Pi. No Rockchip RKNN or Jetson CUDA runtime is used for this NPU path.

The NPU wrapper runs the native example once per processed frame. Model setup, JPEG I/O, preprocessing, output copies and postprocessing explain why total pipeline time is much longer than network execution. A persistent native worker is a possible later optimization, not part of these measurements.

The 20.42-second integration sample used a 1 Hz detector cap and a CPU quota equivalent to four cores. The handheld recording used a 3 Hz cap. Both had the cooler installed and the same live camera. Synthetic scans exercised odometry and costmap generation; planner and mission modules were loaded but idle, and controllers used in-memory/mock interfaces.

The cockpit derives from MOSS's existing cockpit, with **Space Grotesk** and MOSS assets. Font copyright: The Space Grotesk Project Authors; the [SIL OFL license](moss_mighty/cockpit/fonts/SpaceGrotesk-OFL.txt) is included. New code follows the repository's Apache-2.0 license. Documentation and the demo frame follow the repository's CC BY 4.0 media terms.

The downloader references upstream model weights and VIPLite binaries; their licenses are not changed by this repository. These files are not redistributed in Git. The [file manifest](scripts/npu-files.json) records the exact upstream inputs and hashes.

No OS image, workshop network configuration, SSH setup, private credentials or complete camera recordings are included.
