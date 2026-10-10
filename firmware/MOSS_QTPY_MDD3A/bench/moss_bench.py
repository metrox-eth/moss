"""First contact bench for the MOSS V0.4 base: send one command, log every telemetry line, summarise.
Usage: python moss_bench.py "test left 5" [seconds]
"""
import glob, json, sys, time, serial

cmd = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
port = [p for p in glob.glob("/dev/serial/by-id/*") if "QT_Py" in p][0]
s = serial.Serial(port, 115200, timeout=0.05)
time.sleep(0.3); s.reset_input_buffer()
s.write(b"zero\n"); time.sleep(0.3); s.reset_input_buffer()
s.write((cmd + "\n").encode())
t0 = time.time(); rows = []; other = []
buf = b""
while time.time() - t0 < secs:
    buf += s.read(4096)
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        try:
            rows.append((time.time() - t0, json.loads(line)))
        except Exception:
            other.append(line.decode("utf8", "replace"))
s.close()
print("replies:", other[:5])
print(f"{len(rows)} telemetry lines in {secs} s")
for t, r in rows[::2]:
    print(f"{t:4.2f}s mode={r['mode']} {r['reason']:<12} out={r['output_pct']} ticks={r['ticks']} bad={r['invalid_edges']} bus={r['bus_mV']} mV")
