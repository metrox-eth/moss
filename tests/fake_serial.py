"""A fake serial port and a fake clock for cold tests of moss_pi (no pyserial, no robot).

FakeSerial replays firmware lines queued with `feed_line` / `feed_recording`
and keeps every byte the bridge writes in `written`. `fail_next_io()` makes
the next read or write raise, like an unplugged USB adapter.
"""
from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
# 52 telemetry lines of the 20 September 2026 bench test at the 25 % limit
# (hardware/bench/20260920/ina_bypassed_NOT_motor_current.json), rewritten in
# the firmware's exact snprintf format; host-side fields dropped.
RECORDING = FIXTURES / "firmware_telemetry_20260920.txt"


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeSerial:
    def __init__(self) -> None:
        self.rx = b""
        self.written: list[bytes] = []
        self.closed = False
        self._fail = False

    # firmware -> Pi
    def feed_line(self, text: str) -> None:
        self.rx += text.encode("ascii") + b"\n"

    def feed_bytes(self, data: bytes) -> None:
        self.rx += data

    def feed_recording(self, path: Path = RECORDING) -> list[str]:
        lines = path.read_text().splitlines()
        for line in lines:
            self.feed_line(line)
        return lines

    def fail_next_io(self) -> None:
        self._fail = True

    # pyserial subset
    def read(self, size: int = 1) -> bytes:
        self._check()
        out, self.rx = self.rx[:size], self.rx[size:]
        return out

    def write(self, data: bytes) -> int:
        self._check()
        self.written.append(bytes(data))
        return len(data)

    def close(self) -> None:
        self.closed = True

    def _check(self) -> None:
        if self.closed:
            raise OSError("port closed")
        if self._fail:
            self._fail = False
            raise OSError("device disconnected")


class PortFactory:
    """open_port callable for SerialBridge: hands out FakeSerial objects, or fails while `absent`."""

    def __init__(self) -> None:
        self.ports: list[FakeSerial] = []
        self.absent = False

    def __call__(self) -> FakeSerial:
        if self.absent:
            raise OSError("no such device")
        p = FakeSerial()
        self.ports.append(p)
        return p

    @property
    def port(self) -> FakeSerial:
        return self.ports[-1]
