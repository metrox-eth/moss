# Running the experimental bench

This is a source snapshot of the first bench session, not a ready-to-flash OS image. It does not provision Wi-Fi, change SSH access, flash firmware or configure a real rover.

## Board and camera

Use the **A733 Orange Pi Zero 3W**, with its cooler installed, a suitable power supply, and an ARM64 vendor image that provides `/dev/vipcore`. The measured system used Armbian 26.8.1 / Debian 13 with kernel `6.6.98-vendor-sun60iw2`. The NPU helper below supplies user-space libraries, not a kernel driver.

Connect MightyCam with a **USB data cable**. Its USB network interface should have an address on the camera's subnet. Our camera is served at `http://192.168.7.1`; check it from the Orange Pi. No extra camera stream needs to be opened in another application.

## Python environment

These commands are run on the Orange Pi from the **MOSS repository root**. They use `uv` and a Python 3.12 virtual environment.

```sh
sudo apt-get install build-essential pkg-config git python3-venv \
  libgl1 libegl1 libglib2.0-0 libgomp1 libturbojpeg0 libusb-1.0-0 \
  libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0 \
  libopencv-core-dev libopencv-imgcodecs-dev libopencv-imgproc-dev libjpeg-dev

uv venv --python 3.12 .venv
DIMOS_ALLOW_MISSING_COCKPIT=1 uv pip install --python .venv/bin/python \
  -r experiments/orange-pi-mightycam/requirements.txt
uv pip install --python .venv/bin/python -e '.[nav,gamepad]' \
  -e ./experiments/orange-pi-mightycam
```

The dimOS and Mighty SDK revisions are pinned. Current upstream versions may change the blueprint APIs. Use the LCM loopback configuration in [MOSS software setup](../../Software.md) if multicast transport is not already configured.

## Build the NPU example

The vendor libraries, pretrained model and example sources are **not included in this repository**. This downloads the small set of required files from the pinned upstream revision, checks their SHA-256 hashes, then builds the example on the board:

```sh
python3 experiments/orange-pi-mightycam/scripts/fetch_npu.py
bash experiments/orange-pi-mightycam/scripts/build_npu.sh
```

Files go under this experiment's ignored `runtime/npu-sdk/` directory. The helper replaces an unused HighGUI include with `imgcodecs` and corrects the end iterator of the sample's output-vector copies. It does not install libraries globally. Upstream components retain their own terms; see [SOURCES.md](SOURCES.md).

## Start one profile

```sh
bash experiments/orange-pi-mightycam/scripts/run.sh demo
```

For the additional simulated rover load, stop the first process with Ctrl-C, then run:

```sh
bash experiments/orange-pi-mightycam/scripts/run.sh full-bench
```

Open **`http://<orange-pi-ip>:8905/`** in a browser on the same LAN. Include the port. If a Mac browser cannot reach the board while other applications can, check that browser's macOS **Local Network** permission.

`Record` saves the current camera views, trajectory and measurements as a 1920 × 1080 video, using the browser's available encoder (MP4 or WebM). It stops after 30 seconds or when you press `Stop`. It records no audio and sends no video to a cloud service. Reset the displayed path before a new take if desired; this does not reset or calibrate Mighty VIO.

Settings may be overridden with `MOSS_MIGHTY_URL`, `MOSS_MIGHTY_WEB_PORT`, `MOSS_MIGHTY_DATA_DIR`, `MOSS_NPU_SDK`, `MOSS_YOLO_FPS` and `MOSS_DIMOS`. The launcher defaults to experiment-local runtime storage. The package alone defaults to `~/.local/share/moss-mighty/`.

The CPU detector fallback is retained in the source but is not the measured NPU profile. It additionally needs CPU builds of PyTorch/torchvision, Ultralytics, and a local model selected by `MOSS_YOLO_MODEL`; those weights and dependencies are not bundled.

## Checks

Standard-library tests, without hardware or the full dimOS environment:

```sh
PYTHONPATH=experiments/orange-pi-mightycam python3 -m unittest discover \
  -s experiments/orange-pi-mightycam/tests -p 'test_core.py' -v
```

With the installed environment, the message, SDK and HTTP tests can also run:

```sh
.venv/bin/python -m unittest discover \
  -s experiments/orange-pi-mightycam/tests -p 'test_integration.py' -v
```

The original bench passed 14 software checks. Physical VIO accuracy failed during the handheld trial and remains unvalidated; a passing software test is not a substitute for calibration and a measured trajectory.
