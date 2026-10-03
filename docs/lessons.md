# What we learned the hard way

One line each. What it changes for you.

1. **The INA219 reads battery voltage, not motor current.** The shunt is not in the motor line. Do not read its current field as if it were.
2. **The controller sits on a screw-terminal board.** Jumper wires make false contacts once the rover moves. Keep it that way.
3. **The RealSense needs the right-angle USB cable.** The straight plug does not clear the hull. It is a line in the BOM.
4. **Keep the arm plate where the CAD puts it.** The arm was moved to make room for the lidar and clear the bin; folded, the elbow already touches the bin.
5. **Weigh the real robot before trusting the model.** The prototype came in at 3.5 kg without the arm; the first simulator export said 6.14 kg. A number copied often enough starts to look like a measurement.
6. **Put the rover on blocks for the first run.** Every time the firmware or the wiring changes.
