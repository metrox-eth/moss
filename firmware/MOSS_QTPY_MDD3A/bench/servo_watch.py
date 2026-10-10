"""Log which servo moves while someone moves the arm by hand (torque off). Ctrl-C or kill to stop.
Writes one line per movement event to the log path given as argv[1]."""
import glob, sys, time, serial
log = open(sys.argv[1], "a", buffering=1)
ids = [int(x) for x in sys.argv[2:]]
port = [p for p in glob.glob("/dev/serial/by-id/*") if "Single_Serial" in p][0]
s = serial.Serial(port, 1_000_000, timeout=0.01)
def packet(sid, instr, params=b""):
    body = bytes([sid, len(params) + 2, instr]) + params
    return b"\xff\xff" + body + bytes([(~sum(body)) & 0xFF])
def pos(sid):
    s.reset_input_buffer(); pkt = packet(sid, 0x02, bytes([56, 2])); s.write(pkt); s.flush()
    t0=time.time(); buf=b""
    while time.time()-t0 < 0.015: buf += s.read(64)
    if buf.startswith(pkt): buf = buf[len(pkt):]
    if len(buf) >= 8 and buf[2]==sid: return int.from_bytes(buf[5:7], "little")
    return None
base = {i: pos(i) for i in ids}
last = dict(base); lastlog = {i: 0 for i in ids}
log.write(f"# start {time.strftime('%H:%M:%S')} base={base}\n")
t0=time.time()
while True:
    for i in ids:
        p = pos(i)
        if p is None or last[i] is None: last[i] = p if p is not None else last[i]; continue
        if abs(p - last[i]) >= 25 and time.time() - lastlog[i] > 0.5:
            log.write(f"{time.time()-t0:7.1f}s  ID {i:3d} moved  {last[i]} -> {p}\n"); lastlog[i] = time.time()
        last[i] = p
    time.sleep(0.02)
