#!/usr/bin/env python3
"""MOSS flight check: every organ the MOSS stack needs, probed read-only, one verdict each.

Runs on the robot, from the root of this checkout, before a stack is launched
(and by `tools/moss-fly.sh check` and the launcher's gate 1):

    .venv/bin/python tools/moss_preflight.py            the whole check (the lidar spins ~5 s)
    .venv/bin/python tools/moss_preflight.py --no-spin  everything but the lidar spin
    .venv/bin/python tools/moss_preflight.py --quick    no lidar spin, no firmware listen
    .venv/bin/python tools/moss_preflight.py --json     one JSON document on stdout instead of lines
    ... --save <file>                                    also write that JSON document to <file>

Sections, in order: stack, ports, firmware, lidar, camera (RealSense), wrist
camera, gamepad, system, software, state dir. One line per probe,
"  OK |KO  label - detail", a summary "N/M OK - ready to fly" or
"N/M OK - KO: a, b", exit 1 on any KO.

Read-only by construction:
- the motor board (QT Py) is opened only when no dimOS stack runs and no other
  process holds it, exactly as tools/moss-teleop.sh gate 3 does: a plain open at
  115200 (DTR asserted, which the firmware needs before it streams), 1.5 s of
  listening, not one byte written. The firmware stays disarmed;
- the lidar is opened under the same conditions; it spins for a few seconds and
  is stopped again (C1Scanner.close sends STOP);
- the RealSense is enumerated, never streamed;
- sudo is only asked whether it would run without a password (`sudo -n true`),
  and only when dimOS would need it at launch (loopback multicast, its route
  or the socket buffers not set yet). It runs nothing as root.
The one thing it may create is the MOSS state dir (and its recordings/).

The MOSS_* on/off switches (MOSS_CAMERA, MOSS_WRIST, MOSS_MOCK_BUS,
MOSS_REQUIRE_PAD) are read the way the stack reads them
(moss_dimos.robot_profile.env_on): unset or empty = the default, 0 / false /
no / off = off, anything else = on. A camera switched off is skipped here, as
the stack skips it.

A check that cannot run because a stack owns the device is reported as skipped
("held by the stack"), never as a failure and never by fighting the stack for
the port: two readers on one serial line corrupt each other's frames.

Every probe is a module-level function so benches/bench_moss_preflight_cold.py
can replace it; nothing runs at import.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import importlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BYID_DIR = "/dev/serial/by-id"
V4L_DIR = "/dev/v4l/by-id"
JS_PATH = "/dev/input/js0"
QTPY_GLOB = "*QT_Py*"
C1_GLOB = "*CP2102N*"
WRIST_GLOBS = ("*KD-USB*-video-index0", "*Sonix*-video-index0")   # known arm cameras first
WRIST_ANY_GLOB = "*-video-index0"                                   # then any other UVC camera...
WRIST_NOT = ("realsense",)                                          # ...except the nose camera
FIRMWARE_BAUD = 115200
LISTEN_S = 1.5              # five telemetry lines at the firmware's 200 ms period
LIDAR_TURNS = 3
LIDAR_MIN_PPS = 200.0       # the C1 gives ~1500 points/s; 200 = a scan that is barely alive
BATTERY_FLOOR_MV = 10800    # launcher floor (moss-teleop.sh gate 3): margin above the cut under load
BMS_CUT_MV = 10200          # the 3S pack's BMS cuts here
DISK_MIN_GB = 5.0
RAM_MIN_KB = 2.5e6
RMEM_TARGET = 67_108_864    # what dimOS's LCM buffer configurator asks for
IFF_MULTICAST = 0x1000
MCAST_PREFIX = "224.0.0.0/4"   # the route dimOS's LCM multicast configurator checks
PAD_SHANWAN = "2563:0526"
PAD_SWITCH_PRO = "057e:2009"
MOSS_BLUEPRINTS = ("moss-nav", "moss-explore", "moss-gamepad")
DISTRIBUTION = "moss-dimos"     # the blueprint namespace: dimos run moss-dimos.<name>
# pyrealsense2 is not here: the camera section checks it, and only when the camera is on.
SOFTWARE_IMPORTS = ("dimos", "kiss_icp", "serial", "numpy", "pygame")
REINSTALL = ("uv pip install --python .venv/bin/python -e . --no-deps"
             " (a venv made with python -m venv: .venv/bin/pip install -e . --no-deps)")
LCM_FIX = ("install tools/lcm-loopback.service to set it at boot (docs/cockpit.md),"
           " or give this user passwordless sudo")

RESULTS: list[dict] = []
_SECTION = [""]
_QUIET = [False]


# ── output ─────────────────────────────────────────────────────────────────
def _say(text: str) -> None:
    if not _QUIET[0]:
        print(text, flush=True)


def section(name: str) -> None:
    _SECTION[0] = name
    _say(name)


def verdict(ok: bool, label: str, detail: str = "") -> None:
    RESULTS.append({"ok": bool(ok), "label": label, "detail": detail, "section": _SECTION[0]})
    _say(f"  {'OK ' if ok else 'KO '} {label}" + (f" - {detail}" if detail else ""))


def skipped(label: str, why: str) -> None:
    """A probe deliberately not run: not a failure, not counted in N/M."""
    RESULTS.append({"ok": True, "skipped": True, "label": label,
                    "detail": f"skipped: {why}", "section": _SECTION[0]})
    _say(f"  --  {label} - skipped: {why}")


# ── probes (each one replaced by the cold bench) ─────────────────────────────
def _ls(pattern: str) -> list[str]:
    return sorted(glob.glob(pattern))


def _exists(path: str) -> bool:
    return os.path.exists(path)


def _read_text(path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def _pad_name(js: str) -> str:
    try:
        return Path(f"/sys/class/input/{os.path.basename(js)}/device/name").read_text(encoding="utf-8").strip()
    except OSError:
        return os.path.basename(js)


def _pad_init_axes(js: str, listen_s: float = 1.0) -> list[int] | None:
    """The joystick API's initial axis values (events flagged 0x80 on open): a pad the receiver has
    never heard reports every axis at -32767; a live pad at rest reports its sticks at 0."""
    import select
    import struct

    fmt, size = "IhBB", struct.calcsize("IhBB")
    try:
        fd = os.open(js, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None
    axes: dict[int, int] = {}
    try:
        deadline = time.monotonic() + listen_s
        while time.monotonic() < deadline:
            r, _, _ = select.select([fd], [], [], 0.1)
            if not r:
                if axes:
                    break
                continue
            try:
                data = os.read(fd, size * 64)
            except OSError:
                break
            for i in range(0, len(data) - size + 1, size):
                _, value, typ, num = struct.unpack(fmt, data[i:i + size])
                if typ & 0x80 and typ & 0x02:
                    axes[num] = value
    finally:
        os.close(fd)
    return [axes[k] for k in sorted(axes)]


def _runs_dir() -> Path:
    """dimOS's run registry, where dimOS, tools/moss-fly.sh and the cockpit
    look for it (XDG_STATE_HOME when set and not empty)."""
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "dimos" / "runs"


def _pid_alive(pid: int) -> bool:
    return pid > 0 and os.path.exists(f"/proc/{pid}")


def _proc_cmdlines() -> list[tuple[int, str]]:
    """(pid, cmdline with NULs as spaces) for every readable process. Each read
    is guarded: a process that exits between listdir and open is normal."""
    out = []
    try:
        pids = os.listdir("/proc")
    except OSError:
        return out
    for pid in pids:
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                raw = f.read()
        except OSError:
            continue
        out.append((int(pid), raw.replace(b"\0", b" ").decode(errors="replace").strip()))
    return out


def _port_holders(dev: str) -> list[int]:
    """PIDs with `dev` open, from /proc/*/fd (no sudo: fds of other users'
    processes are unreadable and skipped - every MOSS process runs as us)."""
    real = os.path.realpath(dev)
    me = os.getpid()
    holders = []
    try:
        pids = os.listdir("/proc")
    except OSError:
        return holders
    for pid in pids:
        if not pid.isdigit() or int(pid) == me:
            continue
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                try:
                    if os.readlink(f"/proc/{pid}/fd/{fd}") == real:
                        holders.append(int(pid))
                        break
                except OSError:
                    continue
        except OSError:
            continue
    return holders


def _open_serial(port: str, baud: int):
    """A plain pyserial open, as moss-teleop.sh gate 3: DTR is asserted on open
    (the QT Py's USB CDC only streams to a host holding DTR), and this exact
    open does not reset the board."""
    import serial

    return serial.Serial(port, baud, timeout=0.05)


def _usb_devices() -> set[str]:
    """'vvvv:pppp' of every enumerated USB device, from sysfs (no lsusb needed)."""
    out = set()
    for d in glob.glob("/sys/bus/usb/devices/*"):
        try:
            vid = Path(d, "idVendor").read_text().strip()
            pid = Path(d, "idProduct").read_text().strip()
        except OSError:
            continue
        out.add(f"{vid}:{pid}".lower())
    return out


def _statvfs(path: str):
    return os.statvfs(path)


def _meminfo() -> dict[str, int]:
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k] = int(v.split()[0])
    return info


def _sysctl(name: str) -> str | None:
    try:
        return Path("/proc/sys", *name.split(".")).read_text().strip()
    except OSError:
        return None


def _lo_flags() -> int | None:
    try:
        return int(Path("/sys/class/net/lo/flags").read_text().strip(), 16)
    except (OSError, ValueError):
        return None


def _mcast_route() -> bool | None:
    """Whether 224.0.0.0/4 has a route, as dimOS checks it (`ip -o route show`
    prints something). None when `ip` cannot run."""
    try:
        r = subprocess.run(["ip", "-o", "route", "show", MCAST_PREFIX],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(r.stdout.strip()) if r.returncode == 0 else None


def _sudo_ok() -> bool:
    """Whether dimOS could fix the system settings itself at launch: root, or
    sudo without a password. `sudo -n true` never prompts and changes nothing."""
    if os.geteuid() == 0:
        return True
    try:
        return subprocess.run(["sudo", "-n", "true"], stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _lidar_probe(port: str) -> dict:
    """Info, health and LIDAR_TURNS turns, then STOP (C1Scanner.close)."""
    from moss_dimos.c1_serial import C1Scanner

    lidar = C1Scanner(port, baudrate=460800, timeout=3)
    try:
        lidar.open()
        info = lidar.info()
        health = lidar.health()
        sectors: set[int] = set()
        n = turns = 0
        t0 = time.monotonic()
        for scan in lidar.scans(min_len=50):
            turns += 1
            for _q, ang, dist in scan:
                if dist > 0:
                    sectors.add(int(ang // 10) % 36)
                    n += 1
            if turns >= LIDAR_TURNS:
                break
        dt = max(time.monotonic() - t0, 1e-6)
        return {"info": info, "health": health, "turns": turns,
                "points_per_s": n / dt, "hz": turns / dt, "sectors": len(sectors)}
    finally:
        lidar.close()


def _realsense_probe() -> list[dict]:
    """Enumeration only (no pipeline, no stream). Raises ImportError without pyrealsense2."""
    import pyrealsense2 as rs

    out = []
    for dev in rs.context().query_devices():
        def info(key, dev=dev):
            try:
                return dev.get_info(getattr(rs.camera_info, key))
            except Exception:  # noqa: BLE001 - a field a device does not report
                return None
        out.append({"name": info("name"), "serial": info("serial_number"),
                    "firmware": info("firmware_version"), "usb": info("usb_type_descriptor")})
    return out


def _import(name: str):
    return importlib.import_module(name)


def _canonical(name: str) -> str:
    """A distribution name as dimOS turns it into a namespace (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _on_root(entry: str) -> bool:
    try:
        return Path(entry or ".").resolve() == ROOT
    except (OSError, RuntimeError, ValueError):
        return False


def _entry_points(group: str = "dimos.blueprints") -> set[str]:
    """Local names of the blueprints registered by THIS distribution only:
    `dimos run moss-dimos.moss-nav` resolves through the moss-dimos namespace,
    so the same local name registered by another installed package proves
    nothing. Read from the installed distributions, as the stack's dimOS reads
    them: the checkout itself is left out, because the moss_dimos.egg-info an
    editable install leaves there is not on the stack's path."""
    from importlib.metadata import distributions

    path = [p for p in sys.path if not _on_root(p)]
    for dist in distributions(path=path):
        dist_name = dist.metadata.get("Name")
        if dist_name and _canonical(dist_name) == DISTRIBUTION:
            # the first one found is the one Python uses
            return {ep.name for ep in dist.entry_points if ep.group == group}
    return set()


def _module_file() -> str | None:
    """Where `import moss_dimos` lands for the stack: a fresh interpreter of
    this venv, started from this checkout as the launcher starts dimOS, without
    the current directory on sys.path (dimOS runs as a console script, which
    does not add it). None when moss_dimos does not import there."""
    code = ("import sys\n"
            "if sys.path and sys.path[0] == '':\n"
            "    del sys.path[0]\n"
            "import moss_dimos\n"
            "sys.stdout.write(moss_dimos.__file__ or '')\n")
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def _robot_profile():
    """The geometry the MOSS stack will fly (MOSS with its MOSS_* overrides)."""
    from moss_dimos import robot_profile

    p = robot_profile.current()
    return p, robot_profile.derived(p)


def _state_dir() -> Path:
    """MOSS_STATE_DIR resolved exactly as the recorder resolves it (absolute)."""
    from moss_dimos import robot_profile

    return robot_profile.moss_state_dir()


# ── robot.env: what the robot IS (driver, pad layout, measured numbers) ──────────────────────
ROBOT_ENV_NAME = "robot.env"


def load_robot_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines (optional `export `, # comments, quotes stripped). Pure: tests/benches."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            out[key] = val
    return out


def apply_robot_env(env: dict | None = None) -> tuple[Path, dict[str, str]]:
    """The launchers source <MOSS_STATE_DIR>/robot.env; the flight check reads the same file so its
    verdicts match what the stack will run with. The shell's own values win (setdefault)."""
    e = os.environ if env is None else env
    path = _state_dir() / ROBOT_ENV_NAME
    text = _read_text(path)
    pairs = load_robot_env(text) if text is not None else {}
    for key, val in pairs.items():
        e.setdefault(key, val)
    return path, pairs


def driver_verdict(expected: str, reported) -> tuple[bool, str]:
    """MOSS_DRIVER (robot.env) against the firmware's `driver` key. Pure.
    No expectation: informative. Expectation and a different (or missing) driver: a KO with the fix."""
    exp = (expected or "").strip().lower()
    rep = (str(reported).strip().lower() if reported else "")
    if not exp:
        return True, (rep or "not reported (a firmware build older than the driver key)") + \
            "; set MOSS_DRIVER in robot.env to make this a check"
    if rep == exp:
        return True, f"{rep} = MOSS_DRIVER"
    if not rep:
        return False, f"not reported, robot.env expects {exp}: reflash the {exp} build (bench/README.md)"
    return False, f"firmware built for {rep}, robot.env expects {exp}: reflash the {exp} build (bench/README.md)"


PAD_MUTE_AXIS = -32767   # the kernel's initial value for an axis the pad never reported


def pad_verdict(name: str, init_axes, layout: str) -> tuple[bool, str]:
    """One pad as SDL will take it: alive at neutral, in the layout the stack will use. Pure.
    init_axes: the joystick API's initial axis values (None = could not read)."""
    lay = (layout or "android").strip().lower() or "android"
    n = (name or "").lower()
    if lay == "auto":
        from moss_dimos.gamepad import layout_for_name
        lay = f"auto -> {layout_for_name(name)}"
    if init_axes is None:
        return False, f"{name}: cannot read it (permissions? held exclusively?)"
    if init_axes and all(int(v) == PAD_MUTE_AXIS for v in init_axes):
        return False, (f"{name}: MUTE - every axis at its never-reported value: the receiver sees no pad "
                       "(pad off, or not paired with this dongle); the stack will never see it at neutral")
    if lay.startswith("auto"):
        return True, f"{name} alive, layout {lay}"
    xbox = ("x-box" in n or "xbox" in n or "x box" in n)
    if xbox and lay != "xinput":
        return False, f"{name}: an Xbox 360 pad to the kernel (the pad on its cable), MOSS_PAD_LAYOUT is {lay}: set MOSS_PAD_LAYOUT=xinput in robot.env"
    if "shanwan" in n and lay == "xinput":
        return False, f"{name}: the dongle in Android mode, MOSS_PAD_LAYOUT is xinput: set MOSS_PAD_LAYOUT=android in robot.env"
    return True, f"{name} alive, layout {lay}"


# ── helpers ────────────────────────────────────────────────────────────────
def _env_on(name: str, default: bool) -> bool:
    """A MOSS_* switch, parsed by the stack's own parser."""
    from moss_dimos import robot_profile

    return robot_profile.env_on(name, default)


def _raw(name: str) -> str:
    """A switch's value as written, for the messages."""
    return os.environ.get(name, "").strip()


def _first(patterns) -> str | None:
    for pat in patterns:
        hits = _ls(pat)
        if hits:
            return hits[0]
    return None


def _nearest_existing(path: Path) -> Path:
    p = path
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


def _is_dimos_run(cmdline: str) -> bool:
    """`<venv>/bin/dimos [root options] run <blueprint>`: root options such as
    `--rerun-open none` sit BETWEEN `dimos` and `run`, so a plain substring
    'bin/dimos run' never matches a real launch."""
    toks = cmdline.split()
    for i, t in enumerate(toks):
        if t.endswith("bin/dimos"):
            return "run" in toks[i + 1:]
    return False


# ── checks ─────────────────────────────────────────────────────────────────
def check_stack(ctx: dict) -> None:
    """A running stack owns the board and the lidar: the probes that would open
    them are skipped, and the launcher's own gate 0 refuses a second stack."""
    section("stack (dimOS)")
    me = os.getpid()
    cmdlines = dict(_proc_cmdlines())
    live, stale = None, 0
    for f in sorted(_runs_dir().glob("*.json")):
        try:
            entry = json.loads(f.read_text())
            pid = int(entry.get("pid", 0))
        except (OSError, ValueError, TypeError):
            stale += 1
            continue
        # A registry file outlives a reboot and its pid can be reused by any
        # process: only a live pid that IS a `dimos ... run` makes a stack.
        if _pid_alive(pid) and _is_dimos_run(cmdlines.get(pid, "")):
            live = (entry.get("run_id") or f.stem, pid)
        else:
            stale += 1
    procs = [(pid, cmd) for pid, cmd in cmdlines.items() if pid != me and _is_dimos_run(cmd)]
    note = f" ({stale} stale registry entr{'y' if stale == 1 else 'ies'})" if stale else ""
    if live:
        ctx["stack"] = f"run {live[0]} pid {live[1]}"
        verdict(True, "stack", f"{live[0]} pid {live[1]}{note}")
    elif procs:
        ctx["stack"] = f"unregistered dimos run pid {procs[0][0]}"
        verdict(True, "stack", f"unregistered dimos run pid {procs[0][0]} (a zombie? moss-fly.sh gate 0 sweeps it){note}")
    else:
        ctx["stack"] = None
        verdict(True, "stack", f"none{note}")


def _resolve(env_name: str, pattern: str) -> tuple[str | None, str]:
    """The path the stack will open: the env override when set, else the by-id glob."""
    env = os.environ.get(env_name)
    if env:
        return env, f"{env_name}"
    hits = _ls(os.path.join(BYID_DIR, pattern))
    return (hits[0] if hits else None), f"by-id {pattern}"


def check_ports(ctx: dict) -> None:
    section("ports (by-id)")
    ctx["qtpy"] = ctx["c1"] = None
    for key, label, env_name, pattern, missing in (
            ("qtpy", "motor board (QT Py)", "MOSS_PORT", QTPY_GLOB,
             "not on USB - cable, power, or the board sits in its bootloader (by-id 'Espressif')"),
            ("c1", "lidar (RPLidar C1 on CP2102N)", "MOSS_LIDAR_PORT", C1_GLOB,
             "not on USB - lidar cable or hub")):
        if key == "qtpy" and _env_on("MOSS_MOCK_BUS", False):
            verdict(True, label, f"MOSS_MOCK_BUS={_raw('MOSS_MOCK_BUS')}: fake firmware, the board is not needed")
            continue
        path, how = _resolve(env_name, pattern)
        if not path or not _exists(path):
            verdict(False, label, f"{path or pattern} {missing}")
            continue
        holders = [] if ctx.get("stack") else _port_holders(path)
        if holders:
            verdict(False, f"{label} free", f"held by pid {', '.join(map(str, holders))} - stop that process first")
            continue
        ctx[key] = path
        verdict(True, label, f"{os.path.basename(path)} ({how})"
                + (" - in use by the stack" if ctx.get("stack") else ", free"))
    # On MOSS /dev/ttyUSB0 IS the lidar: a MOSS_PORT naming it (or the CP2102N
    # by-id path) would send motor commands into the lidar.
    if ctx["qtpy"] and ctx["c1"] and os.path.realpath(ctx["qtpy"]) == os.path.realpath(ctx["c1"]):
        verdict(False, "motor port is not the lidar", f"MOSS_PORT and the lidar are both {os.path.realpath(ctx['c1'])}"
                " - unset MOSS_PORT (the QT Py by-id is found on its own)")
        ctx["qtpy"] = None


def _battery(t: dict) -> None:
    mv = t.get("bus_mV")
    if t.get("ina_ok") is not True or mv is None:
        verdict(False, "battery", "INA219 not seen (ina_ok false, no bus_mV) - check its STEMMA cable")
        return
    v = int(mv) / 1000.0
    if mv >= BATTERY_FLOOR_MV:
        verdict(True, "battery", f"{v:.2f} V")
    elif mv >= BMS_CUT_MV:
        verdict(False, "battery", f"{v:.2f} V - under 10.8 V: the BMS cuts at 10.2 V under load, charge first")
    else:
        verdict(False, "battery", f"{v:.2f} V - under the BMS cut (10.2 V): charge before anything")


def check_firmware(ctx: dict, quick: bool) -> None:
    section("firmware (QT Py, listen only)")
    if _env_on("MOSS_MOCK_BUS", False):
        skipped("firmware telemetry", f"MOSS_MOCK_BUS={_raw('MOSS_MOCK_BUS')} (fake firmware)")
        return
    if ctx.get("stack"):
        skipped("firmware telemetry", f"held by the stack ({ctx['stack']})")
        return
    if quick:
        skipped("firmware telemetry", "--quick")
        return
    port = ctx.get("qtpy")
    if not port:
        skipped("firmware telemetry", "no free QT Py port (see ports)")
        return
    try:
        ser = _open_serial(port, FIRMWARE_BAUD)
    except Exception as exc:  # noqa: BLE001
        verdict(False, "firmware telemetry", f"cannot open {port}: {exc!r} - dialout group? another process?")
        return
    last, n, buf = None, 0, b""
    try:
        with contextlib.suppress(Exception):
            ser.reset_input_buffer()     # a partial line from before the open
        deadline = time.monotonic() + LISTEN_S
        while time.monotonic() < deadline:
            buf += ser.read(4096) or b""
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line.startswith(b"{"):
                    continue
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if isinstance(doc, dict):
                    last, n = doc, n + 1
    finally:
        with contextlib.suppress(Exception):
            ser.close()
    if last is None:
        verdict(False, "firmware telemetry", f"mute for {LISTEN_S:.1f} s - power-cycle the board, or reflash it")
        return
    verdict(True, "firmware telemetry", f"{n} line(s) in {LISTEN_S:.1f} s")
    fw = last.get("fw")
    verdict(isinstance(fw, str) and bool(fw), "firmware version", str(fw) if fw else "no 'fw' key - a build older than v3?")
    mode = last.get("mode")
    verdict(mode == 0, "firmware disarmed",
            "mode 0 (off)" if mode == 0 else f"mode {mode} ({last.get('reason')}) - something else is driving it")
    ok, detail = driver_verdict(_raw("MOSS_DRIVER"), last.get("driver"))
    verdict(ok, "motor driver", detail)
    if "stop_open" in last or "stop_latched" in last:
        opened, latched = last.get("stop_open"), last.get("stop_latched")
        valid = isinstance(opened, bool) and isinstance(latched, bool)
        ready = valid and not opened and not latched
        detail = ("NC loop closed, no latched stop" if ready else
                  "open NC loop: release the button and check SCK-to-GND wiring" if opened is True else
                  "stop latched: stop teleoperation, release the button, then send clearstop" if latched is True else
                  "malformed stop telemetry")
        verdict(ready, "track stop button", detail)
    _battery(last)
    ticks = last.get("ticks")
    good = isinstance(ticks, list) and len(ticks) == 2 and all(isinstance(x, int) for x in ticks)
    verdict(good, "encoder ticks", f"L {ticks[0]} R {ticks[1]}" if good else f"missing or malformed: {ticks!r}")


def check_lidar(ctx: dict, spin: bool) -> None:
    section("lidar (RPLidar C1, ~5 s spin)")
    if ctx.get("stack"):
        skipped("lidar scan", f"held by the stack ({ctx['stack']})")
        return
    if not spin:
        skipped("lidar scan", "--quick/--no-spin")
        return
    port = ctx.get("c1")
    if not port:
        skipped("lidar scan", "no free lidar port (see ports)")
        return
    try:
        r = _lidar_probe(port)
    except Exception as exc:  # noqa: BLE001
        verdict(False, "lidar answers", f"{type(exc).__name__}: {exc} - unplug/replug the lidar cable, then rerun")
        return
    info = r.get("info") or {}
    verdict(True, "lidar answers", f"model {info.get('model')} serial {info.get('serial')}")
    status, code = (r.get("health") or ("?", -1))
    verdict(status == "Good", "lidar health", f"{status} ({code})")
    pps, sectors = float(r.get("points_per_s", 0.0)), int(r.get("sectors", 0))
    verdict(pps > LIDAR_MIN_PPS and sectors == 36, "lidar scan",
            f"{r.get('turns')} turns, {pps:.0f} points/s, {sectors}/36 sectors seen"
            + ("" if sectors == 36 else " - something sits in the scan plane, or the spin is weak"))


def check_realsense(ctx: dict) -> None:
    section("camera (RealSense, enumeration only)")
    if not _env_on("MOSS_CAMERA", True):
        skipped("RealSense", f"MOSS_CAMERA={_raw('MOSS_CAMERA')}: this flight builds no RealSense")
        return
    wanted = os.environ.get("MOSS_RS_SERIAL") or None
    try:
        devices = _realsense_probe()
    except ImportError as exc:
        verdict(False, "RealSense", f"pyrealsense2 not importable: {exc} - install it (Software.md),"
                " or fly without the camera: MOSS_CAMERA=0")
        return
    except Exception as exc:  # noqa: BLE001
        verdict(False, "RealSense", f"enumeration failed: {exc}")
        return
    d455 = [d for d in devices if "D455" in str(d.get("name") or "")
            and (wanted is None or d.get("serial") == wanted)]
    if not d455:
        seen = ", ".join(f"{d.get('name')} {d.get('serial')}" for d in devices) or "nothing"
        verdict(False, "RealSense D455", f"no D455{' with serial ' + wanted if wanted else ''} (seen: {seen})"
                " - plug it on USB 3, or fly without the camera: MOSS_CAMERA=0")
        return
    d = d455[0]
    usb = str(d.get("usb") or "")
    desc = f"{d.get('name')} serial {d.get('serial')} fw {d.get('firmware')} USB {usb or '?'}"
    if usb.startswith("3"):
        verdict(True, "RealSense D455", desc)
    elif usb.startswith("2"):
        verdict(False, "RealSense D455", f"{desc} - on USB 2: 5 fps max, replug on a USB 3 port/cable")
    else:
        verdict(False, "RealSense D455", f"{desc} - unknown USB link")


def check_wrist(ctx: dict) -> None:
    section("wrist camera (UVC)")
    if not _env_on("MOSS_WRIST", True):
        skipped("wrist camera", f"MOSS_WRIST={_raw('MOSS_WRIST')}: this flight builds no wrist camera")
        return
    path = _first(os.path.join(V4L_DIR, g) for g in WRIST_GLOBS)
    if path is None:
        others = [h for h in _ls(os.path.join(V4L_DIR, WRIST_ANY_GLOB))
                  if not any(x in os.path.basename(h).lower() for x in WRIST_NOT)]
        path = others[0] if others else None
    # The stack skips a missing wrist camera with a warning (no wrist_image):
    # its absence is a warning here too, not a refusal.
    verdict(True, "wrist camera", path or f"WARN not seen (no {' or '.join(WRIST_GLOBS)} and no other "
            f"{WRIST_ANY_GLOB} besides the RealSense under {V4L_DIR}); the stack runs without wrist_image")


def check_gamepad(ctx: dict) -> None:
    section("gamepad")
    pads = _ls("/dev/input/js*")   # any number: the pad on its cable keeps js1 after the dongle's js0
    if pads:
        try:
            index = max(0, int(_raw("MOSS_PAD_INDEX") or "0"))
        except ValueError:
            index = 0
        js = pads[index] if index < len(pads) else pads[0]
        name = _pad_name(js)
        ok, detail = pad_verdict(name, _pad_init_axes(js), _raw("MOSS_PAD_LAYOUT"))
        others = [f"{os.path.basename(j)}={_pad_name(j)}" for j in pads if j != js]
        verdict(ok, "gamepad", f"{os.path.basename(js)}: {detail}" + (f"; also plugged: {', '.join(others)}" if others else ""))
        return
    usb = _usb_devices()
    if PAD_SHANWAN in usb:
        why = f"receiver visible ({PAD_SHANWAN}), no js device: replug or reboot"
    elif PAD_SWITCH_PRO in usb:
        why = (f"pad enumerated as a Nintendo Pro Controller ({PAD_SWITCH_PRO}) without a driver: "
               "switch the pad to its Android/X-input mode and replug")
    else:
        why = "no pad (no js device, no known receiver on USB)"
    # A missing pad stops nothing from running: the map builds, the cockpit shows, exploration
    # can be armed; only hand driving is lost. MOSS_REQUIRE_PAD=1 turns this into a refusal.
    required = _env_on("MOSS_REQUIRE_PAD", False)
    verdict(not required, "gamepad", ("" if required else "WARN nothing drives by hand in moss-nav; ") + why)


def check_system(ctx: dict) -> None:
    section("system")
    try:
        where = _nearest_existing(_state_dir())
        st = _statvfs(str(where))
        free_gb = st.f_bavail * st.f_frsize / 1e9
        verdict(free_gb > DISK_MIN_GB, "disk for recordings", f"{free_gb:.1f} GB free on {where}")
    except Exception as exc:  # noqa: BLE001 - an unresolvable state dir, a failed statvfs
        verdict(False, "disk for recordings", f"{type(exc).__name__}: {exc}")
    try:
        avail = _meminfo().get("MemAvailable", 0)
        verdict(avail > RAM_MIN_KB, "RAM available", f"{avail / 1e6:.1f} GB")
    except (OSError, ValueError) as exc:
        verdict(False, "RAM available", str(exc))
    rmem = _sysctl("net.core.rmem_max")
    try:
        r = int(rmem) if rmem is not None else None
    except ValueError:
        r = None
    flags = _lo_flags()
    lo_on = flags is not None and bool(flags & IFF_MULTICAST)
    route = _mcast_route()
    # dimOS sets what is missing with sudo at every launch, and its multicast
    # setting is critical: a launch that cannot run sudo dies on it. The
    # launcher starts dimOS in the background (and the cockpit page has no
    # terminal at all), so only passwordless sudo, or the boot unit, works.
    needs_fix = not lo_on or not route or (r is not None and r < RMEM_TARGET)
    sudo = _sudo_ok() if needs_fix else True
    if r is None:
        verdict(True, "socket buffers", "net.core.rmem_max unreadable (warning only)")
    elif r >= RMEM_TARGET:
        verdict(True, "socket buffers", f"rmem_max {r}")
    elif sudo:
        verdict(True, "socket buffers", f"warning: rmem_max {r} < {RMEM_TARGET} - dimOS raises it with sudo at launch")
    else:
        verdict(True, "socket buffers", f"warning: rmem_max {r} < {RMEM_TARGET} and no passwordless sudo:"
                f" LCM runs with small buffers - {LCM_FIX}")
    if lo_on:
        verdict(True, "loopback multicast", "on")
    elif sudo:
        verdict(True, "loopback multicast", "off - dimOS turns it on with sudo at launch")
    else:
        verdict(False, "loopback multicast", f"off, and no passwordless sudo here: dimOS cannot turn it on at launch"
                f" - {LCM_FIX}")
    if route is None:
        verdict(False, "multicast route", "cannot run `ip` (iproute2): dimOS needs it to check and set LCM multicast")
    elif route:
        verdict(True, "multicast route", f"{MCAST_PREFIX} routed")
    elif sudo:
        verdict(True, "multicast route", f"no {MCAST_PREFIX} route - dimOS adds it on lo with sudo at launch")
    else:
        verdict(False, "multicast route", f"no {MCAST_PREFIX} route, and no passwordless sudo here: dimOS cannot"
                f" add it at launch - {LCM_FIX}")


def check_software(ctx: dict) -> None:
    section("software")
    # pygame prints a banner on import unless told not to (as moss_dimos/gamepad.py does)
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    for name in SOFTWARE_IMPORTS:
        try:
            mod = _import(name)
            verdict(True, f"import {name}", str(getattr(mod, "__version__", "") or ""))
        except Exception as exc:  # noqa: BLE001
            verdict(False, f"import {name}", f"{type(exc).__name__}: {exc}")
    try:
        names = _entry_points()
    except Exception as exc:  # noqa: BLE001
        names = set()
        verdict(False, "blueprint entry points", f"cannot read: {exc}")
    for bp in MOSS_BLUEPRINTS:
        verdict(bp in names, f"blueprint {bp}",
                f"registered as {DISTRIBUTION}.{bp}" if bp in names
                else f"missing from {DISTRIBUTION} - reinstall in {ROOT}: {REINSTALL}")
    try:
        src = _module_file()
    except Exception:  # noqa: BLE001 - reported as not importable
        src = None
    if src is None:
        verdict(False, "moss-dimos install", f"moss_dimos does not import in this venv ({sys.executable})"
                f" - install it in {ROOT}: {REINSTALL}")
    elif Path(src).resolve().is_relative_to(ROOT):
        verdict(True, "moss-dimos install", "the stack imports moss_dimos from this checkout")
    else:
        verdict(False, "moss-dimos install", f"the stack would import moss_dimos from {Path(src).resolve().parent},"
                f" not from this checkout - reinstall in {ROOT}: {REINSTALL}")
    try:
        p, d = _robot_profile()
        name = getattr(p, "name", None)
        lethal = d.get("lethal_clearance_m") if isinstance(d, dict) else getattr(d, "lethal_clearance_m", None)
        verdict(True, "robot profile",
                f"{name}: width {p.robot_width_m} m, pivot {p.pivot_diameter_m} m, "
                f"lidar {p.lidar_height_m} m up, lethal {lethal:.2f} m (placeholders until measured)")
    except Exception as exc:  # noqa: BLE001
        verdict(False, "robot profile", f"{type(exc).__name__}: {exc}")


def check_state_dir(ctx: dict) -> None:
    section("state dir")
    try:
        d = _state_dir()
        (d / "recordings").mkdir(parents=True, exist_ok=True)
        ok = os.access(d / "recordings", os.W_OK)
        verdict(ok, "MOSS state dir", f"{d} (recordings/ {'writable' if ok else 'NOT writable'})")
    except Exception as exc:  # noqa: BLE001 - unresolvable or unwritable
        verdict(False, "MOSS state dir", f"{os.environ.get('MOSS_STATE_DIR') or '~/.local/state/moss'}: {exc}")


# ── main ───────────────────────────────────────────────────────────────────
def document(flags: dict) -> dict:
    counted = [r for r in RESULTS if not r.get("skipped")]
    ko = [r["label"] for r in counted if not r["ok"]]
    n_ok = len(counted) - len(ko)
    summary = f"{n_ok}/{len(counted)} OK" + (f" - KO: {', '.join(ko)}" if ko else " - ready to fly")
    return {"ts": time.time(), "checks": list(RESULTS), "ok_count": n_ok, "ko_count": len(ko),
            "skipped_count": len(RESULTS) - len(counted), "summary": summary, "flags": flags}


def _save(path: str, doc: dict) -> None:
    p = Path(os.path.expanduser(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1))
    os.replace(tmp, p)   # the cockpit never reads half a document


def run(quick: bool = False, no_spin: bool = False) -> None:
    ctx: dict = {}
    section("robot.env (what the robot is: driver, pad layout, measured numbers)")
    env_path, pairs = apply_robot_env()
    verdict(True, "robot.env", (f"{env_path}: " + ", ".join(f"{k}={v}" for k, v in pairs.items())) if pairs
            else f"{env_path} absent: nothing declared (MOSS_DRIVER, MOSS_PAD_LAYOUT...) - the checks stay informative")
    check_stack(ctx)
    check_ports(ctx)
    check_firmware(ctx, quick)
    check_lidar(ctx, spin=not (quick or no_spin))
    check_realsense(ctx)
    check_wrist(ctx)
    check_gamepad(ctx)
    check_system(ctx)
    check_software(ctx)
    check_state_dir(ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MOSS flight check (read-only)")
    ap.add_argument("--json", action="store_true", help="print one JSON document instead of lines")
    ap.add_argument("--quick", action="store_true", help="skip the lidar spin and the firmware listen")
    ap.add_argument("--no-spin", action="store_true", help="skip only the lidar spin")
    ap.add_argument("--save", metavar="FILE", help="also write the JSON document to FILE (atomically)")
    a = ap.parse_args(argv)
    RESULTS.clear()
    _QUIET[0] = a.json
    flags = {"quick": a.quick, "no_spin": a.no_spin or a.quick}
    if a.json:
        # imports (dimos above all) may print: keep stdout for the document only
        with contextlib.redirect_stdout(sys.stderr):
            run(a.quick, a.no_spin)
    else:
        run(a.quick, a.no_spin)
    doc = document(flags)
    if a.save:
        try:
            _save(a.save, doc)
        except OSError as exc:
            print(f"(could not save {a.save}: {exc})", file=sys.stderr)
    if a.json:
        print(json.dumps(doc, indent=1))
    else:
        print(f"\n{doc['summary']}" + (f" ({doc['skipped_count']} skipped)" if doc["skipped_count"] else ""))
    return 1 if doc["ko_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
