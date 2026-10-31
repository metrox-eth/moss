"""Check/export the current MOSS prototype. No supplier upload or payment."""
from pathlib import Path
import argparse, csv, hashlib, json, shutil, subprocess, zipfile

P = Path(__file__).resolve().parents[1]
E, EV, D = P / 'electrical', P / 'evidence', P / 'delivery'
NAME = 'MOSS_Core_V07_Prototype'
B, S = E / (NAME + '.kicad_pcb'), E / (NAME + '.kicad_sch')
K = shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--reuse-checks', action='store_true')
args = parser.parse_args()

def run(*a):
    r = subprocess.run([K, *map(str, a)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)

def design_hashes():
    files = [f for f in E.iterdir() if f.suffix in ('.kicad_pcb', '.kicad_pro', '.kicad_sch', '.kicad_dru', '.kicad_sym')]
    files += list((E / 'MOSS.pretty').glob('*.kicad_mod'))
    files += [E / 'circuit.json', E / 'BOM_PCBWAY_ASSEMBLY.json']
    return {str(f.relative_to(P)): sha(f) for f in files}

if args.reuse_checks:
    assert json.loads((EV / 'CHECKS.json').read_text())['file_hashes'] == design_hashes(), 'Design changed: rerun checks'
else:
    run('pcb', 'drc', '--schematic-parity', '--refill-zones', '--format', 'json', '--severity-all', '-o', EV / 'DRC.json', B)
    run('sch', 'erc', '--format', 'json', '--severity-all', '-o', EV / 'ERC.json', S)
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '-o', EV / 'NETLIST.xml', S)
    netlist = EV / 'NETLIST.xml'
    netlist.write_text(netlist.read_text().replace(str(P) + '/', ''))

drc = json.loads((EV / 'DRC.json').read_text())
erc = json.loads((EV / 'ERC.json').read_text())
assert not drc['unconnected_items'] and not drc['schematic_parity']
assert not any(v['severity'] == 'error' for v in drc['violations'])
assert len(drc['violations']) == 2
assert {i['uuid'] for v in drc['violations'] for i in v['items']} == {'19bdfd6d-a7bb-4aff-95d1-84e813186cc4', '5c5052fc-92bc-4db5-9351-1b24011a52e6'}
assert not any(s.get('violations') for s in erc['sheets'])
checks = dict(board_sha256=sha(B), DRC_errors=0, unconnected_items=0, schematic_parity_issues=0,
              ERC_violations=0, known_DRC_warnings=len(drc['violations']), file_hashes=design_hashes(),
              scope='Native prototype checks; no hardware qualification.')
(EV / 'CHECKS.json').write_text(json.dumps(checks, indent=2) + '\n')

F, A = D / 'fabrication', D / 'assembly'
F.mkdir(parents=True, exist_ok=True)
A.mkdir(parents=True, exist_ok=True)
before = sha(B)
run('pcb', 'export', 'gerbers', '--layers', 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts',
    '--subtract-soldermask', '-o', str(F) + '/', B)
run('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm', '--drill-origin', 'absolute',
    '--excellon-separate-th', '--generate-report', '--report-path', EV / 'DRILL_REPORT.txt', '-o', str(F) + '/', B)
run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '--exclude-dnp', '-o', A / 'NATIVE_POSITIONS.csv', B)
assert sha(B) == before, 'Export modified the approved PCB'

data = json.loads((E / 'BOM_PCBWAY_ASSEMBLY.json').read_text())
rows = data['parts']
refs = {r for x in rows for r in x['references']}
assert len(refs) == 210 and len(rows) == 96 and not data['accessories_excluded_from_PCB_placement']
assert next(x for x in rows if 'F1' in x['references'])['mpn'] == '08853.15DR'
with (A / 'MOSS_CORE_V07_PROTOTYPE_BOM.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Quantity', 'Manufacturer Part Number', 'Value', 'Footprint', 'Manufacturer', 'Assembly notes'])
    for x in rows:
        w.writerow([','.join(x['references']), x['quantity'], x['mpn'], x['value'], x['footprint'], x.get('manufacturer', ''), x.get('assemblyPreference', '')])
with (A / 'NATIVE_POSITIONS.csv').open(newline='') as f:
    r = csv.DictReader(f)
    fields, pos = r.fieldnames, list(r)
key = 'Ref' if 'Ref' in fields else 'Designator'
placed = [r for r in pos if r[key] in refs]
assert len(placed) == len(refs) and {r[key] for r in placed} == refs
with (A / 'MOSS_CORE_V07_PROTOTYPE_POSITIONS.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fields)
    w.writeheader()
    w.writerows(placed)
(A / 'NATIVE_POSITIONS.csv').unlink()
(A / 'ASSEMBLY_NOTES.txt').write_text('MOSS CORE V0.7 / PROTOTYPE / 2026-10-31 / NEW PCB + PCBA QUOTATION\n210 components per assembled board; 96 grouped purchase articles. Two assembled boards requested. Use the matched BOM, positions, Gerbers and drills.\nUpdated 31 October 2026. Use this matched set of design and assembly files.\n\nRESOLUTIONS OF PCBWAY COMMENTS RECEIVED ON 2026-10-31\nD20-D22: Keep exact TI TPD1E10B06DYAR. TI catalog SOT-5X3 / DYA and drawing DYA0002A SOT (SOD-523) refer to the same two-pin package. The copper footprint remains D_SOD-523.\nJ7: Keep JST S2B-PH-K-S(LF)(SN). Manual through-hole insertion/soldering with a suitable fixture and PCB support is accepted. Fully seat it without bending the PCB or damaging the housing; inspect seating and solder joints.\nJ8: Keep JST BM06B-SRSS-TB(LF)(SN). Manual placement is accepted for the two prototypes because this code has no suction cap. Use a suitable soldering/inspection process. Do not omit the connector. Pins 3/4 have no harness wires or crimp contacts.\nMOD1: Removed from design/BOM. Do not buy Waveshare 29035. U60/L3/passives implement the converter directly on the PCB.\nQ50: SIRA99DP-T1-GE3 is accepted; capitalization of SiRA99DP-T1-GE3 is the only difference. Keep the exact Vishay device/package.\nU2: Replaced by TI TPD2E2U06QDCKRQ1, DCK / SC-70-3. Pins 1 IO1, 2 IO2, 3 GND. Manufacturer package drawing DCK0003A and land-pattern drawing match the previous DCK part. This Q1 code is MSL2: observe dry-pack and floor-life requirements. Procurement lead: DigiKey 296-44302-1-ND, product URL below. Stock is not reserved; confirm procurement in the quotation. No DBZ/DRL package substitution.\nhttps://www.digikey.com/en/products/detail/texas-instruments/TPD2E2U06QDCKRQ1/6026260\n\nOTHER ASSEMBLY DETAILS\nU60: Exact MP9447GL-Z, 25-land MPS QFN 3 x 4 mm with FIVE DISTINCT exposed IN/SW lands. Not a generic QFN20 single thermal pad. Review paste/stencil and inspection for this footprint.\nL3: SRP6060FA-100M, same procurement article as L2. No unreviewed inductor/capacitor/ripple-network substitutions.\nH1: Grounding board feature, excluded from assembly BOM. Plated 2.7 mm mounting hole, 5.4 mm exposed copper ring on both faces, eight 0.5 mm plated stitch holes, no paste. Lug, screw and grounding strap are not PCBA items.\nF1: 08853.15DR soldered SMD, no fuse holder. F2/F3: 0451001.MRL 1 A.\nJ14/J15: B2B-XH-A(LF)(SN), pin 1 fused 3S positive, pin 2 GND.\nU14/U17/U43 have common soldermask openings for the affected fine-pitch pin rows. Copper and paste apertures are unchanged. Confirm stencil/process for these rows and U60 during review.\nThis submission requests quotation/engineering review, not payment or production authorization.\n')
(F / 'FABRICATION_NOTES.txt').write_text('MOSS CORE V0.7 / PROTOTYPE / 2026-10-31 / NEW QUOTATION\n4 copper layers, 80 x 75 mm, 1.6 mm board. Layer order F.Cu / In1.Cu / In2.Cu / B.Cu.\nMinimum plated hole 0.20 mm. Use the complete matched Gerber and separate PTH/NPTH files, including slots.\nPCBWAY SOLDER MASK COMMENT RESOLVED IN FILES: Common mask openings are provided locally over both pin rows of U14, U17 and U43, removing the 0.15 mm bridges that PCBWay cannot manufacture. No pad narrowing, copper rerouting or drill change is made by this DFM correction. Other mask openings and all paste apertures remain unchanged. Do not apply an additional global mask expansion. Please review CAM/stencil before production.\nH1 at (4,4) mm is now PTH, finished diameter 2.7 mm for M2.5: 5.4 mm exposed copper ring both faces, eight 0.5 mm stitch PTH to GND, no paste. Use the NEW drill files; do not reuse the previous NPTH file. The other seven mounting holes remain NPTH.\nThe converter is now integrated: no Waveshare module footprint or separate module procurement.\nPlease confirm final stackup, copper build and DFM in the quotation.\nQuotation/review only; no payment or production authorization in this submission.\n')
report = dict(status='PCBWAY_DFM_CORRECTED_NEW_QUOTATION', board_sha256=before, component_count=len(refs), article_count=len(rows),
              DRC_errors=0, unconnected_items=0, schematic_parity_issues=0, ERC_violations=0,
              known_DRC_warnings=len(drc['violations']), hardware_qualified=False)
(EV / 'EXPORT_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')

def archive(path, files, base):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(files):
            z.write(f, f.relative_to(base))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
    return dict(path=str(path.relative_to(P)), bytes=path.stat().st_size, sha256=sha(path))

date = '20261031_DFM'
prefix = 'MOSS_CORE_V07_PROTOTYPE_'
outputs = []
outputs.append(archive(D / (prefix + 'GERBERS_' + date + '.zip'), F.iterdir(), F))
outputs.append(archive(D / (prefix + 'ASSEMBLY_NOTES_' + date + '.zip'), A.iterdir(), A))
# Package only the board design, not the independent harness study or local caches.
roots = ('electrical', 'evidence', 'tools', 'preview')
files = [f for name in roots for f in (P / name).rglob('*')
         if f.is_file() and not any(part.startswith('.') or part == '__pycache__' for part in f.relative_to(P).parts)]
files += [f for folder in (F, A) for f in folder.iterdir() if f.is_file()]
files += [P / name for name in ('README.md', 'CONNECTORS.md', 'LICENSE-HARDWARE', 'NOTICE', 'KiCad_Libraries_LICENSE.md', '.gitattributes') if (P / name).is_file()]
manifest = {str(f.relative_to(P)): dict(bytes=f.stat().st_size, sha256=sha(f)) for f in sorted(files)}
(P / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
outputs.append(archive(D / (prefix + 'REVIEW_' + date + '.zip'), files + [P / 'MANIFEST.json'], P))
(P / 'PACKAGE.json').write_text(json.dumps(dict(**report, archives=outputs), indent=2) + '\n')
print(json.dumps(dict(**report, archives=outputs), indent=2), flush=True)
