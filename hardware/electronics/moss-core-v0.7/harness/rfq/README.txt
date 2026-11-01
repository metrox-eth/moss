MOSS Core V0.7 harness prototype quotation - 1 November 2026

PCB SHA256: 7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14
14 routes;42 custom wire segments;3 complete USB cable assemblies.

CAD lengths follow the relaxed connector wire-exit to wire-exit paths, including the service slack drawn. Prototype quote free span = longest modelled conductor + 20 mm, rounded up to 5 mm; target tolerance +/-5 mm. The assembler adds cut/strip, contact engagement and termination allowances. These are quotation estimates, not released cut lengths. Fit the first article before freezing the batch. Complete USB cables are selected commercially and are not cut to CAD length.

Supply H02 and nine-wire H03 form one sleeved Cytron cable ensemble with TWO Core terminations: J11 for supply and J2 for controls plus four winding outputs. H03 has no supply-positive conductor. J2.5 is signal ground; driver supply current uses J11. Leave J2.10 empty. Neither winding lead is ground.

Retain both six-wire pigtails supplied with Arduitronics RU00129. With power disconnected, trace each stock wire to the motor board's M1/M2, GND/VCC and C1/C2 markings. Record cavity numbers, wire gauge and insulation OD, then approve the factory wirelist. Device-end cavity numbering and OEM connector MPN are not established. Quote insulated factory transitions when the stock wire cannot be terminated directly with the specified Core contact. Never force 18 AWG into an unverified stock motor contact.

Read MOSS_CORE_V07_HARNESS_RFQ.pdf, HARNESS_SPECIFICATION.json, WIRELIST.csv, CONNECTIONS.md and INTERFACE_VERIFICATION.md together.
