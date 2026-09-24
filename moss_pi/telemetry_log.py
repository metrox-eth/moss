"""Append every firmware telemetry line to a JSONL file, with a wall-clock timestamp.

One JSON object per line:

    {"wall_time_s": 1790000000.123, "telemetry": {"ms": 305602, "mode": 2, ...}}

`wall_time_s` is the Pi's clock (Unix seconds, UTC) when the line was read;
`telemetry` is the firmware object exactly as decoded. OK/ERR replies and other
lines are not written. Each record is flushed, so a power cut loses at most the
line being written.

Run alone, it only listens: it sends `stop` on connect (see SerialBridge) and
nothing else, so it cannot move a motor.

    python -m moss_pi.telemetry_log --port /dev/ttyUSB0 --out moss_telemetry.jsonl
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Callable, TextIO

from .serial_bridge import Info, Reply, SerialBridge, Telemetry, open_serial


class TelemetryLog:
    """Listener for SerialBridge: `bridge.add_listener(log.on_line)`."""

    def __init__(self, path: str | Path, wall_clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self._clock = wall_clock
        self._fh: TextIO = self.path.open("a", encoding="utf-8")
        self.count = 0

    def on_line(self, line: str, parsed: Telemetry | Reply | Info) -> None:
        if not isinstance(parsed, Telemetry):
            return
        record = {"wall_time_s": self._clock(), "telemetry": parsed.raw}
        self._fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._fh.flush()
        self.count += 1

    def close(self) -> None:
        self._fh.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Log MOSS firmware telemetry to JSONL (listen only).")
    ap.add_argument("--port", required=True, help="serial device, e.g. /dev/ttyUSB0")
    ap.add_argument("--out", required=True, help="JSONL file, appended to")
    args = ap.parse_args(argv)

    log = TelemetryLog(args.out)
    bridge = SerialBridge(lambda: open_serial(args.port))
    bridge.add_listener(log.on_line)
    try:
        while True:
            bridge.tick()
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        log.close()
        print(f"{log.count} telemetry lines written to {args.out}")


if __name__ == "__main__":
    main()
