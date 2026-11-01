# Independent bounded firmware review

**No outstanding blocking software or hardware mismatch was found in the requested scope.** The code is a commissioning candidate; neither this review nor its host tests is a physical robot/flash qualification.

`FINAL_SOURCE_HASHES.json` identifies the seven reviewed files by filename, independently of the sketch directory name. `final_snapshot/` contains those exact inputs. The later `firmware/`→`src/` relocation is acceptable only if these content hashes remain identical.

## Final delta results

- The 140-character, seven-ID `servo syncmove` command fits the final 256-byte line buffer and is parsed without truncation. Seven goals produce 58 parameter bytes and a 64-byte broadcast frame, with correct ID 254, opcode 0x83, register 41, seven-byte register span, byte order and checksum. Duplicate IDs, a one-ID group and an eight-ID group are rejected. Broadcast success is reported as transmitted with `acknowledged:false`, not as a measured successful movement.
- AIN3 is diagnostic GND and remains signed: small negative readings are retained. Both ADC endpoint saturations are rejected. Negative current-channel readings and an out-of-range measured rail invalidate samples; AIN2 remains the direct 3V3 reference for the unchanged 0.1 V/A ratiometric calculation.
- The actual `usbOpen()` function requires CDC open, TinyUSB mounted and not suspended. The actual `serviceTx()` makes one write attempt of at most 64 bytes, advances by the accepted count, and makes no retry when the transport accepts zero bytes. Its calls are finite; this does not quantify USB-task scheduling.
- The final UART adapter permits no packet over 64 bytes and waits for TX_DONE for at most 1.5 ms. The maximum group frame is 640 µs at 1 Mbaud/8N1. The buffer enable is high only during transmission. Broadcast sets completion without waiting for an ACK; unicast still validates response ID, checksum, status and size. Physical turnaround voltage/timing and servo return-status settings remain first-board checks.
- GPIO44 remains feedback input. The final ordering checks safety faults before evaluating expected drive feedback, so an actual latch/rail fault is not deliberately treated as an ordinary feedback delay. The LED now distinguishes explicit stop/boot from a fault reason; this changes indication only.
- Encoder initialization delay occurs before enabling SET1. Watchdog timing, new-arm token requirements, cleared targets and refusal of stale drive before rearming remain covered by the unchanged independent state probe.

## Executed evidence

Both probes consume the actual reviewed headers and run with AddressSanitizer and UndefinedBehaviorSanitizer:

| Probe | Result | Log |
| --- | --- | --- |
| `independent_state_probe.cpp` | 272 assertions passed | `final_run/test.log` |
| `independent_delta_probe.cpp` | 227 assertions passed | `final_delta_run/test.log` |

The USB function bodies in `usb_functions.inc` are extracted verbatim from the reviewed sketch by `prepare_delta_probe.py`; the second probe executes them with a bounded transport stub. It does not replace the target ESP32 build. Source snapshots, probes and logs are bound in `FINAL_REVIEW.json`.

To reproduce from this directory, passing the current sketch directory explicitly:

```sh
python3 prepare_delta_probe.py PATH_TO_SKETCH
bash run_independent_probe.sh PATH_TO_SKETCH final_run
bash run_independent_probe.sh PATH_TO_SKETCH final_delta_run "$PWD/independent_delta_probe.cpp"
```

The initial 128-byte parser observation was already superseded by 256 before the first source snapshot; it is not an outstanding finding. The executable 140-character case now confirms the corrected behavior.

Physical current calibration, motor direction signs, actual servo motion, rail transients, signal slew and real host/USB timing were not measured. The hardware latch inhibits new commands, not autonomous commands already stored in a servo. No firmware, PCB or circuit was modified by this reviewer.
