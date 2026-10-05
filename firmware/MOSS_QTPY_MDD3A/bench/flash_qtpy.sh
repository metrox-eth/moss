#!/bin/bash
# Flash the MOSS V0.4 firmware on the QT Py ESP32-S3 from the Jetson, through its native USB.
# Step 1: ask the running Arduino app to reboot into the ROM bootloader (DTR/RTS trick);
# step 2: write; step 3: reset out of the bootloader by toggling RTS with the port held open.
set -e
PY=~/vector-dimos/.venv/bin/python
cd ~/moss_fw_v04
port() { ls /dev/serial/by-id/ | grep -E "QT_Py|Espressif" | head -1 | sed 's|^|/dev/serial/by-id/|'; }
P=$(port)
if [[ "$P" == *QT_Py* ]]; then
  $PY -m esptool --chip esp32s3 --port "$P" --before default-reset --after no-reset chip-id >/dev/null 2>&1 || true
  sleep 3; P=$(port)
fi
echo "bootloader port: $P"
$PY -m esptool --chip esp32s3 --port "$P" --baud 921600 --before no-reset --after watchdog-reset write-flash -z \
  --flash-mode dio --flash-freq 80m --flash-size 8MB \
  0x0 MOSS_QTPY_MDD3A.ino.bootloader.bin 0x8000 MOSS_QTPY_MDD3A.ino.partitions.bin 0xe000 boot_app0.bin 0x10000 MOSS_QTPY_MDD3A.ino.bin 2>&1 | grep -E "Wrote|verified|rror"
$PY - <<PYEOF
import serial, time
s = serial.Serial("$P", 115200, timeout=0.1)
s.dtr = False; s.rts = True; time.sleep(0.1); s.rts = False
try:
    time.sleep(0.5); s.close()
except Exception: pass
PYEOF
sleep 4; ls /dev/serial/by-id/ | grep -E "QT_Py|Espressif"
