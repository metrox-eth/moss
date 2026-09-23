# Hardware V0.4 — development update

24 September 2026. The physical rover remains **V0.3**. **V0.4** is the next hardware revision, being developed from assembly feedback while the existing prototype is tested. It is not yet a printed, assembled or qualified replacement.

## Control electronics ordered

Two of each item below were ordered, providing two sets. Quantities in the first numeric column are for one rover. Prices are the builder's order prices, not a complete robot cost.

| Item | Per rover | Ordered | Unit USD |
|---|---:|---:|---:|
| [QT Py ESP32-S3, 8 MB Flash / no PSRAM, PID 5426](https://www.adafruit.com/product/5426) | 1 | 2 | 12.50 |
| [Terminal Block BFF, PID 6495](https://www.adafruit.com/product/6495) | 1 | 2 | 10.95 |
| [Snap-on enclosure, PID 6505](https://www.adafruit.com/product/6505) | 1 optional | 2 | 4.95 |
| [INA219 STEMMA QT, PID 904](https://www.adafruit.com/product/904) | 1 | 2 | 9.95 |
| [STEMMA QT / Qwiic JST-SH cable, 300 mm, PID 5384](https://www.adafruit.com/product/5384) | 1 | 2 | 1.25 |
| **One set, including enclosure** | | | **39.60** |

Two sets: **$79.20** in parts, **$21.83** shipping, **$101.03** order total before any separately collected import charges. Without the optional enclosure the parts used in one integrated hull cost **$34.65**. This is a control-electronics subtotal, not a revised total BOM.

The BFF provides screw terminals for the harness. Headers still need soldering to the QT Py; the wires themselves terminate in connectors or screw terminals. One STEMMA QT cable connects each INA219 to its controller. The QT Py and BFF have different I2C pin routes on this ESP32-S3 variant, so the firmware must match the connector actually used. The old DevKitC pin numbers are not a drop-in QT Py wiring map.

The INA219 remains a **battery-voltage monitor** in the present design. Its stock shunt measurement range is ±3.2 A; this update does not put the complete rover current through it or validate current-based battery monitoring.

Ordered is not received or tested. The existing V0.3 wiring and firmware remain the reference for the physical prototype until the new electronics are fitted and tested.

## Other selected changes

- One **Cytron MDD3A dual-channel driver**, ordered earlier, is selected to replace the two MD10C drivers in V0.4. The first-drive prototype still uses the MD10Cs. The MDD3A has not been validated on MOSS in this update; its purchase price is not supplied here.
- The **Waveshare Bus Servo Adapter (A) V1.1** remains the separate SO-101 servo interface. The General Driver for Robots is already removed from the selected architecture.
- A **30 cm USB-A to right-angle USB-C cable** is ordered for the RealSense D455f. USB3 operation and the actual plug envelope remain to be tested at delivery.
- Panel-mount **5.5 × 2.1 mm DC jack** selected for the charging connection. The supplied DC-022B drawing specifies an M8 × 1 mounting barrel. This is a connector provision, not a charging circuit.
- Four **40 × 10 × 5 mm magnets** are ordered to retain the bin. Their mounting pockets and retention arrangement are still to be designed.
- The fuse remains in the power path, in an **inline cable holder**. Removing the separate printed fuse-holder mount does not remove electrical protection or establish a final fuse rating.

## Current hull CAD

The latest local assembly is named `MOSS_Hull_V04_Cartes_INA90.step`. It includes the hull, electronics, battery envelope, motor supports and motor reference models. Its companion hull-only STEP/STL is `MOSS_hull_V04_cartes_INA90`.

- Jetson retains its original plastic base. The removable caddy is replaced by an integrated seat and retaining pieces, with a cable route on the USB side.
- Integrated mounting provision for the QT Py / BFF. The purchased snap-on enclosure is optional and is not the mounting interface used in this hull CAD.
- Cytron and Waveshare positions have been exchanged. The Waveshare is rotated 90 degrees for USB access; the INA219 and its mounting features are also rotated 90 degrees for wiring access.
- The existing battery measures **67 × 74 × 27 mm**. The blue **75 × 82 × 32 mm** volume is a candidate larger-pack envelope only, with wire and XT connector space. It establishes neither a purchased battery nor capacity or runtime.
- The **lower platform integrated into the hull beneath the arm** is still fixed. Making it detachable has been deferred.
- Motor-support fastening is designed from the outside through recessed M4 heads in the hull into captive M4 nuts in the supports. The local study uses standard M4 × 20 screws; final assembly access and printed fit still need validation.

The latest hull export passed local solid/mesh and clearance checks. Those checks are not physical assembly validation. The INA reference is an approximate model of the **existing module**, not proof of fit for the newly ordered Adafruit board. Its footprint, mount positions and STEMMA connectors must be reconciled before printing that revision. The motor reference model also does not certify the actual motor screw pattern or encoder/cable clearance.

Only the hull and explicitly requested component placements were advanced in this work. Unrelated printed parts were not silently replaced. The manufacturing files are still awaiting release review.

## Assembly feedback still to close

- Fit the second tensioner on each track and validate even tension. A track shortened by one tooth is a candidate for testing, not a validated new belt length.
- Add screw-head recesses in wheels and rollers.
- Use commonly available screw lengths and head types; do not require custom 26 mm screws or routine screw shortening in the released design.
- Keep the corrected flank geometry. The suspected tensioner conflict was partly due to trying the wrong rail; do not relocate the fourth fixing solely on that initial diagnosis.
- Validate the more continuous front cover / hull interface separately. No replacement cover is being released by this hull update.
- Finish the bin magnet retention, new INA mounting, real connector fit and the electronics/firmware migration before calling the V0.4 BOM reproducible.

## Animation

[V0.4 hardware tour and pickup animation](../media/video/MOSS_V04_Inside_and_Action_20260924.mp4) — 40 seconds, 1920 × 1080, 30 fps, silent.

The exterior moves out of frame, the camera orbits the current hull and components with readable labels, then the rover reassembles, rolls and picks up a can. This is a **scripted CAD presentation**, not footage of autonomous pickup, a Jev run or a new physical test. Exterior geometry is reused from the previous exploded view; the interior reflects the saved V0.4 assembly. The separate Jev / MuJoCo demo is unchanged.
