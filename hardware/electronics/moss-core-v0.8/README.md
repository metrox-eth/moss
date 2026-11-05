# MOSS Core V0.8

**Next revision notes · 5 November 2026.** The [V0.7 prototype](../moss-core-v0.7/) proceeds through PCBWay review as submitted. The first milestone is simple: the board boots, MOSS drives, and the arm can pick something up. Use what happens on those first boards to decide which changes belong in V0.8.

| Observation on V0.7 | What to learn from the prototype |
| --- | --- |
| **Arm power (J5).** Keep one plug for the daisy-chained servos. The whole arm draws through a 4 mm length of 0.6 mm-wide copper. J5 is rated at 3 A per contact; the pack has a 15 A fuse. | Measure total arm current and connector temperature over repeated pickups, especially while the shoulder lifts and holds a load. Use that evidence to decide whether a wider trace or separate arm-branch protection would help. |
| **Red stop button (J8).** A short to ground on pin 1 can keep actuator power on when the button is pressed. A short on pin 2 can restore power on release. A separate contact inhibits track commands. | On clear ground, check that the tracks stop driving, measure how far the rover rolls, and confirm it stays stopped when the button is released. Check separately whether a servo resumes its previous move after a brief power interruption. |
| **Orange Pi and motor power.** The host is the **Zero 3W, 6 GB**. It shares the battery with the tracks and arm. | Measure voltage and current at the 5 V output (J20) with the hub and sensors attached while enabling the arm and starting or reversing the tracks. Watch for resets and battery-rail spikes during braking. |
| **Local decoupling (C155/U52).** C155's ground pad has 11.525 mm of track to the first ground via. | If the layout is reopened, look for a closer ground via and a shorter supply connection. The effect on U52 still needs a bench measurement. |

Two lower-priority questions from the review are whether the right motor path heats more than the left under the same load, and how the enable pin of the Orange Pi regulator (U60) behaves with its 499 kΩ pull-up.

For the next drawing pass, bring the off-page items on the USB power and encoder schematic sheets back into the printable area. The existing battery-trace stub and C21 silkscreen clip are recorded in the [V0.7 DRC report](../moss-core-v0.7/evidence/DRC.json).

Design references: [connector pinouts](../moss-core-v0.7/CONNECTORS.md) and [power and rearm behavior](../moss-core-v0.7/POWER_AND_REARM.md).
