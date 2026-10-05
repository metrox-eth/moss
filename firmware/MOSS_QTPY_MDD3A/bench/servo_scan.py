"""Scan a Feetech (SMS_STS) servo bus: ping every ID at 1 Mbps, then read model/position/voltage of each.
Usage: python servo_scan.py [port] [baud]
"""
import glob, sys, time, serial

port = sys.argv[1] if len(sys.argv) > 1 else [p for p in glob.glob("/dev/serial/by-id/*") if "Single_Serial" in p][0]
baud = int(sys.argv[2]) if len(sys.argv) > 2 else 1_000_000
s = serial.Serial(port, baud, timeout=0.02)

def packet(sid, instr, params=b""):
    body = bytes([sid, len(params) + 2, instr]) + params
    return b"\xff\xff" + body + bytes([(~sum(body)) & 0xFF])

def txrx(sid, instr, params=b"", want=6, wait=0.02):
    s.reset_input_buffer()
    pkt = packet(sid, instr, params)
    s.write(pkt); s.flush()
    t0 = time.time(); buf = b""
    while time.time() - t0 < wait:
        buf += s.read(64)
        if len(buf) >= len(pkt) + want: break
    if buf.startswith(pkt): buf = buf[len(pkt):]   # half-duplex echo
    i = buf.find(b"\xff\xff")
    return buf[i:] if i >= 0 else b""

def read_reg(sid, addr, n):
    r = txrx(sid, 0x02, bytes([addr, n]), want=6 + n)
    if len(r) >= 6 + n and r[2] == sid:
        return r[5:5 + n]
    return None

found = []
for sid in range(0, 254):
    r = txrx(sid, 0x01)
    if len(r) >= 6 and r[2] == sid:
        found.append((sid, r[4]))
print(f"port {port} @ {baud}: {len(found)} servo(s) answer:", [f for f, _ in found])
for sid, err in found:
    model = read_reg(sid, 3, 2); pos = read_reg(sid, 56, 2); volt = read_reg(sid, 62, 1); temp = read_reg(sid, 63, 1); torque = read_reg(sid, 40, 1)
    f = lambda b: int.from_bytes(b, "little") if b else None
    print(f"  ID {sid:3d}  model={f(model)}  pos={f(pos)}  volt={volt[0]/10 if volt else None} V  temp={temp[0] if temp else None} C  torque_on={torque[0] if torque else None}  err={err}")
s.close()
