# What we learned the hard way

One line each. What happened, and what it changes for you.

1. **Print the tracks with a 0.4 mm nozzle.** The 0.8 mm nozzle makes them too stiff to run. The track profile that works is shipped with the files.
2. **One tensioner per track is not enough.** The first drive showed uneven tension and slack. V0.5 has two per side; fit both.
3. **No jumper wires on a rover.** Dupont connections made false contacts once the rover moved. The controller sits on a screw-terminal board.
4. **The INA219 reads voltage, not motor current.** The shunt was never in the motor line. Do not read its current field as if it were.
5. **Motor-mount screws need access from outside.** We drilled through the hull after assembly. The mounts now have exterior-access heads.
6. **Standard screw lengths only.** No custom cutting. The fastener list is in the [BOM](../BOM.md).
7. **The RealSense needs a right-angle USB cable.** The straight plug does not clear the hull. The cable is a line in the BOM.
8. **Small magnets are enough for the bin.** 20 × 10 × 2 mm, two in the cover, two in the bin.
9. **The arm had to move to make room for the lidar and clear the bin.** Keep the arm plate where the CAD puts it; the elbow already touches the bin when the arm is folded.
10. **Weigh the real robot before trusting the model.** The prototype came in at 3.5 kg without the arm; the first simulator export said 6.14 kg. A number copied often enough starts to look like a measurement.
11. **Put the rover on blocks for the first run.** Every time the firmware or the wiring changes.
