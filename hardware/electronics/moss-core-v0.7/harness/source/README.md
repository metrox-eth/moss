# Rebuild the current harness study

Run from `harness/` using the Python dependencies listed in [requirements.txt](../requirements.txt). The frozen assets now match the 1 November 2026 Core PCB `7d88...`, the final Orange Pi pose and the matching 74 x 71 mm hull boss pattern. A normal rebuild uses these supplied meshes and does not export or modify the PCB.

```sh
python -m pip install -r requirements.txt
python source/build_harness.py
python source/export_harness_step.py
python source/check_current_routes.py
python source/check_cooler_lid.py
python source/build_current_rfq.py
npm ci --prefix viewer_runtime
node source/build_viewer.mjs
```

Outputs go into ignored `output/`; the scene mesh is written into `assets/HARNESS_SCENE.npz`. Published CAD, data, RFQ and viewer files are separate reviewed copies. The connector cache includes its KiCad motor-header reference and dimensioned cable housings, so cached rebuilding does not require a macOS KiCad installation.

`build_harness.py` is the current 14-route recipe. The RFQ generator validates the PCB hash, all route counts and the independent connector map before producing its 42-wire schedule. Its length estimates include drawn slack; batch cut/strip dimensions still require a fitted first article. `extract_current_anchors.py` is an optional read-only native KiCad Python extraction step and requires pcbnew/wx from KiCad, not the regular Python environment.

`export_harness_step.py` produces common-trunk conduit reservations, not complete crimped wires. Individual paths, including the Cytron fanout, are retained in `ROUTE_LENGTHS.json` and the GLB. `render_current_static.py` produces current static review frames. No browser interaction was tested in this session; the offline bundle has no required external network resources.

The hull is maintained in the [dedicated source package](../../../../mechanical/moss-v0.7-hull/). The historical `render_story.py` and audio scripts preserve the earlier film; do not use them as current assembly instructions. There is no new video in this update. Only the STOP tail moves with the removable lid.
