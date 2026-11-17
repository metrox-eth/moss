#!/usr/bin/env python3
"""Cold bench for tools/moss_preflight.py: the MOSS flight check, every probe
stubbed, so what is proven is the VERDICT each world gets.

Known input -> known output in physical units (battery mV -> volts, lidar
points/s, GB free). No robot, no serial port, no dimOS: every probe of
the module is replaced by a counting fake, so the bench also proves which
devices the check did NOT open. Groups:

  A. all green      - exit 0, "N/N OK - ready to fly", 11612 mV -> 11.61 V,
                      the QT Py opened once at 115200 and not one byte written,
                      the lidar probed once on the CP2102N path
  B. QT Py missing  - KO on the board, firmware skipped, the port never opened
  C. stack running  - registry entry with a live pid (and an unregistered
                      `bin/dimos run`): firmware and lidar SKIPPED "held by the
                      stack", zero opens; a dead registry pid is only stale
  D. battery        - 10500 mV -> KO with the BMS sentence; 10100 -> under the
                      cut; 10800 -> OK 10.80 V; ina_ok false -> INA219 not seen
  E. gamepad        - js0 / 2563:0526 / 057e:2009 (the Nintendo sentence) / none
  F. --json         - stdout is ONE JSON document; counts match the checks
  G. --quick / --no-spin - which stubs are never called
  H. firmware and port faults - held port, armed firmware, mute firmware,
                      RealSense on USB 2, MOSS_PORT pointing at the lidar
  H2. switches      - MOSS_CAMERA off skips the RealSense (no pyrealsense2
                      needed), on it is a KO with the fix; MOSS_WRIST off skips
                      the wrist camera; MOSS_MOCK_BUS / MOSS_REQUIRE_PAD read
                      as the stack reads them (y, off, ...)
  I. software and env - the MOSS geometry line, a profile that fails, missing
                      entry points (reinstall line), pygame missing, the venv
                      importing moss_dimos from elsewhere or not at all,
                      MOSS_MOCK_BUS=1
  J. --save         - the file holds the same document (what the cockpit reads)
  L. LCM settings   - loopback multicast, the 224.0.0.0/4 route and rmem:
                      missing + passwordless sudo = OK (dimOS sets them),
                      missing without sudo = KO with the boot unit; sudo is
                      never probed when nothing is missing
  K. real probes on this machine - /proc fd scan finds a child holding a file,
                      sysfs USB ids are vvvv:pppp, our own cmdline is listed,
                      only the moss-dimos distribution's entry points count
                      and never the checkout's own egg-info, the run registry
                      follows XDG_STATE_HOME, the venv's moss_dimos is found
                      where the stack would import it, the pygame banner never
                      reaches stdout, a relative MOSS_STATE_DIR resolves to an
                      absolute path

Run:  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 benches/bench_moss_preflight_cold.py
"""

import contextlib
import fnmatch
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import moss_preflight as mp  # noqa: E402

OK = 0
KO = 0


def check(label, ok, detail=""):
    global OK, KO
    print(f"  {'OK ' if ok else 'KO '} {label}{' - ' + detail if detail else ''}")
    if ok:
        OK += 1
    else:
        KO += 1


TMP = tempfile.TemporaryDirectory()
TMPD = Path(TMP.name)
QTPY = "/dev/serial/by-id/usb-Adafruit_QT_Py_ESP32-S3_No_PSRAM_00:00:00:00:00:00-if00"
C1 = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_0000-if00-port0"
WRIST = "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._KD-USB_Cameras_KD-USB_Cameras-video-index0"
TELEMETRY = {"ms": 1000, "fw": "qtpy-mdd3a-v3", "mode": 0, "reason": "boot",
             "target_pct": [0, 0], "output_pct": [0, 0], "ramp_ms": [5, 5],
             "ticks": [160585, 158263], "invalid_edges": [0, 0], "ina_ok": True,
             "bus_mV": 11612, "shunt_uV": 0, "current_mA": None}
D455 = {"name": "Intel RealSense D455F", "serial": "000000000001", "firmware": "5.17.0.10", "usb": "3.2"}


class FakeSerial:
    def __init__(self, world, port, baud):
        self.world, self.port, self.baud = world, port, baud
        self.chunks = list(world["serial_chunks"])
        world["opens"].append((port, baud))

    def reset_input_buffer(self):
        pass

    def read(self, n):
        if self.chunks:
            return self.chunks.pop(0)
        time.sleep(0.005)
        return b""

    def write(self, data):
        self.world["written"].append(data)
        return len(data)

    def close(self):
        self.world["closed"] += 1


def default_world():
    return {
        "files": {QTPY, C1, WRIST, "/dev/input/js0"},
        "pad_names": {"/dev/input/js0": "shanwan Android GamePad"},
        "pad_axes": {"/dev/input/js0": [0, 0, 0, 0, 0, 0, 0, 0]},   # alive at rest
        "robot_env": None,          # text of <state>/robot.env, None = absent
        "runs": [],                 # (run_id, pid)
        "alive": set(),
        "cmdlines": [(1, "/sbin/init")],
        "holders": {},
        "telemetry": dict(TELEMETRY),
        "serial_chunks": None,      # None = built from "telemetry"
        "usb": {"239a:8119", "10c4:ea60", "8086:0b5c", "2c7f:4a60"},
        "free_gb": 79.0,
        "mem_kb": 6_100_000,
        "rmem": "212992",
        "lo_flags": 0x9,
        "route": True,              # the 224.0.0.0/4 route (None = `ip` cannot run)
        "sudo": True,               # passwordless sudo
        "module_file": str(ROOT / "moss_dimos" / "__init__.py"),   # where the stack imports moss_dimos
        "realsense_exc": None,
        "lidar": {"info": {"model": 65, "serial": "ABCD"}, "health": ("Good", 0),
                  "turns": 3, "points_per_s": 1500.0, "hz": 10.0, "sectors": 36},
        "lidar_exc": None,
        "realsense": [dict(D455)],
        "imports_missing": set(),
        "entry_points": {"moss-nav", "moss-explore", "moss-gamepad", "moss-base"},
        "profile": "moss",
        "profile_exc": None,
        "env": {},
        # counters
        "opens": [], "written": [], "closed": 0, "lidar_calls": [], "holder_calls": [],
        "sudo_calls": 0, "realsense_calls": 0,
    }


ENV_KEYS = ("MOSS_PORT", "MOSS_LIDAR_PORT", "MOSS_MOCK_BUS", "MOSS_RS_SERIAL", "MOSS_CAMERA",
            "MOSS_WRIST", "MOSS_REQUIRE_PAD", "MOSS_STATE_DIR",
            "MOSS_DRIVER", "MOSS_PAD_LAYOUT", "MOSS_PAD_INDEX")   # robot.env setdefaults these: cleared per case


def run(argv=(), **over):
    w = default_world()
    w.update(over)
    if w["serial_chunks"] is None:
        line = json.dumps(w["telemetry"]).encode() + b"\n"
        w["serial_chunks"] = [b"MOSS V0.4 firmware banner\n" + line[:40], line[40:] + line, line]
    runs_dir = TMPD / f"runs_{len(list(TMPD.glob('runs_*')))}"
    runs_dir.mkdir()
    for run_id, pid in w["runs"]:
        (runs_dir / f"{run_id}.json").write_text(json.dumps(
            {"run_id": run_id, "pid": pid, "blueprint": "moss-dimos.moss-nav",
             "started_at": "2026-01-01T00:00:00+00:00", "log_dir": "/x"}))
    state = TMPD / f"state_{runs_dir.name}"

    mp._ls = lambda pat: sorted(f for f in w["files"] if fnmatch.fnmatch(f, pat))
    mp._exists = lambda p: p in w["files"]
    mp._pad_name = lambda js: w["pad_names"].get(js, "?")
    mp._pad_init_axes = lambda js, listen_s=1.0: w["pad_axes"].get(js)
    mp._read_text = lambda path: (w["robot_env"] if str(path).endswith("robot.env") else None)
    mp._runs_dir = lambda: runs_dir
    mp._pid_alive = lambda pid: pid in w["alive"]
    mp._proc_cmdlines = lambda: list(w["cmdlines"])
    mp._port_holders = lambda dev: (w["holder_calls"].append(dev), w["holders"].get(dev, []))[1]
    mp._open_serial = lambda port, baud: FakeSerial(w, port, baud)
    mp._usb_devices = lambda: set(w["usb"])
    mp._statvfs = lambda path: types.SimpleNamespace(f_bavail=int(w["free_gb"] * 1e9 / 4096), f_frsize=4096)
    mp._meminfo = lambda: {"MemTotal": 7_600_000, "MemAvailable": w["mem_kb"]}
    mp._sysctl = lambda name: w["rmem"]
    mp._lo_flags = lambda: w["lo_flags"]
    mp._mcast_route = lambda: w["route"]

    def sudo():
        w["sudo_calls"] += 1
        return w["sudo"]
    mp._sudo_ok = sudo
    mp._module_file = lambda: w["module_file"]

    def lidar(port):
        w["lidar_calls"].append(port)
        if w["lidar_exc"]:
            raise w["lidar_exc"]
        return dict(w["lidar"])
    mp._lidar_probe = lidar

    def realsense():
        w["realsense_calls"] += 1
        if w["realsense_exc"]:
            raise w["realsense_exc"]
        return [dict(d) for d in w["realsense"]]
    mp._realsense_probe = realsense

    def imp(name):
        if name in w["imports_missing"]:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return types.SimpleNamespace(__version__="9.9")
    mp._import = imp
    mp._entry_points = lambda group="dimos.blueprints": set(w["entry_points"])

    def profile():
        if w["profile_exc"]:
            raise w["profile_exc"]
        return (types.SimpleNamespace(name=w["profile"], robot_width_m=0.34, pivot_diameter_m=0.5, lidar_height_m=0.2),
                {"lethal_clearance_m": 0.22, "pivot_clearance_m": 0.25})
    mp._robot_profile = profile
    mp.LISTEN_S = 0.05

    saved = {k: os.environ.get(k) for k in ENV_KEYS}
    for k in ENV_KEYS:
        os.environ.pop(k, None)
    os.environ["MOSS_STATE_DIR"] = str(state)
    os.environ.update(w["env"])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = mp.main(list(argv))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    w["state"] = state
    return rc, buf.getvalue(), list(mp.RESULTS), w


def find(results, label):
    return [r for r in results if r["label"] == label]


def line_of(out, label):
    for ln in out.splitlines():
        if f" {label}" in ln and (ln.startswith("  OK") or ln.startswith("  KO") or ln.startswith("  --")):
            return ln.strip()
    return ""


def last_line(out):
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else ""


HEADERS = ("ports (by-id)", "firmware (QT Py, listen only)", "lidar (RPLidar C1, ~5 s spin)",
           "camera (RealSense, enumeration only)", "wrist camera (UVC)", "gamepad", "system", "software", "state dir")

print("A. all green")
rc, out, res, w = run()
counted = [r for r in res if not r.get("skipped")]
check("exit 0", rc == 0, f"rc {rc}")
check("summary N/N OK - ready to fly", last_line(out) == f"{len(counted)}/{len(counted)} OK - ready to fly", last_line(out))
check("no KO line at all", "  KO " not in out)
check("battery 11612 mV -> 11.61 V", line_of(out, "battery") == "OK  battery - 11.61 V", line_of(out, "battery"))
check("firmware version read from telemetry", "qtpy-mdd3a-v3" in line_of(out, "firmware version"))
check("firmware disarmed: mode 0", "mode 0 (off)" in line_of(out, "firmware disarmed"))
check("ticks L 160585 R 158263", "L 160585 R 158263" in line_of(out, "encoder ticks"))
check("driver absent -> informational OK with the build note",
      line_of(out, "motor driver") == "OK  motor driver - not reported (a firmware build older than the driver key); set MOSS_DRIVER in robot.env to make this a check",
      line_of(out, "motor driver"))
check("telemetry parsed across chunk boundaries (3 lines, banner ignored)",
      "3 line(s)" in line_of(out, "firmware telemetry"), line_of(out, "firmware telemetry"))
check("QT Py opened ONCE, at 115200, on the by-id path", w["opens"] == [(QTPY, 115200)], str(w["opens"]))
check("not one byte written to the firmware", w["written"] == [], str(w["written"]))
check("port closed after listening", w["closed"] == 1)
check("lidar probed once on the CP2102N path", w["lidar_calls"] == [C1], str(w["lidar_calls"]))
check("lidar 1500 points/s, 36/36 sectors", "1500 points/s, 36/36 sectors" in line_of(out, "lidar scan"))
check("RealSense on USB 3.2 with serial and firmware",
      "serial 000000000001 fw 5.17.0.10 USB 3.2" in line_of(out, "RealSense D455"))
check("disk 79.0 GB free", "79.0 GB free" in line_of(out, "disk for recordings"), line_of(out, "disk for recordings"))
check("RAM 6.1 GB", "6.1 GB" in line_of(out, "RAM available"))
check("rmem 212992 is a warning, never a KO",
      line_of(out, "socket buffers").startswith("OK") and "warning" in line_of(out, "socket buffers"))
check("lo without MULTICAST, passwordless sudo: OK, dimOS turns it on at launch",
      line_of(out, "loopback multicast") == "OK  loopback multicast - off - dimOS turns it on with sudo at launch",
      line_of(out, "loopback multicast"))
check("the multicast route is checked on its own line",
      line_of(out, "multicast route") == "OK  multicast route - 224.0.0.0/4 routed", line_of(out, "multicast route"))
check("pygame is one of the software imports, pyrealsense2 is not (the camera section owns it)",
      line_of(out, "import pygame").startswith("OK") and not line_of(out, "import pyrealsense2"))
check("the stack's moss_dimos comes from this checkout",
      line_of(out, "moss-dimos install") == "OK  moss-dimos install - the stack imports moss_dimos from this checkout",
      line_of(out, "moss-dimos install"))
check("the state dir and recordings/ were created", (w["state"] / "recordings").is_dir())
check("sections in the spec order",
      [r["section"].split(" ")[0] for r in res][:2] == ["robot.env", "stack"]
      and [out.find("\n" + h + "\n") for h in HEADERS] == sorted(out.find("\n" + h + "\n") for h in HEADERS)
      and -1 not in [out.find("\n" + h + "\n") for h in HEADERS])
rc, out, res, w = run(lo_flags=0x1009)
check("lo flags 0x1009 -> multicast on", line_of(out, "loopback multicast") == "OK  loopback multicast - on")

print("B. QT Py missing")
rc, out, res, w = run(files={C1, WRIST, "/dev/input/js0"})
check("exit 1", rc == 1, f"rc {rc}")
check("KO on the motor board with the fix", line_of(out, "motor board (QT Py)").startswith("KO")
      and "not on USB" in line_of(out, "motor board (QT Py)"))
check("summary names it", "KO: motor board (QT Py)" in last_line(out), last_line(out))
check("firmware skipped, the serial port never opened",
      w["opens"] == [] and "skipped: no free QT Py port" in line_of(out, "firmware telemetry"))
check("the lidar still checked on its own port", w["lidar_calls"] == [C1])

print("C. a stack already running")
STACK_CMD = "/home/x/moss/.venv/bin/python3 /home/x/moss/.venv/bin/dimos --rerun-open none run moss-dimos.moss-nav --daemon"
rc, out, res, w = run(runs=[("20260101-040000-moss-dimos-moss-nav", 4242)], alive={4242},
                      cmdlines=[(1, "/sbin/init"), (4242, STACK_CMD)])
check("stack verdict OK with run id and pid",
      line_of(out, "stack") == "OK  stack - 20260101-040000-moss-dimos-moss-nav pid 4242", line_of(out, "stack"))
fw, li = find(res, "firmware telemetry"), find(res, "lidar scan")
check("firmware SKIPPED: held by the stack",
      len(fw) == 1 and fw[0].get("skipped") and fw[0]["detail"].startswith("skipped: held by the stack"),
      fw[0]["detail"] if fw else "none")
check("lidar SKIPPED: held by the stack",
      len(li) == 1 and li[0].get("skipped") and li[0]["detail"].startswith("skipped: held by the stack"))
check("zero serial opens, zero lidar spins", w["opens"] == [] and w["lidar_calls"] == [])
check("no port-holder scan either (the stack holds them by design)", w["holder_calls"] == [])
check("exit 0 (a stack is not a hardware fault) and skips counted apart",
      rc == 0 and "(2 skipped)" in last_line(out), last_line(out))
rc, out, res, w = run(cmdlines=[(1, "/sbin/init"), (777, "/home/x/moss/.venv/bin/dimos --rerun-open none run moss-dimos.moss-nav --daemon")])
check("unregistered `bin/dimos run` process -> probes skipped too",
      "unregistered dimos run pid 777" in line_of(out, "stack") and w["opens"] == [] and w["lidar_calls"] == [],
      line_of(out, "stack"))
rc, out, res, w = run(cmdlines=[(1, "/sbin/init"), (778, "/home/x/moss/.venv/bin/python3 /home/x/moss/.venv/bin/dimos log"),
                                (779, "python3 tools/moss_cockpit.py --port 8904")])
check("`dimos log` and the cockpit are not a stack", line_of(out, "stack") == "OK  stack - none"
      and len(w["opens"]) == 1, line_of(out, "stack"))
rc, out, res, w = run(runs=[("20260101-155115-moss-dimos-moss-gamepad", 999)], alive=set())
check("dead registry pid = stale, not a stack: probes run",
      "none (1 stale registry entry)" in line_of(out, "stack") and len(w["opens"]) == 1 and w["lidar_calls"] == [C1],
      line_of(out, "stack"))

rc, out, res, w = run(runs=[("20260101-155115-moss-dimos-moss-gamepad", 818205)], alive={818205},
                      cmdlines=[(1, "/sbin/init"), (818205, "-bash")])
fw = find(res, "firmware telemetry")
check("registry pid alive but reused by a shell = stale, not a stack: battery read, lidar spun",
      "none (1 stale registry entry)" in line_of(out, "stack") and len(w["opens"]) == 1
      and w["lidar_calls"] == [C1] and len(fw) == 1 and not fw[0].get("skipped")
      and "11.61 V" in line_of(out, "battery"), line_of(out, "stack"))

print("D. battery (3S pack, INA219 voltage)")
for mv, want_ok, needle in ((10500, False, "10.50 V - under 10.8 V: the BMS cuts at 10.2 V under load"),
                            (10100, False, "10.10 V - under the BMS cut (10.2 V)"),
                            (10800, True, "10.80 V"),
                            (12600, True, "12.60 V")):
    rc, out, res, w = run(telemetry=dict(TELEMETRY, bus_mV=mv))
    ln = line_of(out, "battery")
    check(f"{mv} mV -> {'OK' if want_ok else 'KO'} '{needle}'",
          ln.startswith("OK" if want_ok else "KO") and needle in ln and rc == (0 if want_ok else 1), ln)
rc, out, res, w = run(telemetry=dict(TELEMETRY, ina_ok=False, bus_mV=None))
check("ina_ok false -> KO INA219 not seen", line_of(out, "battery").startswith("KO") and "INA219 not seen" in out)

print("E. gamepad diagnosis")
files_nopad = {QTPY, C1, WRIST}
rc, out, res, w = run(files=files_nopad, usb={"057e:2009", "239a:8119"})
check("057e:2009 -> the Nintendo sentence, as a warning (nothing refuses a missing pad)",
      "pad enumerated as a Nintendo Pro Controller (057e:2009) without a driver: switch the pad to its "
      "Android/X-input mode and replug" in line_of(out, "gamepad") and line_of(out, "gamepad").startswith("OK")
      and "WARN" in line_of(out, "gamepad"),
      line_of(out, "gamepad"))
rc, out, res, w = run(files=files_nopad, usb={"2563:0526"})
check("2563:0526 -> receiver visible, no js device", "receiver visible (2563:0526), no js device: replug or reboot" in line_of(out, "gamepad"))
rc, out, res, w = run(files=files_nopad, usb=set())
check("nothing -> no pad, still a warning", "no pad" in line_of(out, "gamepad") and line_of(out, "gamepad").startswith("OK"))
rc, out, res, w = run(files=files_nopad, usb=set(), env={"MOSS_REQUIRE_PAD": "1"})
check("MOSS_REQUIRE_PAD=1 -> no pad is a KO and the check fails", line_of(out, "gamepad").startswith("KO") and rc == 1)
rc, out, res, w = run(usb={"057e:2009"})
check("js0 present wins over any USB id", line_of(out, "gamepad").startswith("OK"))

# E2. the pad must be ALIVE and in the layout the stack will use (14 Oct: a mute dongle passed as OK;
#     the pad on its cable is an Xbox 360 pad with another button map)
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0"}, pad_axes={"/dev/input/js0": [-32767] * 8})
check("every axis at -32767 (never reported) -> KO MUTE with the cause",
      line_of(out, "gamepad").startswith("KO") and "MUTE" in line_of(out, "gamepad") and "not paired" in line_of(out, "gamepad"),
      line_of(out, "gamepad"))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js1"}, pad_names={"/dev/input/js1": "Microsoft X-Box 360 pad"},
                      pad_axes={"/dev/input/js1": [0, 0, -32767, 0, 0, -32767, 0, 0]})
check("Xbox pad (cable) with the default android layout -> KO, fix = MOSS_PAD_LAYOUT=xinput",
      line_of(out, "gamepad").startswith("KO") and "MOSS_PAD_LAYOUT=xinput" in line_of(out, "gamepad"), line_of(out, "gamepad"))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js1"}, pad_names={"/dev/input/js1": "Microsoft X-Box 360 pad"},
                      pad_axes={"/dev/input/js1": [0, 0, -32767, 0, 0, -32767, 0, 0]}, env={"MOSS_PAD_LAYOUT": "xinput"})
check("Xbox pad with MOSS_PAD_LAYOUT=xinput -> OK, alive, layout xinput",
      line_of(out, "gamepad").startswith("OK") and "layout xinput" in line_of(out, "gamepad"), line_of(out, "gamepad"))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0"}, env={"MOSS_PAD_LAYOUT": "xinput"})
check("dongle (shanwan) with MOSS_PAD_LAYOUT=xinput -> KO, fix = android",
      line_of(out, "gamepad").startswith("KO") and "MOSS_PAD_LAYOUT=android" in line_of(out, "gamepad"), line_of(out, "gamepad"))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0", "/dev/input/js1"},
                      pad_names={"/dev/input/js0": "shanwan Android GamePad", "/dev/input/js1": "Microsoft X-Box 360 pad"},
                      pad_axes={"/dev/input/js0": [-32767] * 8, "/dev/input/js1": [0, 0, -32767, 0, 0, -32767, 0, 0]},
                      env={"MOSS_PAD_LAYOUT": "xinput", "MOSS_PAD_INDEX": "1"})
check("two pads, MOSS_PAD_INDEX=1 -> the Xbox one is judged (OK), the mute dongle only listed",
      line_of(out, "gamepad").startswith("OK") and "js1:" in line_of(out, "gamepad") and "also plugged: js0" in line_of(out, "gamepad"),
      line_of(out, "gamepad"))
check("pad_verdict: cannot read -> KO", mp.pad_verdict("x", None, "android")[0] is False)

# E3. robot.env: read before the checks, the shell wins, the driver is checked against it
rc, out, res, w = run(robot_env="# MOSS robot\nMOSS_DRIVER=mdd10a\nexport MOSS_PAD_LAYOUT=\"xinput\"\n",
                      files={QTPY, C1, "/dev/input/js1"}, pad_names={"/dev/input/js1": "Microsoft X-Box 360 pad"},
                      pad_axes={"/dev/input/js1": [0, 0, -32767, 0, 0, -32767, 0, 0]})
check("robot.env line lists what it declared", "MOSS_DRIVER=mdd10a" in line_of(out, "robot.env") and "MOSS_PAD_LAYOUT=xinput" in line_of(out, "robot.env"),
      line_of(out, "robot.env"))
check("MOSS_PAD_LAYOUT from robot.env reaches the pad check (xinput -> OK)", line_of(out, "gamepad").startswith("OK"), line_of(out, "gamepad"))
check("firmware without a driver key, robot.env expects mdd10a -> KO with the reflash line",
      line_of(out, "motor driver").startswith("KO") and "reflash the mdd10a build" in line_of(out, "motor driver"), line_of(out, "motor driver"))
rc, out, res, w = run(robot_env="MOSS_DRIVER=mdd10a\n", telemetry=dict(TELEMETRY, driver="mdd10a"))
check("firmware driver = MOSS_DRIVER -> OK", line_of(out, "motor driver").startswith("OK") and "= MOSS_DRIVER" in line_of(out, "motor driver"), line_of(out, "motor driver"))
rc, out, res, w = run(robot_env="MOSS_DRIVER=mdd10a\n", telemetry=dict(TELEMETRY, driver="mdd3a"))
check("firmware mdd3a, robot.env mdd10a -> KO naming both", line_of(out, "motor driver").startswith("KO") and "built for mdd3a" in line_of(out, "motor driver"), line_of(out, "motor driver"))
rc, out, res, w = run(robot_env="MOSS_DRIVER=mdd3a\n", env={"MOSS_DRIVER": "mdd10a"}, telemetry=dict(TELEMETRY, driver="mdd10a"))
check("the shell's MOSS_DRIVER wins over robot.env", line_of(out, "motor driver").startswith("OK"), line_of(out, "motor driver"))
rc, out, res, w = run()
check("no robot.env, no driver key -> informative OK that says how to make it a check",
      line_of(out, "motor driver").startswith("OK") and "set MOSS_DRIVER in robot.env" in line_of(out, "motor driver"), line_of(out, "motor driver"))
check("load_robot_env: comments, export, quotes, junk", mp.load_robot_env("# c\nexport A=\"1 2\"\nB='x'\nnot a pair\nlower=3\nC=\n") == {"A": "1 2", "B": "x", "C": ""})
check("driver_verdict pure: expected set and nothing reported -> KO", mp.driver_verdict("mdd10a", None) == (False, "not reported, robot.env expects mdd10a: reflash the mdd10a build (bench/README.md)"))

rc, out, res, w = run(telemetry=dict(TELEMETRY, stop_open=False, stop_latched=False))
check("closed two-wire stop loop -> OK", line_of(out, "track stop button").startswith("OK"), line_of(out, "track stop button"))
rc, out, res, w = run(telemetry=dict(TELEMETRY, stop_open=True, stop_latched=True))
check("open two-wire stop loop -> KO without writing to serial", line_of(out, "track stop button").startswith("KO") and "open NC loop" in line_of(out, "track stop button"), line_of(out, "track stop button"))
rc, out, res, w = run(telemetry=dict(TELEMETRY, stop_open=False, stop_latched=True))
check("released but latched stop -> KO with explicit clearstop instruction", line_of(out, "track stop button").startswith("KO") and "clearstop" in line_of(out, "track stop button"), line_of(out, "track stop button"))
rc, out, res, w = run(telemetry=dict(TELEMETRY, stop_open="false", stop_latched=False))
check("malformed stop telemetry -> KO", line_of(out, "track stop button").startswith("KO") and "malformed" in line_of(out, "track stop button"), line_of(out, "track stop button"))

print("F. --json")
rc, out, res, w = run(["--json"], telemetry=dict(TELEMETRY, bus_mV=10500))
try:
    doc = json.loads(out)
    parsed = True
except ValueError as exc:
    doc, parsed = {}, False
    print("   ", exc, out[:200])
check("stdout is exactly one JSON document", parsed)
checks = doc.get("checks", [])
counted = [c for c in checks if not c.get("skipped")]
check("keys ts, checks, ok_count, ko_count, summary",
      all(k in doc for k in ("ts", "checks", "ok_count", "ko_count", "summary")))
check("each check has ok, label, detail, section",
      bool(checks) and all(set(("ok", "label", "detail", "section")) <= set(c) for c in checks))
check("ok_count / ko_count match the checks",
      doc.get("ok_count") == sum(1 for c in counted if c["ok"]) and doc.get("ko_count") == sum(1 for c in counted if not c["ok"])
      and doc.get("ko_count") == 1, f"{doc.get('ok_count')} / {doc.get('ko_count')}")
check("summary carries the KO label", doc.get("summary", "").endswith("KO: battery"), doc.get("summary"))
check("exit 1 with a KO in JSON mode too", rc == 1)
check("ts is now", abs(doc.get("ts", 0) - time.time()) < 60)

print("G. --quick and --no-spin")
rc, out, res, w = run(["--quick"])
check("--quick: the serial stub is never called", w["opens"] == [])
check("--quick: the lidar stub is never called", w["lidar_calls"] == [])
check("--quick: both reported skipped, exit 0",
      rc == 0 and "skipped: --quick" in line_of(out, "firmware telemetry") and "skipped" in line_of(out, "lidar scan"))
rc, out, res, w = run(["--no-spin"])
check("--no-spin: the firmware IS listened to (battery judged)", len(w["opens"]) == 1 and "11.61 V" in out)
check("--no-spin: the lidar never spins", w["lidar_calls"] == [])

print("H. firmware and port faults")
rc, out, res, w = run(holders={QTPY: [3131]})
check("QT Py held by pid 3131 -> KO naming it", "held by pid 3131" in line_of(out, "motor board (QT Py) free")
      and rc == 1, line_of(out, "motor board (QT Py) free"))
check("... and the firmware is never opened against it", w["opens"] == [])
rc, out, res, w = run(telemetry=dict(TELEMETRY, mode=2, reason="drive"))
check("mode 2 -> KO firmware disarmed with the reason",
      line_of(out, "firmware disarmed") == "KO  firmware disarmed - mode 2 (drive) - something else is driving it",
      line_of(out, "firmware disarmed"))
rc, out, res, w = run(serial_chunks=[b"", b"garbage\n"])
check("mute firmware -> KO, no further firmware verdict",
      line_of(out, "firmware telemetry").startswith("KO") and "mute" in out and not find(res, "battery"))
rc, out, res, w = run(telemetry=dict(TELEMETRY, driver="mdd10a"))
check("driver reported -> shown (informative without MOSS_DRIVER)", line_of(out, "motor driver").startswith("OK  motor driver - mdd10a; set MOSS_DRIVER"))
rc, out, res, w = run(realsense=[dict(D455, usb="2.1")])
check("RealSense on USB 2.1 -> KO 5 fps max", "on USB 2: 5 fps max" in line_of(out, "RealSense D455")
      and line_of(out, "RealSense D455").startswith("KO"))
rc, out, res, w = run(realsense=[])
check("camera on, no D455 -> KO with both fixes (USB 3, or MOSS_CAMERA=0)",
      line_of(out, "RealSense D455").startswith("KO") and "MOSS_CAMERA=0" in line_of(out, "RealSense D455") and rc == 1,
      line_of(out, "RealSense D455"))
rc, out, res, w = run(env={"MOSS_PORT": C1})
check("MOSS_PORT pointing at the lidar -> KO, and the lidar is never written as a motor port",
      line_of(out, "motor port is not the lidar").startswith("KO") and w["opens"] == [], line_of(out, "motor port is not the lidar"))
rc, out, res, w = run(lidar=dict(default_world()["lidar"], sectors=31, points_per_s=1400.0))
check("31/36 sectors -> KO lidar scan", line_of(out, "lidar scan").startswith("KO") and "31/36" in out)
rc, out, res, w = run(lidar_exc=RuntimeError("no descriptor for a550"))
check("lidar mute -> KO with the exception", "no descriptor for a550" in line_of(out, "lidar answers")
      and line_of(out, "lidar answers").startswith("KO"))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0"})
check("wrist camera absent -> OK with a warning (the stack runs without wrist_image)",
      line_of(out, "wrist camera").startswith("OK") and "WARN" in line_of(out, "wrist camera")
      and "without wrist_image" in line_of(out, "wrist camera"), line_of(out, "wrist camera"))
rc, out, res, w = run(free_gb=3.2, mem_kb=1_900_000)
check("3.2 GB free -> KO disk; 1.9 GB RAM -> KO", "3.2 GB free" in line_of(out, "disk for recordings")
      and line_of(out, "disk for recordings").startswith("KO") and line_of(out, "RAM available").startswith("KO"))

print("H2. the MOSS_* switches, read as the stack reads them")
NO_RS = ImportError("No module named 'pyrealsense2'")
for val in ("0", "off", " No "):
    rc, out, res, w = run(realsense_exc=NO_RS, imports_missing={"pyrealsense2"}, env={"MOSS_CAMERA": val})
    rs = find(res, "RealSense")
    check(f"MOSS_CAMERA={val!r}, no pyrealsense2 -> RealSense skipped, never probed, exit 0",
          rc == 0 and len(rs) == 1 and rs[0].get("skipped") and "this flight builds no RealSense" in rs[0]["detail"]
          and w["realsense_calls"] == 0 and "  KO " not in out, f"rc {rc} {line_of(out, 'RealSense')}")
rc, out, res, w = run(realsense_exc=NO_RS, imports_missing={"pyrealsense2"})
check("MOSS_CAMERA unset, no pyrealsense2 -> KO RealSense with the install / MOSS_CAMERA=0 fix, exit 1",
      rc == 1 and line_of(out, "RealSense").startswith("KO") and "pyrealsense2 not importable" in line_of(out, "RealSense")
      and "MOSS_CAMERA=0" in line_of(out, "RealSense") and last_line(out).endswith("KO: RealSense"),
      f"rc {rc} {last_line(out)}")
rc, out, res, w = run(realsense_exc=NO_RS, env={"MOSS_CAMERA": "1"})
check("MOSS_CAMERA=1 -> the same KO", rc == 1 and line_of(out, "RealSense").startswith("KO"))
RS_V4L = "/dev/v4l/by-id/usb-Intel_R_RealSense_TM_Depth_Camera_455f_000000000000-video-index0"
OTHER_CAM = "/dev/v4l/by-id/usb-Generic_Vendor_USB_Camera_XYZ-video-index0"
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0", RS_V4L, OTHER_CAM})
check("an unknown UVC camera next to the RealSense is reported as the wrist camera",
      any(r["label"] == "wrist camera" and r["ok"] and OTHER_CAM in r["detail"] for r in res), str([r for r in res if r["label"] == "wrist camera"]))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0", RS_V4L})
check("only the RealSense under by-id -> wrist camera WARN (never the nose camera)",
      any(r["label"] == "wrist camera" and r["ok"] and "WARN" in r["detail"] for r in res), str([r for r in res if r["label"] == "wrist camera"]))
rc, out, res, w = run(files={QTPY, C1, "/dev/input/js0"}, env={"MOSS_WRIST": "false"})
wr = find(res, "wrist camera")
check("MOSS_WRIST=false -> wrist camera skipped (the stack builds none)",
      len(wr) == 1 and wr[0].get("skipped") and "MOSS_WRIST=false" in wr[0]["detail"] and rc == 0, line_of(out, "wrist camera"))
rc, out, res, w = run(files={C1, WRIST, "/dev/input/js0"}, env={"MOSS_MOCK_BUS": "y"})
check("MOSS_MOCK_BUS=y mocks the bus as the adapter does: no QT Py needed, never opened, exit 0",
      rc == 0 and "MOSS_MOCK_BUS=y: fake firmware" in line_of(out, "motor board (QT Py)") and w["opens"] == [],
      line_of(out, "motor board (QT Py)"))
rc, out, res, w = run(files={C1, WRIST, "/dev/input/js0"}, env={"MOSS_MOCK_BUS": "off"})
check("MOSS_MOCK_BUS=off -> the real board is required (KO without it)",
      rc == 1 and line_of(out, "motor board (QT Py)").startswith("KO"), line_of(out, "motor board (QT Py)"))
rc, out, res, w = run(files={QTPY, C1, WRIST}, usb=set(), env={"MOSS_REQUIRE_PAD": "yes"})
check("MOSS_REQUIRE_PAD=yes -> no pad is a KO", rc == 1 and line_of(out, "gamepad").startswith("KO"))
rc, out, res, w = run(files={QTPY, C1, WRIST}, usb=set(), env={"MOSS_REQUIRE_PAD": "0"})
check("MOSS_REQUIRE_PAD=0 -> no pad stays a warning", rc == 0 and line_of(out, "gamepad").startswith("OK"))

print("I. software and env")
rc, out, res, w = run()
check("robot profile: the MOSS geometry, lethal 0.22 m",
      line_of(out, "robot profile") == "OK  robot profile - moss: width 0.34 m, pivot 0.5 m, lidar 0.2 m up, "
      "lethal 0.22 m (placeholders until measured)", line_of(out, "robot profile"))
check("blueprints registered under the moss-dimos namespace",
      line_of(out, "blueprint moss-nav") == "OK  blueprint moss-nav - registered as moss-dimos.moss-nav",
      line_of(out, "blueprint moss-nav"))
rc, out, res, w = run(profile_exc=ValueError("MOSS_ROBOT_WIDTH_M: not a number"))
check("a profile that fails -> KO robot profile with the reason",
      line_of(out, "robot profile") == "KO  robot profile - ValueError: MOSS_ROBOT_WIDTH_M: not a number" and rc == 1,
      line_of(out, "robot profile"))
rc, out, res, w = run(entry_points={"moss-gamepad", "moss-base"})
nav = line_of(out, "blueprint moss-nav")
check("moss-nav / moss-explore missing -> KO with the reinstall line for this checkout",
      nav.startswith("KO") and "missing from moss-dimos" in nav
      and f"reinstall in {ROOT}: uv pip install --python .venv/bin/python -e . --no-deps" in nav
      and ".venv/bin/pip install -e . --no-deps" in nav
      and line_of(out, "blueprint moss-explore").startswith("KO") and line_of(out, "blueprint moss-gamepad").startswith("OK"),
      nav)
rc, out, res, w = run(imports_missing={"kiss_icp"})
check("kiss_icp missing -> KO import kiss_icp", line_of(out, "import kiss_icp").startswith("KO"))
rc, out, res, w = run(imports_missing={"pygame"})
check("pygame missing -> KO import pygame, named in the summary, exit 1 (nothing would drive)",
      line_of(out, "import pygame").startswith("KO") and "KO: import pygame" in last_line(out) and rc == 1,
      last_line(out))
rc, out, res, w = run(module_file=None)
check("moss_dimos not importable in the venv -> KO with the install line",
      line_of(out, "moss-dimos install").startswith("KO") and "does not import" in line_of(out, "moss-dimos install")
      and "uv pip install --python .venv/bin/python -e . --no-deps" in line_of(out, "moss-dimos install") and rc == 1,
      line_of(out, "moss-dimos install"))
rc, out, res, w = run(module_file="/srv/old_checkout/moss_dimos/__init__.py")
check("the venv imports moss_dimos from another checkout -> KO naming it, reinstall here",
      line_of(out, "moss-dimos install").startswith("KO") and "/srv/old_checkout/moss_dimos" in line_of(out, "moss-dimos install")
      and f"reinstall in {ROOT}" in line_of(out, "moss-dimos install") and rc == 1, line_of(out, "moss-dimos install"))
rc, out, res, w = run(files={C1, WRIST, "/dev/input/js0"}, env={"MOSS_MOCK_BUS": "1"})
check("MOSS_MOCK_BUS=1: no QT Py needed, firmware skipped, exit 0",
      rc == 0 and "MOSS_MOCK_BUS=1" in line_of(out, "motor board (QT Py)") and w["opens"] == [], last_line(out))

print("J. --save (the document the cockpit serves)")
target = TMPD / "saved" / "preflight.json"
rc, out, res, w = run(["--save", str(target)])
try:
    saved = json.loads(target.read_text())
except (OSError, ValueError):
    saved = {}
check("file written, human lines still on stdout", bool(saved) and "ready to fly" in last_line(out))
check("same checks and counts as the run", saved.get("ok_count") == len([r for r in res if not r.get("skipped")])
      and saved.get("ko_count") == 0 and len(saved.get("checks", [])) == len(res))
check("no .tmp left behind", not (target.parent / "preflight.json.tmp").exists())

print("L. LCM system settings (what dimOS sets with sudo at launch)")
FIX = "install tools/lcm-loopback.service to set it at boot"
rc, out, res, w = run(sudo=False)
check("lo multicast off and no passwordless sudo -> KO with the boot unit, exit 1",
      line_of(out, "loopback multicast").startswith("KO") and FIX in line_of(out, "loopback multicast")
      and "dimOS cannot turn it on at launch" in line_of(out, "loopback multicast") and rc == 1 and w["sudo_calls"] == 1,
      line_of(out, "loopback multicast"))
check("... rmem low without sudo stays a warning (dimOS treats the buffers as optional)",
      line_of(out, "socket buffers").startswith("OK") and "warning" in line_of(out, "socket buffers")
      and FIX in line_of(out, "socket buffers"), line_of(out, "socket buffers"))
rc, out, res, w = run(sudo=False, lo_flags=0x1009, route=False, rmem="67108864")
check("route missing and no sudo -> KO multicast route, lo on is OK",
      line_of(out, "multicast route").startswith("KO") and "no 224.0.0.0/4 route" in line_of(out, "multicast route")
      and line_of(out, "loopback multicast") == "OK  loopback multicast - on" and rc == 1, line_of(out, "multicast route"))
rc, out, res, w = run(sudo=True, lo_flags=0x1009, route=False)
check("route missing with passwordless sudo -> OK, dimOS adds it",
      line_of(out, "multicast route") == "OK  multicast route - no 224.0.0.0/4 route - dimOS adds it on lo with sudo at launch"
      and rc == 0, line_of(out, "multicast route"))
rc, out, res, w = run(route=None, lo_flags=0x1009, rmem="67108864")
check("`ip` cannot run -> KO multicast route", line_of(out, "multicast route").startswith("KO")
      and "iproute2" in line_of(out, "multicast route") and rc == 1, line_of(out, "multicast route"))
rc, out, res, w = run(sudo=False, lo_flags=0x1009, route=True, rmem="67108864")
check("everything set at boot -> all OK and sudo never even probed",
      rc == 0 and w["sudo_calls"] == 0 and line_of(out, "socket buffers") == "OK  socket buffers - rmem_max 67108864"
      and line_of(out, "loopback multicast") == "OK  loopback multicast - on", f"rc {rc} sudo calls {w['sudo_calls']}")

print("K. the real probes, on this machine (no device opened)")
import importlib  # noqa: E402
real = importlib.reload(mp)
real_runs_dir = real._runs_dir     # the real one: a case below replaces it on the module
held = TMPD / "held_port"
held.write_text("x")
child = subprocess.Popen([sys.executable, "-c",
                          f"import time; f = open({str(held)!r}); print('ready', flush=True); time.sleep(20)"],
                         stdout=subprocess.PIPE, text=True)
child.stdout.readline()
try:
    holders = real._port_holders(str(held))
    check("/proc fd scan finds the child holding the file", child.pid in holders, f"{holders} vs {child.pid}")
    check("... and never reports this process", os.getpid() not in holders)
finally:
    child.kill()
    child.wait()
check("nobody holds it once the child is gone", real._port_holders(str(held)) == [])
ids = real._usb_devices()
check("sysfs USB ids look like vvvv:pppp", all(len(i) == 9 and i[4] == ":" for i in ids), f"{len(ids)} devices")
check("our own cmdline is in the /proc scan", any(pid == os.getpid() and "bench_moss_preflight_cold" in cmd
                                                  for pid, cmd in real._proc_cmdlines()))
check("lo flags read as an int (or None off Linux)", real._lo_flags() is None or isinstance(real._lo_flags(), int))
check("nothing ran at import (RESULTS empty after reload)", real.RESULTS == [])
# a registry entry naming a LIVE pid that is not dimos (pid reuse after a reboot)
reused = subprocess.Popen([sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(20)"],
                          stdout=subprocess.PIPE, text=True)
reused.stdout.readline()
try:
    real_runs = TMPD / "real_runs"
    real_runs.mkdir()
    (real_runs / "20260101-155115-moss-dimos-moss-gamepad.json").write_text(json.dumps(
        {"run_id": "20260101-155115-moss-dimos-moss-gamepad", "pid": reused.pid}))
    real._runs_dir = lambda: real_runs
    ctx = {}
    with contextlib.redirect_stdout(io.StringIO()) as sbuf:
        real.check_stack(ctx)
    check("real /proc: a registry pid that is alive but not `dimos run` is stale, not a stack",
          real._pid_alive(reused.pid) and f"pid {reused.pid}" not in (ctx.get("stack") or "")
          and "1 stale registry entry" in sbuf.getvalue(),
          sbuf.getvalue().strip())
finally:
    reused.kill()
    reused.wait()

# Entry points through the real importlib.metadata: two installed distributions
# register blueprints in a private group; only the one named moss-dimos (any
# spelling that canonicalizes to it) counts, as `dimos run moss-dimos.<name>` does.
site = TMPD / "fake_site"
for dist_dir, name, eps in (("Moss_Dimos-0.1.0.dist-info", "Moss_Dimos",
                             ("moss-nav = moss_dimos.blueprints:moss_nav_blueprint",
                              "moss-base = moss_dimos.blueprints:moss_base_blueprint")),
                            ("other_dimos-0.0.1.dist-info", "other-dimos",
                             ("moss-explore = other_dimos.blueprints:explore",
                              "moss-nav = other_dimos.blueprints:nav"))):
    (site / dist_dir).mkdir(parents=True)
    (site / dist_dir / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.0.1\n")
    (site / dist_dir / "entry_points.txt").write_text("[moss.bench.blueprints]\n" + "\n".join(eps) + "\n")
sys.path.insert(0, str(site))
try:
    got = real._entry_points("moss.bench.blueprints")
finally:
    sys.path.remove(str(site))
check("real entry points: moss-nav + moss-base from Moss_Dimos; other-dimos's moss-explore ignored",
      got == {"moss-nav", "moss-base"}, str(sorted(got)))
# The same metadata found in the checkout itself (the egg-info an editable
# install leaves there) is not on the stack's path: it never counts.
real_root = real.ROOT
real.ROOT = site.resolve()
sys.path.insert(0, str(site))
try:
    got_root = real._entry_points("moss.bench.blueprints")
finally:
    sys.path.remove(str(site))
    real.ROOT = real_root
check("real entry points: metadata sitting in the checkout itself is ignored", got_root == set(), str(sorted(got_root)))

# The run registry follows XDG_STATE_HOME, as dimOS, moss-fly.sh and the cockpit do.
old_xdg = os.environ.get("XDG_STATE_HOME")
try:
    os.environ["XDG_STATE_HOME"] = str(TMPD / "xdg")
    rd_xdg = real_runs_dir()
    os.environ["XDG_STATE_HOME"] = ""
    rd_empty = real_runs_dir()
    os.environ.pop("XDG_STATE_HOME")
    rd_home = real_runs_dir()
finally:
    if old_xdg is None:
        os.environ.pop("XDG_STATE_HOME", None)
    else:
        os.environ["XDG_STATE_HOME"] = old_xdg
check("real registry dir: XDG_STATE_HOME=<tmp>/xdg -> <tmp>/xdg/dimos/runs", rd_xdg == TMPD / "xdg" / "dimos" / "runs", str(rd_xdg))
check("... unset or empty -> ~/.local/state/dimos/runs",
      rd_home == rd_empty == Path.home() / ".local" / "state" / "dimos" / "runs", f"{rd_home} / {rd_empty}")

# Where a fresh interpreter of this venv imports moss_dimos from (as the stack would).
other = TMPD / "other_checkout"
(other / "moss_dimos").mkdir(parents=True)
(other / "moss_dimos" / "__init__.py").write_text('"""another checkout"""\n')
old_pp = os.environ.get("PYTHONPATH")
try:
    os.environ["PYTHONPATH"] = str(ROOT)
    mf_here = real._module_file()
    os.environ["PYTHONPATH"] = str(other)
    mf_other = real._module_file()
finally:
    if old_pp is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = old_pp
check("real module probe: this checkout on the path -> moss_dimos from this checkout",
      mf_here is not None and Path(mf_here).resolve() == ROOT / "moss_dimos" / "__init__.py", str(mf_here))
check("... another checkout first on the path -> that one is reported",
      mf_other is not None and Path(mf_other).resolve() == (other / "moss_dimos" / "__init__.py").resolve(), str(mf_other))

# pygame's import banner never reaches stdout (where --json writes its document).
probe = subprocess.run(
    [sys.executable, "-c",
     "import sys; sys.path.insert(0, 'tools'); import moss_preflight as m\n"
     "m.SOFTWARE_IMPORTS = ('pygame',); m._entry_points = lambda group='': set()\n"
     "m._module_file = lambda: None; m._QUIET[0] = True\n"
     "m._robot_profile = lambda: (_ for _ in ()).throw(RuntimeError('not needed'))\n"
     "m.check_software({})\n"
     "sys.stderr.write('pygame ' + ('OK' if m.RESULTS[0]['ok'] else 'missing') + '\\n')\n"],
    cwd=ROOT, env={k: v for k, v in os.environ.items() if k != "PYGAME_HIDE_SUPPORT_PROMPT"},
    capture_output=True, text=True, timeout=120)
if "pygame missing" in probe.stderr:
    print("  --  pygame is not installed here: the banner check is skipped")
else:
    check("real pygame import through the flight check: nothing on stdout",
          probe.returncode == 0 and probe.stdout == "" and "pygame OK" in probe.stderr,
          (probe.stdout or probe.stderr).strip()[-160:])

# The state dir as the recorder resolves it: a relative MOSS_STATE_DIR is made absolute.
old_state = os.environ.get("MOSS_STATE_DIR")
os.environ["MOSS_STATE_DIR"] = "rel/moss_state"
try:
    sd = real._state_dir()
finally:
    if old_state is None:
        os.environ.pop("MOSS_STATE_DIR", None)
    else:
        os.environ["MOSS_STATE_DIR"] = old_state
check("MOSS_STATE_DIR=rel/moss_state -> <cwd>/rel/moss_state (absolute, as the recorder)",
      sd == Path.cwd() / "rel" / "moss_state" and sd.is_absolute(), str(sd))

print(f"{OK} OK, {KO} KO")
print("TEST PASSED" if KO == 0 else "TEST FAILED")
sys.exit(1 if KO else 0)
