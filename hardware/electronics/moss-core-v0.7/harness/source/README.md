# Rebuilding the visual study

Run commands from the `harness/` directory in a Python environment with the dependencies in `requirements.txt`. The frozen meshes in `assets/` preserve the current Core, native context, speaker and prototype hull positions. They are inputs, not additional hardware revisions.

```sh
python source/build_hoco.py
python source/build_harness.py
python source/export_harness_step.py
npm ci --prefix viewer_runtime
node source/build_viewer.mjs
```

The generated files go into ignored `output/` and `assets/HARNESS_SCENE.npz`; published CAD/data are kept separately in `cad/` and `data/`. No native PCB or released rover file is edited. The connector mesh cache includes the KiCad reference header so an installed macOS KiCad path is not required for a normal cached rebuild.

The source includes the complete visual routing recipe and the tie-bridge primitive. The supplied hull STEP/STL are the editable mechanical result; the scene builder does not reconstruct the original Fusion history or repeat its native mesh Boolean workflow.

## Video

```sh
python source/render_story.py --stills
MOSS_MUSIC=/absolute/path/to/your/licensed-music.m4a python source/make_story_audio.py
python source/render_story.py
```

The film uses VTK camera motion and lighting, with Pillow for the existing MOSS graphics and FFmpeg for encoding. It streams frames straight to the encoder rather than saving a large image sequence. The STOP/battery callout shot has a stationary camera; callout endpoints are projected from model coordinates. The soundtrack source is not bundled; use music you have permission to use. The current soundtrack contains music only, with no generated transition beeps.

The offline viewer is a Three.js bundle with the GLB embedded. Bundle checks verify the GLB container, embedded resources and JS compilation. This publication does not claim an automated interactive browser acceptance test.
