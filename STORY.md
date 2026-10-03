# The story so far

MOSS started with me cleaning my street by hand, two or three hours under the sun. In Thailand it rains a lot, and everything on the road ends up in the ocean. People go and clean the beaches as if the mess came from the sea; it comes from the streets. I didn't want to live in a dirty street, and I didn't want to burn cleaning under the tropical sun. So I built a robot.

The idea behind it is older than the robot. Years ago I printed an e-NABLE prosthetic hand, and I saw what happens when a design is free and a maker with a printer picks it up. If every maker with a workshop builds one or two small robots for their own neighbourhood, the litter problem gets solved everywhere at once. Parents and their kids, or any maker, build one over two or three weekends. There is electronics in it, programming, 3D printing, and at the end something useful rolls out the door.

## September 2026

**9 to 15 September.** The idea, said out loud on a bigger rover we already had: drive it in the street, pick up the trash, put it in a bin on the rover. I am fast with a bag. A robot will need time before it is autonomous and enduring. So the sooner we start, and the more of us there are, the better. At 4 am one night I gave Astra, my GPT agent, the components I had lying around, a Raspberry Pi, an SO-101 arm, and "have fun, you can use Fusion, make me a prototype of a robot that can carry this". Tracks, TPU, 3D printing and litter collection came in the next 45 minutes, in a handful of short messages. Since then the CAD is drawn in Codex, one precise instruction at a time, and checked in Fusion. On the 15th, a 40-second concept video, before a single part existed.

**16 to 19 September.** Two printers for three days. The bin and a track the first evening, the hull in black PETG on the 18th. By the 19th, 113 parts on the bench, shafts and bearings in bags next to them. On Discord, the first people showed up: one wants a robot for his yard and offers to design a board for the encoders, one has an SO-101 pair in Canada and wants a real use for cheap robots, one has never touched robotics and wants to clean beaches. Welcome onboard, we'll learn together.

**20 September.** Both motors turned on the bench, encoders counting. The same evening, the electronics went into the hull and the Jetson booted from the battery. I posted a 12-second clip of it, "MOSS is taking shape". Robit quoted it to his followers, and it went round a corner of Twitter: 49,000 views by morning, 110,000 the next day, a thousand new people following the build. That is when the project stopped being mine alone. The same day, the MOSS × Jev demo went up: Jev, TypeSafe AI's decision model, choosing every step of a pickup on physics recorded in MuJoCo, replayed in your browser.

**22 September.** First drive. Tracks on, the rover moving and turning on the floor under its own motors, still tethered.

**24 September.** The simulator went public, and the same day Jonathan Hawkins imported the MOSS body into his microduck-lab and started training a pick-up policy by reinforcement learning, 32 copies of the rover in parallel. First contributor from outside.

**26 September.** The arm. A standard SO-101 bolted on, with the NormaCore parallel-jaw gripper, widened to a 90 mm grip, and a camera in the hand. Folded over the bin, it looks like the video. A reader looked at the photo and said the shoulder looked weak; it became issue #2. The same day, a team in the Netherlands building a larger autonomous litter-picking robot, X17, got in touch: "we're building its bigger brother, let's connect".

**28 and 29 September.** NormaCore, whose gripper is on the robot, granted us hardware and became the first partner. Dimensional, who make dimOS, the software MOSS runs on, approved a hardware grant the next day. Chris Matthieu from RealSense saw MOSS roll and pointed us to their close-range update: depth from 12 cm with the camera we already had.

**30 September.** Dirac Robotics offered to build a calibrated simulation of MOSS, so that what works in MuJoCo has a chance of working on the floor.

## October 2026

**1 October.** V0.5, the CAD redrawn on the real robot, release candidate for the open source files, with a film to show it. The same evening, a call with Tnkr, who turn open source robots into kits: the parts in a box, with an assembly guide where you can look inside the robot.

**2 October.** Tnkr announced, waitlist open. Jonathan published his results: 87 grasps out of 88 in simulation.

**3 October.** V0.6 makes the hardware modular: Pi or Jetson, RealSense or Gemini, same chassis. And the "Meet the fam" card: OpenAI (Codex Physical Builds), Dimensional, NormaCore, Tnkr, Dirac Robotics, microduck-lab. We help each other.

## Next

The robot is being rebuilt with the V0.6 parts. The files come out after one test: a full battery emptied over 3 km on the beach, tracks still on, no bolt lost. No date. It is posted when it is real.
