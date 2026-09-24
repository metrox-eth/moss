"""Cold tests of moss_pi.telemetry_log: every telemetry line, and only those, with a wall-clock time."""
import json

from fake_serial import FakeClock, PortFactory
from moss_pi.serial_bridge import SerialBridge
from moss_pi.telemetry_log import TelemetryLog


def test_recorded_session_is_logged_line_for_line_with_wall_time(tmp_path):
    wall = FakeClock(1790000000.0)
    log = TelemetryLog(tmp_path / "t.jsonl", wall_clock=wall)
    bridge = SerialBridge(PortFactory(), clock=FakeClock())
    bridge.add_listener(log.on_line)
    bridge.tick()
    port = bridge._port
    port.feed_line("MOSS V0.3 bench firmware; USB-UART 115200; limit 25%; type status")
    port.feed_line("OK")
    lines = port.feed_recording()
    port.feed_line("ERR invalid_command")
    while port.rx:
        wall.t += 0.2
        bridge.tick()
    log.close()

    records = [json.loads(r) for r in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert len(records) == 52 == log.count
    assert [r["telemetry"] for r in records] == [json.loads(line) for line in lines]
    assert records[0]["wall_time_s"] >= 1790000000.0
    assert all(b["wall_time_s"] >= a["wall_time_s"] for a, b in zip(records, records[1:]))


def test_log_appends_and_does_not_truncate(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text('{"earlier":true}\n')
    log = TelemetryLog(path, wall_clock=lambda: 1.5)
    from moss_pi.serial_bridge import parse_line
    line = ('{"ms":1,"mode":0,"reason":"boot","target_pct":[0,0],"output_pct":[0,0],"ticks":[0,0],'
            '"invalid_edges":[0,0],"ina_ok":false,"bus_mV":null,"shunt_uV":null,"current_mA":null}')
    log.on_line(line, parse_line(line))
    log.close()
    rows = path.read_text().splitlines()
    assert rows[0] == '{"earlier":true}'
    assert json.loads(rows[1]) == {"wall_time_s": 1.5, "telemetry": json.loads(line)}
