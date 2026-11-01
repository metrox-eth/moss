# Core power/rearm update compatibility

The harness drawings and viewer retain PCB geometry from `7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14`. The power/rearm PCB is `456219f7eb97119b7e4328ed76f150012619131788f42d3a9d21fc4e40859cdb`.

The new board preserves all existing component positions, connector geometry, connector pin assignments, outline and mounting centres. The harness connection schedule and hull fixings therefore remain applicable. The eight small internal additions appear in the [current Core views](../README.md); the older harness viewer is not a rendering of those additions. [Geometry and interface evidence](../evidence/UPDATE_EQUIVALENCE.json). Existing fitted-wire tolerances and physical first-article checks remain necessary.

J11 is the intended main Cytron power connection. J2.5 and J11.2 share Core ground; a common ground inside the Cytron creates parallel return paths. Some power current may flow in the signal-ground wire. Keep the main supply pair low impedance and check the complete harness under load. Do not remove the signal reference ground without reviewing the interface. The two winding leads remain H-bridge outputs, not ground wires.
