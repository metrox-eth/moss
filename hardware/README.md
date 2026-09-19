# Hardware

Design in Fusion 360. The current prototype is **V0.3**, being assembled from its first print set (113 pieces, see `docs/printed_parts.md`). Fit problems are logged in `docs/assembly_feedback.md`: some are fixed on the prototype, the others wait for the next hardware revision, which has no number yet.

Manufacturing files (STL/STEP) are published here part by part once their validation is decided, with the fastener list (type, thread, length, head, quantity, what goes into PETG with inserts) and the sources they derive from (SO-101 arm, NormaCore gripper) with exact revisions and local changes. Until then, the photos in `media/`, the inventory and the BOM are the reference.

`bench/` holds the raw traces of the bench tests, one folder per date. Each trace is only what the build log says it is: the 20 September INA219 file is explicitly not a motor-current measurement.
