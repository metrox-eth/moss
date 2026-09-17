# Data

What we want is a robot that works. Data is how it gets there.

Proposed rules for MOSS builders:

1. Teleop demonstrations are recorded in the LeRobot dataset format, with the same camera names on every robot, so datasets can be pooled without rework.
2. Pooled datasets are published under an open license on Hugging Face. Anyone can train on them.
3. Each builder keeps the right to do what they want with their own recordings, including selling them. The pooled copy stays open.
4. The first policy trained on pooled data is evaluated on real litter, on a real roadside, and the numbers are published whether they are good or not.

The camera layout and the recording tooling will be fixed in this repository before the first pooled dataset exists.
