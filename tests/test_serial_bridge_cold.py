"""Cold tests of moss_pi.serial_bridge: exact command bytes, telemetry parsing, deadman, reconnect."""
import pytest

from fake_serial import FakeClock, PortFactory
from moss_pi.serial_bridge import (Info, Reply, SerialBridge, Telemetry, format_drive, format_simple,
                                   parse_line)


def make():
    clock, ports = FakeClock(), PortFactory()
    bridge = SerialBridge(ports, clock=clock)
    bridge.tick()                      # opens the port, writes the initial stop
    ports.port.written.clear()
    return bridge, ports, clock


# ---------------------------------------------------------------- command lines

def test_drive_plus_10_plus_10_is_the_exact_firmware_line():
    assert format_drive(10, 10) == b"drive 10 10\n"


def test_drive_limits_and_signs_are_written_as_the_firmware_parses_them():
    assert format_drive(-25, 25) == b"drive -25 25\n"
    assert format_drive(0, 0) == b"drive 0 0\n"


@pytest.mark.parametrize("left,right", [(26, 0), (0, -26), (10.0, 10), (True, 0), ("10", 10), (None, 0)])
def test_out_of_contract_drive_is_refused_before_the_wire(left, right):
    with pytest.raises(ValueError):
        format_drive(left, right)


def test_simple_commands_and_nothing_else():
    assert [format_simple(c) for c in ("status", "stop", "zero", "arm")] == [b"status\n", b"stop\n", b"zero\n", b"arm\n"]
    for bad in ("test left 10", "drive", "reboot", "STOP"):
        with pytest.raises(ValueError):
            format_simple(bad)


# ---------------------------------------------------------------- roundtrip through the fake port

def test_arm_then_drive_10_10_reaches_the_port_byte_for_byte():
    bridge, ports, _ = make()
    assert bridge.arm() and bridge.drive(10, 10)
    assert ports.port.written == [b"arm\n", b"drive 10 10\n"]


def test_drive_without_arm_sends_nothing():
    bridge, ports, _ = make()
    assert bridge.drive(10, 10) is False
    assert ports.port.written == []


def test_first_line_on_a_new_link_is_stop():
    clock, ports = FakeClock(), PortFactory()
    bridge = SerialBridge(ports, clock=clock)
    bridge.tick()
    assert ports.port.written == [b"stop\n"] and not bridge.armed


# ---------------------------------------------------------------- deadman

def test_300_ms_of_silence_after_a_drive_produces_one_stop():
    bridge, ports, clock = make()
    bridge.arm(); bridge.drive(10, 10)
    ports.port.written.clear()
    clock.t = 0.299
    bridge.tick()
    assert ports.port.written == []            # 299 ms: still driving
    clock.t = 0.300
    bridge.tick()
    assert ports.port.written == [b"stop\n"]   # 300 ms: stop
    assert not bridge.armed
    clock.t = 5.0
    bridge.tick()
    assert ports.port.written == [b"stop\n"]   # once, not a flood


def test_drive_every_20_ms_keeps_the_deadman_quiet_for_2_s():
    bridge, ports, clock = make()
    bridge.arm()
    for i in range(100):
        clock.t = i * 0.020
        bridge.drive(5, 5)
        bridge.tick()
    assert b"stop\n" not in ports.port.written
    assert ports.port.written.count(b"drive 5 5\n") == 100


def test_after_a_deadman_stop_drive_needs_a_new_arm():
    bridge, ports, clock = make()
    bridge.arm(); bridge.drive(10, 10)
    clock.t = 0.5; bridge.tick()
    assert bridge.drive(10, 10) is False
    assert bridge.arm() and bridge.drive(10, 10)


def test_arm_expires_after_10_s_without_drive_like_the_firmware():
    bridge, ports, clock = make()
    bridge.arm()
    clock.t = 9.99; bridge.tick(); assert bridge.armed
    clock.t = 10.0; bridge.tick(); assert not bridge.armed
    assert bridge.drive(10, 10) is False


def test_any_err_reply_disarms_the_bridge_like_the_firmware():
    bridge, ports, clock = make()
    bridge.arm(); bridge.drive(10, 10)
    ports.port.feed_line("ERR invalid_command")
    bridge.tick()
    assert not bridge.armed and bridge.last_reply == Reply(ok=False, error="invalid_command")
    assert bridge.drive(10, 10) is False


# ---------------------------------------------------------------- reconnect

def test_lost_port_disarms_and_reopens_with_a_stop():
    bridge, ports, clock = make()
    bridge.arm(); bridge.drive(10, 10)
    ports.port.fail_next_io()
    assert bridge.drive(10, 10) is False       # write fails: port dropped
    assert not bridge.connected and not bridge.armed and ports.port.closed
    ports.absent = True
    clock.t = 1.0; bridge.tick()
    assert not bridge.connected                # device still gone: retry later
    ports.absent = False
    clock.t = 1.5; bridge.tick()
    assert not bridge.connected                # 1 s back-off after the failed attempt
    clock.t = 2.0; bridge.tick()
    assert bridge.connected and len(ports.ports) == 2
    assert ports.port.written == [b"stop\n"]
    assert bridge.drive(10, 10) is False       # re-arm required


def test_read_error_drops_the_port():
    bridge, ports, clock = make()
    ports.port.fail_next_io()
    bridge.tick()
    assert not bridge.connected


def test_close_sends_a_last_stop():
    bridge, ports, _ = make()
    first = ports.port
    bridge.close()
    assert first.written == [b"stop\n"] and first.closed


# ---------------------------------------------------------------- telemetry

def test_recorded_line_parses_to_known_values_in_physical_units():
    t = parse_line('{"ms":305602,"mode":2,"reason":"drive","target_pct":[25,0],"output_pct":[20,0],'
                   '"ticks":[-60,0],"invalid_edges":[0,0],"ina_ok":true,"bus_mV":11916,"shunt_uV":-700,"current_mA":null}')
    assert isinstance(t, Telemetry)
    assert t.mode_name == "drive" and t.reason == "drive"
    assert t.target_pct == (25, 0) and t.output_pct == (20, 0) and t.ticks == (-60, 0)
    assert t.bus_V == 11.916 and t.uptime_s == 305.602
    assert t.current_mA is None


def test_replies_and_other_lines():
    assert parse_line("OK") == Reply(ok=True)
    assert parse_line("ERR not_armed") == Reply(ok=False, error="not_armed")
    assert parse_line("MOSS V0.3 bench firmware; USB-UART 115200; limit 25%; type status") == \
        Info("MOSS V0.3 bench firmware; USB-UART 115200; limit 25%; type status")


@pytest.mark.parametrize("line", ['{"ms":1', '{"ms":1,"mode":0}', '{"ms":"1","mode":0,"reason":"x","target_pct":[0,0],'
                                  '"output_pct":[0,0],"ticks":[0,0],"invalid_edges":[0,0],"ina_ok":false,'
                                  '"bus_mV":null,"shunt_uV":null,"current_mA":null}', "{\x00}"])
def test_truncated_or_malformed_json_is_info_never_telemetry(line):
    assert isinstance(parse_line(line), Info)


def test_recorded_session_replays_in_order_through_the_bridge():
    bridge, ports, _ = make()
    lines = ports.port.feed_recording()
    seen = []
    bridge.add_listener(lambda text, parsed: seen.append(parsed))
    while ports.port.rx:
        bridge.tick()
    assert len(seen) == len(lines) == 52 and all(isinstance(p, Telemetry) for p in seen)
    assert [p.mode_name for p in seen[4:8]] == ["off", "ready", "ready", "drive"]
    last = seen[-1]
    assert last.mode_name == "off" and last.ticks == (-6049, -6163) and last.bus_V == 11.944


def test_a_line_split_across_reads_is_reassembled():
    bridge, ports, _ = make()
    seen = []
    bridge.add_listener(lambda text, parsed: seen.append(parsed))
    ports.port.feed_bytes(b"O")
    bridge.tick()
    ports.port.feed_bytes(b"K\r\nERR inv")
    bridge.tick()
    ports.port.feed_bytes(b"alid_command\n")
    bridge.tick()
    assert seen == [Reply(ok=True), Reply(ok=False, error="invalid_command")]


def test_real_pyserial_on_a_pseudo_terminal_reads_telemetry_and_writes_exact_bytes():
    """The one place pyserial itself runs: a Linux pty stands in for the USB-UART adapter."""
    pytest.importorskip("serial")
    import os
    import time

    from moss_pi.serial_bridge import open_serial

    if not hasattr(os, "openpty"):
        pytest.skip("no pty on this platform")
    master, slave = os.openpty()
    try:
        bridge = SerialBridge(lambda: open_serial(os.ttyname(slave)))
        bridge.tick()
        assert bridge.connected
        os.write(master, b'{"ms":1,"mode":0,"reason":"boot","target_pct":[0,0],"output_pct":[0,0],"ticks":[0,0],'
                         b'"invalid_edges":[0,0],"ina_ok":true,"bus_mV":12000,"shunt_uV":0,"current_mA":null}\n')
        deadline = time.monotonic() + 2.0
        while bridge.last_telemetry is None and time.monotonic() < deadline:
            bridge.tick(); time.sleep(0.01)
        assert bridge.last_telemetry is not None and bridge.last_telemetry.bus_V == 12.0
        bridge.arm(); bridge.drive(10, 10)
        time.sleep(0.05)
        assert os.read(master, 1024) == b"stop\narm\ndrive 10 10\n"
        bridge.close()
    finally:
        os.close(master)
        try:
            os.close(slave)
        except OSError:
            pass
