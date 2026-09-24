"""Serial bridge to the MOSS ESP32-S3 firmware (see firmware/README.md).

The firmware contract, restated so this file can be read alone:
- 115200 baud, newline-terminated commands: `status`, `stop`, `zero`, `arm`,
  `drive LEFT RIGHT` (integers, -25..+25), `test left|right PERCENT`;
- replies are `OK` or `ERR <reason>`; every ERR also stops and disarms;
- `status` and a timer produce one JSON telemetry line about every 200 ms;
- the firmware itself stops and disarms 300 ms after the last drive command.

What this module adds on the Pi side:
- pure `format_*` functions that build the exact command lines;
- `parse_line`, which turns a firmware line into a Telemetry, a Reply or an Info;
- `SerialBridge`, which writes commands, reads lines, reopens a lost port and
  runs a host-side deadman: no drive request for 300 ms means one `stop`.

`test` is left out on purpose: it moves one motor without arming and belongs to
bench commissioning, not to driving.

Time and the port are injected (`clock`, `open_port`) so every behaviour here
is testable without a robot or a serial device.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

BAUD = 115200
MAX_PERCENT = 25            # firmware MAX_PERCENT (commissioning limit)
DEADMAN_S = 0.300           # same value as the firmware COMMAND_TIMEOUT_MS
ARM_TIMEOUT_S = 10.0        # firmware ARM_TIMEOUT_MS: an arm with no drive expires
RECONNECT_S = 1.0           # delay between two attempts to reopen a lost port
MODES = {0: "off", 1: "ready", 2: "drive", 3: "test"}


# --------------------------------------------------------------------------- commands

def format_drive(left: int, right: int) -> bytes:
    """(left, right) duty in percent -> the exact line the firmware expects, e.g. b'drive 10 10\\n'.

    Only integers in [-MAX_PERCENT, MAX_PERCENT] are accepted: the firmware
    would answer anything else with `ERR invalid_command` and a stop, so the
    Pi refuses it before it reaches the wire.
    """
    for name, v in (("left", left), ("right", right)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f"{name} must be an int percent, got {v!r}")
        if not -MAX_PERCENT <= v <= MAX_PERCENT:
            raise ValueError(f"{name} must be in [-{MAX_PERCENT}, {MAX_PERCENT}], got {v}")
    return f"drive {left} {right}\n".encode("ascii")


def format_simple(command: str) -> bytes:
    """One of the argument-free commands -> its line."""
    if command not in ("status", "stop", "zero", "arm"):
        raise ValueError(f"unknown command {command!r}")
    return f"{command}\n".encode("ascii")


# --------------------------------------------------------------------------- telemetry

@dataclass(frozen=True)
class Telemetry:
    """One firmware telemetry line. Units are the firmware's; properties convert."""
    ms: int                          # firmware uptime, milliseconds
    mode: int                        # 0 off, 1 ready, 2 drive, 3 test
    reason: str                      # why the firmware is in this mode
    target_pct: tuple[int, int]      # commanded PWM duty, percent
    output_pct: tuple[int, int]      # ramped PWM duty actually applied, percent
    ticks: tuple[int, int]           # raw quadrature x4 encoder counts
    invalid_edges: tuple[int, int]
    ina_ok: bool
    bus_mV: int | None               # battery bus voltage, None when the INA219 is not read
    shunt_uV: int | None
    current_mA: float | None         # None in the reference firmware (no validated shunt)
    raw: dict                        # the decoded JSON object, untouched

    @property
    def mode_name(self) -> str:
        return MODES.get(self.mode, f"unknown({self.mode})")

    @property
    def bus_V(self) -> float | None:
        return None if self.bus_mV is None else self.bus_mV / 1000.0

    @property
    def uptime_s(self) -> float:
        return self.ms / 1000.0


@dataclass(frozen=True)
class Reply:
    """`OK` or `ERR <reason>`."""
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class Info:
    """Anything else: the boot banner, a garbled or truncated line."""
    text: str


def _pair(obj: dict, key: str) -> tuple[int, int]:
    v = obj[key]
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in v)):
        raise ValueError(key)
    return v[0], v[1]


def _opt_int(obj: dict, key: str) -> int | None:
    v = obj[key]
    if v is not None and (not isinstance(v, int) or isinstance(v, bool)):
        raise ValueError(key)
    return v


def parse_line(line: str) -> Telemetry | Reply | Info:
    """A firmware line (without its newline) -> Telemetry, Reply or Info. Never raises."""
    text = line.strip()
    if text == "OK":
        return Reply(ok=True)
    if text.startswith("ERR"):
        return Reply(ok=False, error=text[3:].strip() or "unknown")
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            current = obj["current_mA"]
            if current is not None and (not isinstance(current, (int, float)) or isinstance(current, bool)):
                raise ValueError("current_mA")
            if not isinstance(obj["ms"], int) or not isinstance(obj["mode"], int) or not isinstance(obj["reason"], str):
                raise ValueError("header")
            return Telemetry(
                ms=obj["ms"], mode=obj["mode"], reason=obj["reason"],
                target_pct=_pair(obj, "target_pct"), output_pct=_pair(obj, "output_pct"),
                ticks=_pair(obj, "ticks"), invalid_edges=_pair(obj, "invalid_edges"),
                ina_ok=obj["ina_ok"] is True, bus_mV=_opt_int(obj, "bus_mV"),
                shunt_uV=_opt_int(obj, "shunt_uV"),
                current_mA=None if current is None else float(current), raw=obj,
            )
        except (ValueError, KeyError, TypeError):
            pass
    return Info(text)


# --------------------------------------------------------------------------- bridge

class Port(Protocol):
    """The subset of pyserial.Serial the bridge uses."""
    def write(self, data: bytes) -> int | None: ...
    def read(self, size: int = 1) -> bytes: ...
    def close(self) -> None: ...


def open_serial(device: str) -> Port:
    """Open the real port: 115200 8N1, non-blocking reads.

    DTR and RTS are held low before opening. On the ESP32-S3-DevKitC-1 these
    lines drive EN and IO0 through the auto-program circuit; asserting them can
    reset the board or stop it in the bootloader. (Hypothesis for the Pi: this
    is the usual behaviour of that circuit, not yet checked on MOSS.)
    """
    import serial  # optional dependency: pip install 'moss-dimos[pi]'

    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.write_timeout = device, BAUD, 0, 0.1
    s.dtr = False
    s.rts = False
    s.open()
    return s


Listener = Callable[[str, "Telemetry | Reply | Info"], None]


class SerialBridge:
    """Writes commands, reads firmware lines, stops on silence, reopens a lost port.

    Call `tick()` often (the teleop loop does, or `start()` runs it in a
    thread). All methods are safe to call from several threads.

    Local safety rules, on top of the firmware's own:
    - `drive()` is refused unless `arm()` was sent since the last stop, error
      or reconnect, and less than ARM_TIMEOUT_S ago if no drive followed it;
    - the deadman: `DEADMAN_S` after the last `drive()` call, one `stop` is
      written and the bridge disarms;
    - a failed read or write closes the port and disarms; the port is reopened
      every `RECONNECT_S`, and the first line written after reopening is `stop`.
    """

    def __init__(self, open_port: Callable[[], Port], clock: Callable[[], float] = time.monotonic,
                 deadman_s: float = DEADMAN_S, reconnect_s: float = RECONNECT_S) -> None:
        self._open_port = open_port
        self._clock = clock
        self.deadman_s = deadman_s
        self.reconnect_s = reconnect_s
        self._port: Port | None = None
        self._next_open = 0.0
        self._buf = b""
        self._lock = threading.RLock()
        self._armed = False
        self._last_drive: float | None = None
        self._armed_at: float | None = None
        self._listeners: list[Listener] = []
        self.last_telemetry: Telemetry | None = None
        self.last_reply: Reply | None = None
        self._thread: threading.Thread | None = None
        self._stop_thread = threading.Event()

    # -- state
    @property
    def connected(self) -> bool:
        return self._port is not None

    @property
    def armed(self) -> bool:
        return self._armed

    def add_listener(self, fn: Listener) -> None:
        """fn(line, parsed) is called for every line read from the firmware."""
        self._listeners.append(fn)

    # -- commands
    def status(self) -> bool:
        return self._write(format_simple("status"))

    def zero(self) -> bool:
        return self._write(format_simple("zero"))

    def arm(self) -> bool:
        with self._lock:
            ok = self._write(format_simple("arm"))
            self._armed = ok
            self._armed_at = self._clock() if ok else None
            self._last_drive = None
            return ok

    def stop(self) -> bool:
        with self._lock:
            self._armed = False
            self._last_drive = None
            return self._write(format_simple("stop"))

    def drive(self, left: int, right: int) -> bool:
        """Send `drive LEFT RIGHT` and feed the deadman. Returns False if nothing was sent."""
        line = format_drive(left, right)  # validate before touching any state
        with self._lock:
            if not self._armed:
                return False
            if not self._write(line):
                return False
            self._last_drive = self._clock()
            return True

    # -- loop
    def tick(self) -> None:
        """Reopen the port if due, read and dispatch lines, apply the deadman."""
        with self._lock:
            now = self._clock()
            if self._port is None and now >= self._next_open:
                self._try_open(now)
            self._read()
            if self._last_drive is not None and now - self._last_drive >= self.deadman_s:
                self.stop()
            elif (self._armed and self._last_drive is None and self._armed_at is not None
                  and now - self._armed_at >= ARM_TIMEOUT_S):
                self._armed = False  # the firmware has disarmed itself; nothing to send

    def start(self, period_s: float = 0.01) -> None:
        """Run tick() in a background thread until close()."""
        def run() -> None:
            while not self._stop_thread.is_set():
                self.tick()
                time.sleep(period_s)
        self._stop_thread.clear()
        self._thread = threading.Thread(target=run, name="moss-serial-bridge", daemon=True)
        self._thread.start()

    def close(self) -> None:
        """Send a last `stop` if the port is open, then close it."""
        self._stop_thread.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        with self._lock:
            if self._port is not None:
                self.stop()
            self._drop_port()

    # -- internals
    def _try_open(self, now: float) -> None:
        try:
            self._port = self._open_port()
        except Exception:  # device absent, permission, busy: retry later
            self._port = None
            self._next_open = now + self.reconnect_s
            return
        self._buf = b""
        self.stop()  # a fresh link starts from a known, stopped state

    def _drop_port(self) -> None:
        port, self._port = self._port, None
        self._armed = False
        self._last_drive = None
        self._buf = b""
        self._next_open = self._clock() + self.reconnect_s
        if port is not None:
            try:
                port.close()
            except Exception:
                pass

    def _write(self, data: bytes) -> bool:
        with self._lock:
            if self._port is None:
                self._armed = False
                return False
            try:
                self._port.write(data)
                return True
            except Exception:
                self._drop_port()
                return False

    def _read(self) -> None:
        if self._port is None:
            return
        try:
            chunk = self._port.read(4096)
        except Exception:
            self._drop_port()
            return
        if not chunk:
            return
        self._buf += chunk
        *lines, self._buf = self._buf.split(b"\n")
        if len(self._buf) > 4096:  # no newline for far too long: garbage, drop it
            self._buf = b""
        for raw in lines:
            text = raw.decode("ascii", errors="replace").rstrip("\r")
            if not text:
                continue
            parsed = parse_line(text)
            if isinstance(parsed, Telemetry):
                self.last_telemetry = parsed
            elif isinstance(parsed, Reply):
                self.last_reply = parsed
                if not parsed.ok:
                    # every ERR stops and disarms the firmware: mirror it
                    self._armed = False
                    self._last_drive = None
            for fn in self._listeners:
                fn(text, parsed)
