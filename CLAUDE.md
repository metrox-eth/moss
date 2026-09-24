# MOSS — working notes for coding agents

MOSS is a small open-source litter-picking rover. This repository is public. Keep it readable for a builder who has never seen it.

- **Software first, cold tests always.** Anything in `moss_dimos/` or a new `moss_pi/` package must run and be tested without the robot: fake serial, recorded telemetry, pure functions. A test passes only when a known input gives a known output in physical units.
- **The firmware contract is the source of truth.** Serial, 115200 baud, line-based commands (`status`, `stop`, `zero`, `arm`, `drive LEFT RIGHT` with -25..+25, `test left|right PERCENT`), JSON telemetry about every 200 ms. See `firmware/README.md`. Do not invent commands; propose firmware changes as a separate PR.
- **Motors never move by accident.** Every drive path needs an explicit arm step and a deadman; a lost link means stop.
- **Docs are for the reader, not a diary.** The README is the door: what it is, where it stands, how to enter. Details go to `docs/`. No order or delivery status anywhere; a state is what exists and what is validated.
- **Nothing private.** No names of third parties, no addresses, no keys, no internal context. Replacement-cost estimates, not receipts.
- **One PR per scoped change**, with what was tested and what remains a hypothesis stated in the description.
