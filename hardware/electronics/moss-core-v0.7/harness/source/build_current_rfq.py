"""Build the local 2026-11-01 harness RFQ/docs from current route and PCB evidence.

Run with the bundled document Python. This writes only output/rfq and output/docs.
It deliberately refuses the superseded 20-route geometry.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import sys
from datetime import datetime, timezone
from xml.sax.saxutils import escape

H = Path(__file__).resolve().parents[1]
ROOT = H.parent
CORE = ROOT if (ROOT / "electrical/MOSS_Core_V07_Prototype.kicad_pcb").is_file() else ROOT / "current_prototype"
OUT = H / "output/rfq"
DOCS = H / "output/docs"
BOARD_HASH = "7d88c146a2482b4d89a26b8dbafe18132ae649e58c58671ddaed233b6ab8bc14"
EXPECTED = {"H01": 2, "H02": 2, "H03": 9, "H04": 6, "H05": 6,
            "H08_chassis": 4, "H08_lid": 4, "O01": 3, "O02": 2,
            "O03_left": 2, "O03_right": 2, "U01": 1, "U02": 1, "U03": 1}
DATE = "2026-11-01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

SOURCES = [
 ("S1", "Molex 43025-0600, six-way cable housing", "https://www.molex.com/en-us/products/part-detail/430250600"),
 ("S2", "Molex 43025-1000, ten-way cable housing", "https://www.molex.com/en-us/products/part-detail/430251000"),
 ("S3", "Molex 43030-0038, 18 AWG female contact", "https://www.molex.com/en-us/products/part-detail/430300038"),
 ("S4", "Molex 43030-0001, 20-24 AWG female contact, reel", "https://www.molex.com/en-us/products/part-detail/430300001"),
 ("S5", "Molex 43030-0007, loose-piece packaging alternative", "https://www.molex.com/en-us/products/part-detail/430300007"),
 ("S6", "Molex 63828-0200 hand-tool scope and crimp data", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/applicationtoolingspecificationpdf/638/63828/ATS-638280200-001.pdf"),
 ("S7", "Molex 63819-0000 hand-tool scope and crimp data", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/applicationtoolingspecificationpdf/638/63819/ATS-638190000-001.pdf"),
 ("S8", "Molex pre-crimped leads overview", "https://www.molex.com/content/dam/molex/molex-dot-com/en_us/pdf/datasheets/987651-2631.pdf"),
 ("S9", "Arduitronics RU00129 motor kit and supplied cable", "https://www.arduitronics.com/product/6047/"),
 ("S10", "Cytron MDD10A official product/manual", "https://www.cytron.io/p-10amp-5v-30v-dc-motor-driver-2-channels"),
 ("S11", "Yijia LA16 catalogue: two independent changeover contacts", "https://yijiabutton.com/wp-content/uploads/2023/10/28.-YJ-LA16-Specification.pdf"),
 ("S12", "Molex PicoBlade 51047/51021 mating drawing", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/510/51047/510470400_sd.pdf"),
 ("S13", "JST SH, six-position STOP housing/contact", "https://www.jst-mfg.com/product/pdf/eng/eSH.pdf"),
 ("S14", "JST PH, speaker housing/contact", "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf"),
 ("S15", "JST XH, fan housings/contacts", "https://www.jst-mfg.com/product/pdf/eng/eXH.pdf"),
 ("S16", "Molex 5264 arm housing drawing", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/526/5264/050375023_sd.pdf"),
 ("S17", "Molex 5263 arm contact drawing", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/526/5263/008701039_sd.pdf"),
 ("S18", "Hoco HB1: four USB-A sockets and 80 cm captive lead", "https://hocotech.com/product/mobile-accessories/cables/hubs-organizers/usb-hub-hb1-four-ports-usb-2-0-charging-and-data-sync/"),
 ("S19", "Molex Micro-Fit current derating, populated circuits", "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf"),
 ("S20", "Phoenix 1715721 supply terminal block", "https://www.phoenixcontact.com/en-pc/products/pcb-terminal-block-mkds-15-2-508-1715721"),
 ("S21", "AMASS XT30U cable connectors", "https://www.china-amass.com/biao/649.html"),
]

# Core pin, exact endpoint function, AWG, Core contact (empty for screw/solder ends).
WIRE_MAP = {
 "H01": [("J10", "1", "Fused battery harness negative", 16, "XT30 solder cup"), ("J10", "2", "Fused battery harness positive", 16, "XT30 solder cup")],
 "H02": [("J11", "1", "Cytron POWER +", 16, "Sized ferrule"), ("J11", "2", "Cytron POWER -", 16, "Sized ferrule")],
 "H03": [("J2", str(i), dest, 24 if i <= 5 else 18, "43030-0001" if i <= 5 else "43030-0038") for i, dest in enumerate(["Cytron PWM1", "Cytron DIR1", "Cytron PWM2", "Cytron DIR2", "Cytron control GND", "Cytron M1A", "Cytron M1B", "Cytron M2A", "Cytron M2B"], 1)],
 "H04": [("J3", str(i), dest, 18 if i <= 2 else 24, "43030-0038" if i <= 2 else "43030-0001") for i, dest in enumerate(["Left stock motor pigtail M1", "Left stock motor pigtail M2", "Left encoder GND", "Left encoder VCC (switched 3.3 V)", "Left encoder C1 / channel A", "Left encoder C2 / channel B"], 1)],
 "H05": [("J4", str(i), dest, 18 if i <= 2 else 24, "43030-0038" if i <= 2 else "43030-0001") for i, dest in enumerate(["Right stock motor pigtail M1", "Right stock motor pigtail M2", "Right encoder GND", "Right encoder VCC (switched 3.3 V)", "Right encoder C1 / channel A", "Right encoder C2 / channel B"], 1)],
 "H08_chassis": [("J8", p, f"X08 chassis cavity {i}", 28, "SSH-003T-P0.2-H") for i, p in enumerate(["1", "2", "5", "6"], 1)],
 "H08_lid": [("X08", str(i), dest, 28, "50133-8000") for i, dest in enumerate(["STOP C1", "STOP NC1", "STOP C2", "STOP NC2"], 1)],
 "O01": [("J5", str(i), dest, 22, "08-70-1040") for i, dest in enumerate(["Arm DATA", "Arm switched battery +", "Arm GND"], 1)],
 "O02": [("J7", str(i), dest, 24, "SPH-002T-P0.5S") for i, dest in enumerate(["Speaker +", "Speaker -"], 1)],
 "O03_left": [("J14", "1", "Left fan +", 26, "SXH-001T-P0.6"), ("J14", "2", "Left fan -", 26, "SXH-001T-P0.6")],
 "O03_right": [("J15", "1", "Right fan +", 26, "SXH-001T-P0.6"), ("J15", "2", "Right fan -", 26, "SXH-001T-P0.6")],
}
STOP_NETS = ["ESTOP_CUT_SOURCE", "ESTOP_CUT_RETURN", "ESTOP_STATUS_SOURCE", "ESTOP_STATUS_RAW"]
WIRE_SPEC = {"H01": "16 AWG candidate; retain suitable existing fused battery lead",
 "H02": "16 AWG candidate; retain separately sized Cytron supply conductors",
 "H03": "4 x 18 AWG winding + 5 x 24 AWG controls",
 "H04": "2 x 18 AWG winding + 4 x 24 AWG encoder",
 "H05": "2 x 18 AWG winding + 4 x 24 AWG encoder",
 "H08_chassis": "28 AWG; insulation OD 0.50-0.80 mm", "H08_lid": "28 AWG; insulation OD 0.50-0.80 mm",
 "O01": "22 AWG; OD 1.15-1.90 mm; optional adapter", "O02": "24 AWG; OD 0.80-1.50 mm; optional adapter",
 "O03_left": "26 AWG; OD 0.90-1.90 mm; optional adapter", "O03_right": "26 AWG; OD 0.90-1.90 mm; optional adapter",
 "U01": "Complete USB-C to USB-C power cable, 5 V / 3 A",
 "U02": "Complete USB-A to USB-C data cable", "U03": "HB1 captive USB-A lead + USB-C OTG adapter"}
PARTS = [
 ["J2", "1", "Molex 43025-1000", "10-way housing; fit cavities 1-9; cavity 10 empty"],
 ["J3/J4", "2", "Molex 43025-0600", "6-way housings; six contacts each"],
 ["Micro-Fit power", "8", "Molex 43030-0038", "18 AWG: 4 in J2 + 2 in each motor housing"],
 ["Micro-Fit signals", "13", "Molex 43030-0001", "24 AWG: 5 in J2 + 4 in each motor housing"],
 ["J8", "1 + 4", "SHR-06V-S + SSH-003T-P0.2-H", "Six-position JST SH housing; contacts 1/2/5/6 only"],
 ["X08 chassis", "1 + 4", "51021-0400 + 50058-8000", "PicoBlade female; 28 AWG, OD 0.50-0.80 mm"],
 ["X08 lid", "1 + 4", "51047-0400 + 50133-8000", "PicoBlade male; same circuit numbers 1-4"],
 ["Motor device ends", "2", "Supplied Arduitronics RU00129 pigtails", "Retain original six-way plugs; trace and record functions"],
 ["Cytron device end", "1 set", "Supplied 5-way control lead + screw terminations", "Match printed PWM1/DIR1/PWM2/DIR2/GND and M1A/B/M2A/B"],
 ["J11 supply", "2", "Ferrules sized to selected supply wire", "Existing Phoenix 1715721 PCB block; one wire per cavity"],
 ["J10 extension", "If needed", "AMASS XT30U-F / XT30U-M", "Retain external 15 A pack fuse; omit extension if existing lead reaches"],
 ["STOP button", "Separate option", "Yijia YJ-LA16-22ZS/A", "Red, non-illuminated, two independent NC contacts"],
 ["Arm adapter O01", "Optional", "50-37-5033 + 3 x 08-70-1040", "Mates vertical Molex 22-03-5035; retain existing arm daisy chain"],
 ["Speaker O02", "Optional", "PHR-2 + 2 x SPH-002T-P0.5S", "Mates vertical JST B2B-PH-K-S(LF)(SN)"],
 ["Fans O03", "Optional, two", "XHP-2 + 2 x SXH-001T-P0.6 each", "Mates JST B2B-XH-A(LF)(SN); verify actual fan polarity"],
]
LENGTH_BASIS = ("CAD lengths follow the relaxed connector wire-exit to wire-exit paths, including the service slack drawn. "
 "Prototype quote free span = longest modelled conductor + 20 mm, rounded up to 5 mm; target tolerance +/-5 mm. "
 "The assembler adds cut/strip, contact engagement and termination allowances. These are quotation estimates, not released cut lengths. "
 "Fit the first article before freezing the batch. Complete USB cables are selected commercially and are not cut to CAD length.")
MOTOR_POLICY = ("Retain both six-wire pigtails supplied with Arduitronics RU00129. With power disconnected, trace each stock wire to the motor board's M1/M2, GND/VCC and C1/C2 markings. "
 "Record cavity numbers, wire gauge and insulation OD, then approve the factory wirelist. Device-end cavity numbering and OEM connector MPN are not established. "
 "Quote insulated factory transitions when the stock wire cannot be terminated directly with the specified Core contact. Never force 18 AWG into an unverified stock motor contact.")
CYTRON_POLICY = ("Supply H02 and nine-wire H03 form one sleeved Cytron cable ensemble with TWO Core terminations: J11 for supply and J2 for controls plus four winding outputs. "
 "H03 has no supply-positive conductor. J2.5 is signal ground; driver supply current uses J11. Leave J2.10 empty. Neither winding lead is ground.")
DIY_POLICY = ("A factory-terminated kit avoids maker crimping. For a small DIY quantity, 43030-0007 is Molex's bagged loose-piece alternative to reel 43030-0001 for 20-24 AWG. "
 "Use 63828-0200 for the listed 18 AWG / 43030-0038 combination and 63819-0000 for its listed 20-30 AWG contacts. "
 "The 18 AWG tool specifies optimal insulation OD 1.60-1.85 mm; the 20-24 AWG tool scope specifies 1.42-1.85 mm. "
 "Record the exact wire and measure insulation OD; AWG alone does not establish crimp compatibility. Thick silicone wire may not fit. "
 "Pre-crimped leads are another documented option, but verify their exact terminal, gauge, insulation and length; no specific pre-crimp lead MPN is selected here.")


def mdtable(head, rows):
    return "\n".join(["| " + " | ".join(map(str, head)) + " |", "| " + " | ".join(["---"] * len(head)) + " |"] +
                     ["| " + " | ".join(str(x).replace("|", "/") for x in r) + " |" for r in rows])


def load_inputs():
    board = CORE / "electrical/MOSS_Core_V07_Prototype.kicad_pcb"
    assert sha(board) == BOARD_HASH, "Current PCB differs from final 7d88 contract"
    check_path = H / "evidence/INDEPENDENT_CONNECTOR_MAP_20261101.json"
    if not check_path.exists():
        check_path = ROOT / "harness_refresh_20261101/INDEPENDENT_CONNECTOR_MAP.json"
    check = json.loads(check_path.read_text())
    assert check["pcb_sha256"] == BOARD_HASH and check["status"].startswith("PASS_")
    assert check["connector_count"] == 12 and check["pins_checked"] == 76
    pins = {(p["ref"], p["pin"]): p for p in check["pins"]}
    route_path = H / "output/ROUTE_LENGTHS.json"
    route_bytes = route_path.read_bytes()
    data = json.loads(route_bytes)
    data["_source_sha256"] = hashlib.sha256(route_bytes).hexdigest()
    assert datetime.fromtimestamp(route_path.stat().st_mtime).date().isoformat() >= DATE, "ROUTE_LENGTHS.json is stale; wait for current rebuild"
    assert {r["id"]: r["conductors"] for r in data["routes"]} == EXPECTED, "Expected exactly the current 14 routes and conductor counts"
    for ref, pin in [("J2", "10"), ("J8", "3"), ("J8", "4")]:
        assert pins[(ref, pin)]["net"] is None
    assert not any(p["ref"] in ["J12", "J13"] for p in check["pins"])
    return data, pins, check_path, route_path


def build_spec(data, pins, check_path, route_path):
    rows = []
    wires = []
    for r in data["routes"]:
        assert len(r["individual_wire_lengths_mm"]) == r["conductors"]
        longest = max(r["individual_wire_lengths_mm"])
        row = {"id": r["id"], "function": r["label"], "conductors": r["conductors"],
               "kind": "complete_standard_usb_assembly" if r["id"].startswith("U") else "custom_wire_route",
               "cad_centreline_mm": r["centreline_mm"], "cad_individual_wire_lengths_mm": r["individual_wire_lengths_mm"],
               "cad_longest_conductor_mm": longest,
               "visual_wire_ods_mm": r.get("wire_ods_mm", [r.get("wire_od_mm")] * r["conductors"]),
               "visual_sleeve_outer_diameter_mm": r.get("sleeve_outer_diameter_mm"),
               "power_branch_control_points_mm": r.get("power_branch_points_mm"),
               "power_branch_visual_sleeve_outer_diameter_mm": 5.3 if "power_branch_points_mm" in r else None,
               "prototype_free_span_mm": None if r["id"].startswith("U") else int(math.ceil((longest + 20) / 5) * 5),
               "wire": WIRE_SPEC[r["id"]], "notes": r.get("notes", "")}
        rows.append(row)
        for n, (ref, cavity, destination, awg, contact) in enumerate(WIRE_MAP.get(r["id"], []), 1):
            net = STOP_NETS[n-1] if ref == "X08" else pins[(ref, cavity)]["net"]
            assert net is not None
            wires.append({"route": r["id"], "wire": n, "core_or_inline_connector": ref, "cavity": cavity,
                          "net": net, "device_function": destination, "awg": awg,
                          "core_or_inline_contact": contact, "quote_free_span_mm": row["prototype_free_span_mm"],
                          "cad_wire_length_mm": r["individual_wire_lengths_mm"][n-1],
                          "visual_wire_od_mm": row["visual_wire_ods_mm"][n-1],
                          "device_cavity": "TRACE_FIRST_ARTICLE" if r["id"] in ["H04", "H05"] else "NAMED_ENDPOINT",
                          "status": "PROTOTYPE_FUNCTION_MAP_NOT_RELEASED_CUT_SCHEDULE"})
    assert len(wires) == 42
    assert sum(w["core_or_inline_contact"] == "43030-0038" for w in wires) == 8
    assert sum(w["core_or_inline_contact"] == "43030-0001" for w in wires) == 13
    assert len({(w["core_or_inline_connector"], w["cavity"]) for w in wires if w["core_or_inline_connector"] != "X08"}) == 38
    return {"title": "MOSS CORE V0.7 - Harness prototype RFQ", "date": DATE,
            "status": "PROTOTYPE_QUOTATION_NOT_PRODUCTION_RELEASE", "board_sha256": BOARD_HASH,
            "connector_map_sha256": sha(check_path), "route_lengths_sha256": data["_source_sha256"],
            "route_lengths_modified_utc": datetime.fromtimestamp(route_path.stat().st_mtime, timezone.utc).isoformat(),
            "connector_count": 12, "connector_pins_checked": 76, "route_count": 14,
            "custom_wire_count": 42, "standard_usb_assembly_count": 3, "quantities_kits": [2, 10, 50, 100],
            "length_basis": LENGTH_BASIS, "cables": rows, "wirelist": wires,
            "connector_parts": PARTS, "motor_policy": MOTOR_POLICY, "cytron_policy": CYTRON_POLICY,
            "diy_policy": DIY_POLICY, "sources": [{"id": k, "label": t, "url": u} for k, t, u in SOURCES],
            "limits": ["PCB/schematic pin map checked statically; no physical harness test performed.",
                       "Motor pigtail cavity/function map, wire dimensions and factory transition process remain first-article records.",
                       "Mating bodies, cable bend/access, strain relief and closed/open-lid routing need a physical fit check.",
                       "No exact manufacturer STEP was obtained for 43025-0600/1000; visual housings are dimensioned references, not certified mating geometry.",
                       "The previous film is historical and does not describe this 14-route revision."]}


def make_docs(spec, pins):
    rows = spec["cables"]
    route_table = mdtable(["Route", "Function", "Wires / cable", "CAD centreline mm", "Quote free span mm"],
                         [[r["id"], r["function"], r["conductors"], r["cad_centreline_mm"], r["prototype_free_span_mm"] or "Complete cable"] for r in rows])
    connections = [(ref, "; ".join(f"{p['pin']} {p['function']} ({p['net'] or 'NO WIRE'})" for p in pins.values() if p["ref"] == ref and p["pin"].isdigit()))
                   for ref in ["J10", "J11", "J2", "J3", "J4", "J5", "J7", "J8", "J14", "J15"]]
    conn = "# Where the cables go\n\nUpdated 1 November 2026 for PCB `" + BOARD_HASH + "`. Twelve external PCB connectors; fourteen routed paths.\n\n"
    conn += "J3 is the complete left motor cable and J4 is the complete right motor cable, viewed in the rover's forward-driving direction. Each has six wires.\n\n" + CYTRON_POLICY + "\n\n"
    conn += mdtable(["Core connector", "Numbered cavities"], connections) + "\n\n"
    conn += "## USB\n\nU01: Core J20 to Orange Pi POWER, complete C-to-C 5 V/3 A cable. U02: HB1 downstream to Core J1, complete A-to-C data cable. U03: Orange Pi DATA through a USB-C OTG adapter to the HB1 captive USB-A upstream lead. Hub downstream sockets serve Core, wrist camera, navigation camera and LiDAR. The HB1 has an 800 mm captive lead; only the routed portion is modelled. Store excess cable clear of fans and moving parts.\n\n"
    conn += "## STOP and lid disconnect\n\nJ8.1/2 connect to C1/NC1 and J8.5/6 to C2/NC2. Cavities 3 and 4 remain empty, with no contacts or wires. X08 is PicoBlade 51021-0400/51047-0400 with 50058-8000/50133-8000 contacts. Map J8.1/2/5/6 to X08 circuits 1/2/3/4, straight through. Use 28 AWG with insulation OD 0.50-0.80 mm. The connector is friction-retained; hold both housings when disconnecting. Only the STOP tail moves with the lid.\n\n"
    conn += "## Motor device ends\n\n" + MOTOR_POLICY + "\n\nThe current shunts remain on Core: Cytron M1A -> J2.6 -> left shunt -> J3.1; M1B -> J2.7 -> J3.2. Right side: M2A -> J2.8 -> right shunt -> J4.1; M2B -> J2.9 -> J4.2. J3/J4.3 is encoder GND, .4 is switched 3.3 V, .5 channel A/C1 and .6 channel B/C2. Neither .1 nor .2 is ground.\n\n"
    conn += "Speaker J7 has two driven amplifier outputs. Fans J14/J15 use fused 3S battery positive and GND, up to 12.6 V; they are not regulated 12 V outputs. J5 is one bus for the whole arm, not one connector per servo.\n"
    verification = "# Harness interface verification\n\nUpdated 1 November 2026. PCB `" + BOARD_HASH + "`.\n\n## Checked evidence\n\nThe independent connector-map check matched all 76 physical connector pins across 12 connectors between PCB, schematic and circuit contract. This is a static check, not a cable or powered test. Core motor/driver housing selections are Molex 43025-0600 and 43025-1000, mating with the PCB's 43045-0612 and 43045-1012.\n\n"
    verification += "## Selected Micro-Fit wire and contacts\n\n" + mdtable(["Circuits", "Wire", "Contact", "Installed contacts per kit"], [["Motor winding leads", "18 AWG; tool optimum OD 1.60-1.85 mm", "43030-0038", "8"], ["Encoder/control", "24 AWG; tool scope OD 1.42-1.85 mm", "43030-0001", "13"]]) + "\n\n" + DIY_POLICY + "\n\n"
    verification += "## Physical motor pin map remains to be recorded\n\n" + MOTOR_POLICY + "\n\nThe distributor SKU identifies the supplied motor kit; it does not establish the motor connector's manufacturer or exact part number. The six-wire Core assignment is fixed; the stock device-side cavity assignment is pending continuity tracing.\n\n"
    verification += "## STOP\n\nA new documented switch option is Yijia YJ-LA16-22ZS/A, red and non-illuminated, with two independent changeover contacts; use C1-NC1 and C2-NC2. An existing unmarked button can be retained only after identifying two independent NC pairs by continuity. Six tabs alone do not prove the contact arrangement. NO terminals remain unused and insulated. The 51021/51047 PicoBlade inline pair and 28 AWG OD 0.50-0.80 mm are retained.\n\n"
    verification += "## First article records\n\n- Record the stock motor cavity/function map, gauge, insulation OD and factory transitions for both motors.\n- Check all numbered cavities and polarity. Keep J2.10 and J8.3/4 empty.\n- Record continuity and isolation of both STOP loops when released, pressed and unplugged; check isolation between loops.\n- Fit the assembled loom with the cover closed and opened; verify connector seating, wire exit, bend radius, strain relief, fan clearance and HB1 excess cable storage.\n- Check encoder counts/direction against an independent rotation reference during forward/reverse operation and repeated loaded reversals; inspect for resets, missed/extra counts and supply dips. This test is planned, not performed.\n- Verify load, startup, temperature and voltage drop on the final wires/crimps. The driver channel rating does not establish the complete harness rating.\n- Freeze the manufacturing cut/strip schedule only after these checks.\n\n"
    verification += "## Geometry limits\n\nNo manufacturer STEP/IGES was obtained for the cable housings. The scene uses dimensioned visual references; actual mating fit, latch operation, insertion access and cable bend remain unverified. Published current header mated height is 17.64 mm; the older family drawing reports 17.56 mm. The latter is not silently treated as the same datum. Native PCB header CAD is retained.\n"
    readme = "# MOSS CORE V0.7 - current harness study\n\nUpdated 1 November 2026 for PCB `" + BOARD_HASH + "`.\n\nThe current model has **14 routed paths**, including complete six-wire left/right motor cables, a nine-wire driver link, the separate two-wire driver supply, two STOP halves, optional arm/speaker/fan adapters and three complete USB cable assemblies. The custom route schedule contains 42 wire segments; the three USB assemblies are counted as cables, not as individual USB conductors.\n\n" + CYTRON_POLICY + "\n\n"
    readme += "## Current review files\n\n- MOSS_HARNESS_VIEWER.html: self-contained offline viewer.\n- MOSS_HARNESS_ASSEMBLY.glb and MOSS_HARNESS_ONLY.glb: meshes for the current scene.\n- ROUTE_LENGTHS.json: current modelled route/conductor lengths and assumptions.\n- rfq/MOSS_CORE_V07_HARNESS_RFQ.pdf: dated prototype quotation package.\n- rfq/HARNESS_SPECIFICATION.json and rfq/WIRELIST.csv: same functional wiring schedule.\n- CONNECTIONS.md and INTERFACE_VERIFICATION.md: wiring and first-article requirements.\n\nOnly the STOP tail follows the removable lid. The arm route remains with the chassis. Sleeve sizes, tie access, retained motor pigtails and complete USB lead storage still need physical fit checks. Any historical film is superseded for this revision; use the current viewer and dated RFQ.\n\n## Lengths\n\n" + LENGTH_BASIS + "\n\nH03's centreline measures the common trunk only; its individual conductor lengths include the fan-out. Use the individual wire lengths for the prototype span calculation.\n\n" + route_table + "\n\n## Visible wire and sleeve dimensions\n\nThe model shows 18 AWG winding wires at OD 1.8 mm and 24 AWG control/encoder wires at OD 1.5 mm. H03's common-trunk sleeve envelope is about 7.1 mm OD and its four-output power-branch sleeve is 5.3 mm OD; each complete six-wire motor sleeve is about 6.1 mm OD. These are visual routing dimensions; supplier wire and sleeve dimensions require prototype confirmation. The selected hand-tool processes specify wire insulation OD 1.60-1.85 mm for 18 AWG and 1.42-1.85 mm for 24 AWG.\n\n## Connector and workmanship limits\n\n" + MOTOR_POLICY + "\n\n" + DIY_POLICY + "\n\nThe mesh display's colours and wire order are illustrations. Read cavity numbering from the exact connector drawing and continuity-check the stock device leads. This study does not claim completed physical qualification or manufacturer cable-housing CAD.\n"
    for folder in [OUT, DOCS]:
        folder.mkdir(parents=True, exist_ok=True)
    (DOCS / "CONNECTIONS.md").write_text(conn)
    (DOCS / "INTERFACE_VERIFICATION.md").write_text(verification)
    (DOCS / "README_CAD.md").write_text(readme)
    (DOCS / "README.md").write_text(readme)
    (OUT / "INTERFACE_VERIFICATION.md").write_text(verification)
    (OUT / "CONNECTIONS.md").write_text(conn)
    (OUT / "SOURCES.md").write_text("# Manufacturer and supplier sources\n\n" + "\n".join(f"- [{k}: {t}]({u})" for k, t, u in SOURCES) + "\n")
    (OUT / "HARNESS_SPECIFICATION.json").write_text(json.dumps(spec, indent=2) + "\n")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(spec["wirelist"][0])); writer.writeheader(); writer.writerows(spec["wirelist"])
    (OUT / "WIRELIST.csv").write_text(buf.getvalue())
    (DOCS / "WIRELIST.csv").write_text(buf.getvalue())
    (OUT / "README.txt").write_text("MOSS Core V0.7 harness prototype quotation - 1 November 2026\n\nPCB SHA256: " + BOARD_HASH + "\n14 routes;42 custom wire segments;3 complete USB cable assemblies.\n\n" + LENGTH_BASIS + "\n\n" + CYTRON_POLICY + "\n\n" + MOTOR_POLICY + "\n\nRead MOSS_CORE_V07_HARNESS_RFQ.pdf, HARNESS_SPECIFICATION.json, WIRELIST.csv, CONNECTIONS.md and INTERFACE_VERIFICATION.md together.\n")


def make_pdf(spec, pins):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    W, HH = landscape(A4)
    width = W - 68
    ink = colors.HexColor("#17333e")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TextM", fontName="Helvetica", fontSize=9.5, leading=12.2, textColor=ink, spaceAfter=8))
    styles.add(ParagraphStyle("CellM", fontName="Helvetica", fontSize=8.2, leading=10.0, textColor=ink))
    styles.add(ParagraphStyle("TitleM", fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=ink, spaceAfter=10))
    styles.add(ParagraphStyle("SubM", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=ink, spaceAfter=8))
    styles.add(ParagraphStyle("SourceM", fontName="Helvetica", fontSize=9, leading=11.5, textColor=ink, spaceAfter=5))
    story = []
    p = lambda s: Paragraph(escape(str(s)), styles["TextM"])
    def title(a, b=None):
        story.append(Paragraph(escape(a), styles["TitleM"]))
        if b: story.append(p(b))
    def text(s): story.append(p(s))
    def table(head, rows, widths):
        values = [[Paragraph(escape(str(x)), styles["CellM"]) for x in row] for row in [head] + rows]
        t = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#c9eadf")),
                              ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f1f5f6")]),
                              ("VALIGN",(0,0),(-1,-1),"TOP"), ("TOPPADDING",(0,0),(-1,-1),5),
                              ("BOTTOMPADDING",(0,0),(-1,-1),5), ("LEFTPADDING",(0,0),(-1,-1),6)]))
        story.extend([t, Spacer(1, 9)])
    def page(): story.append(PageBreak())
    title("MOSS Core V0.7 - ready-terminated harness", "Prototype quotation, 1 November 2026. Quote 2 kits, plus separate prices at 10 / 50 / 100 kits.")
    text("One labelled and electrically tested kit serves one rover. Separate tooling/setup, test fixture, sourcing, lead time and shipping to Thailand. Price the documented STOP switch with its wired lid tail separately, and optional device adapters only where existing leads do not fit.")
    text(CYTRON_POLICY)
    text(LENGTH_BASIS)
    table(["Route", "Function", "Wires / cable", "CAD longest mm", "Quote span mm"],
          [[r["id"], r["function"], str(r["conductors"]) if not r["id"].startswith("U") else "Complete cable", f"{r['cad_longest_conductor_mm']:.1f}", r["prototype_free_span_mm"] or "Select cable"] for r in spec["cables"]], [79, 305, 106, 120, width-610])
    text("14 routes = 42 custom wire segments, including the optional adapters, + 3 complete USB cable assemblies. H03's centreline is the common trunk; individual wire lengths include fan-out. Left/right refer to forward driving. Final cut/strip lengths follow first-article fitting.")
    page()
    title("Cytron and motor pin schedule", "J2 = nine populated circuits in a ten-way housing. J3/J4 = complete six-wire motor cables.")
    table(["Core", "Function / net", "Cytron endpoint", "Wire / Core contact"],
          [[f"J2.{i}", pins[("J2",str(i))]["net"], WIRE_MAP["H03"][i-1][2], "24 AWG / 43030-0001" if i <= 5 else "18 AWG / 43030-0038"] for i in range(1,10)] + [["J2.10", "UNUSED", "No wire or contact", "Empty cavity"]], [65, 230, 250, width-545])
    table(["J3 left / J4 right", "Function", "Retained motor pigtail", "Wire / Core contact"],
          [[str(i), pins[("J3",str(i))]["function"], d, "18 AWG / 43030-0038" if i <= 2 else "24 AWG / 43030-0001"] for i, d in enumerate(["M1 winding", "M2 winding", "Encoder GND", "Encoder VCC, switched 3.3 V", "C1 / channel A", "C2 / channel B"],1)], [125,170,250,width-545])
    text("Motor loops: M1A -> J2.6 -> left shunt -> J3.1, and M1B -> J2.7 -> J3.2. Right: M2A -> J2.8 -> right shunt -> J4.1, and M2B -> J2.9 -> J4.2. Both winding legs are H-bridge outputs; neither is ground.")
    text(MOTOR_POLICY)
    page()
    title("Power, STOP and device connections", "Read the numbered cavities on each exact connector; display colours do not establish a pinout.")
    table(["Route / Core", "Numbered connection", "Termination / note"], [
        ["H01 / J10", "1 negative / GND; 2 fused battery positive", "Existing fused 3S battery lead; retain external 15 A fuse; XT30 cable extension only if needed"],
        ["H02 / J11", "1 switched battery +; 2 GND", "Cytron POWER + / -; one sized ferrule per Core cavity"],
        ["O01 / J5", "1 DATA; 2 switched battery +; 3 GND", "Arm servo daisy chain; optional adapter; one common power path"],
        ["O02 / J7", "1 speaker +; 2 speaker -", "Both amplifier terminals driven; neither is GND"],
        ["O03 / J14, J15", "1 fused 3S positive; 2 GND", "Two nominal 12 V fans; up to 12.6 V; shared F3 1 A fuse"],
        ["U01", "Core J20 -> Orange Pi POWER", "Complete USB-C to USB-C 5 V / 3 A cable"],
        ["U02", "HB1 downstream -> Core J1", "Complete USB-A to USB-C data cable"],
        ["U03", "Orange Pi DATA -> OTG -> HB1 upstream", "Retain HB1 captive 800 mm USB-A cable; store excess clear of moving parts"],
    ], [106, 292, width-398])
    table(["Core J8", "X08 circuit", "Switch terminal", "Function"],
          [["1","1","C1","CUT source"],["2","2","NC1","CUT return"],["5","3","C2","STATUS source"],["6","4","NC2","STATUS return"],["3 / 4","None","None","No contacts or wires"]], [140,150,180,width-470])
    text("STOP: quote Yijia YJ-LA16-22ZS/A, red, non-illuminated, two independent NC loops. Leave NO terminals unused and insulated. An existing unmarked button requires an unpowered continuity check; six tabs alone do not prove the needed contacts.")
    text("X08 chassis 51021-0400 + 4 x 50058-8000; lid 51047-0400 + 4 x 50133-8000. 28 AWG, insulation OD 0.50-0.80 mm. Manufacturer circuits 1-4 pass straight through. The pair uses friction retention; support the service loop and disconnect by the housings. Only H08_lid moves with the cover.")
    page()
    title("Connector parts and wire selection", "Installed quantities per rover; PCB headers are already in the PCBA BOM.")
    table(["Connection", "Qty", "Selected cable-side reference", "Specification"], PARTS, [94,65,247,width-406])
    text("Use stranded copper and document the wire manufacturer, gauge and insulation OD. For the selected Micro-Fit hand-tool processes: 18 AWG OD 1.60-1.85 mm and 24 AWG OD 1.42-1.85 mm. The terminal product's maximum OD is 1.85 mm. The battery/Cytron supply's 16 AWG entry is a quotation candidate retained from the existing supply concept; qualify actual supply leads separately.")
    text("Visual routing: winding wire OD 1.8 mm, control/encoder OD 1.5 mm; sleeve envelopes about 7.1 mm OD for H03's common trunk, 5.3 mm for its four-output power branch and 6.1 mm for each complete motor cable. Supplier dimensions remain to be confirmed on the prototype.")
    page()
    title("Workmanship and first article", "The quotation is ready for supplier review; physical fitting and electrical qualification are still pending.")
    for a in [MOTOR_POLICY, CYTRON_POLICY,
              "Provide a numbered mating-face drawing and factory wirelist, crimp tooling, wire specification and finished-length tolerance. Label each assembly at both ends. Identify LEFT/RIGHT motor cables and both Core terminations of the single Cytron loom. Quote and document all insulated factory splices/transitions.",
              "Test every kit for continuity, shorts and polarity. With power disconnected, both STOP loops must be closed when released and open when pressed or X08 unplugged. Check isolation between the two loops. Keep J2.10 and J8.3/4 empty.",
              "Fit the first kit with cover closed and opened. Inspect connector seating, wire exit/bends, access to the disconnect, strain relief, fan clearance, sharp edges and storage of the HB1's excess captive lead. Freeze batch spans and cut/strip allowances after fitting.",
              "Planned encoder test: compare counts and direction to an independent rotation reference during forward/reverse motion and repeated loaded reversals. Check for missed/extra counts, resets and supply dips. Check the complete wire/crimp assembly under startup/load for temperature and voltage drop; the Cytron channel rating is not the harness rating.",
              DIY_POLICY]:
        text(a)
    text("Evidence: the independent static connector check matched 76 pins on 12 connectors. It does not establish physical motor-end cavity mapping, crimp quality or powered operation. Cable-housing geometry is an explicitly dimensioned visual reference because exact manufacturer STEP/IGES was not obtained. Use current viewer outputs; the previous film is historical.")
    page()
    title("Sources and revision identity", "Manufacturer sources for contacts/tooling; distributor SKU for the retained stock motor kit.")
    for key, label, url in SOURCES:
        story.append(Paragraph(f"<b>{key}</b> - <link href='{escape(url)}' color='#19765f'>{escape(label)}</link>", styles["SourceM"]))
    text("Full URLs are supplied in SOURCES.md and HARNESS_SPECIFICATION.json.")
    text("PCB SHA256: " + BOARD_HASH)
    text("ROUTE_LENGTHS.json SHA256: " + spec["route_lengths_sha256"])
    def footer(c, doc):
        c.setStrokeColor(colors.HexColor("#c9eadf")); c.line(34, 33, W-34, 33)
        c.setFont("Helvetica", 8); c.setFillColor(ink)
        c.drawString(34, 20, "SHOW ROBOTICS / MOSS CORE V0.7 / 01 NOV 2026 / PROTOTYPE QUOTATION")
        c.drawRightString(W-34, 20, str(doc.page))
    doc = SimpleDocTemplate(str(OUT / "MOSS_CORE_V07_HARNESS_RFQ.pdf"), pagesize=(W, HH),
                            rightMargin=34, leftMargin=34, topMargin=30, bottomMargin=46,
                            title=spec["title"], author="Show Robotics")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    data, pins, check_path, route_path = load_inputs()
    spec = build_spec(data, pins, check_path, route_path)
    if "--check-inputs-only" in sys.argv:
        print(json.dumps({k: spec[k] for k in ["board_sha256", "route_count", "custom_wire_count", "standard_usb_assembly_count", "route_lengths_sha256"]}, indent=2)); return
    assert sha(route_path) == spec["route_lengths_sha256"], "Route inputs changed during read; rebuild after geometry completes"
    make_docs(spec, pins)
    make_pdf(spec, pins)
    assert sha(route_path) == spec["route_lengths_sha256"], "Route inputs changed during build; rebuild after geometry completes"
    manifest = {str(p.relative_to(OUT)): {"sha256": sha(p), "size": p.stat().st_size}
                for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"}
    (OUT / "MANIFEST.json").write_text(json.dumps({"date": DATE, "board_sha256": BOARD_HASH, "files": manifest}, indent=2) + "\n")
    print(json.dumps({"output": str(OUT), "docs": str(DOCS), "routes": len(spec["cables"]), "custom_wires": len(spec["wirelist"])}))


if __name__ == "__main__":
    main()
