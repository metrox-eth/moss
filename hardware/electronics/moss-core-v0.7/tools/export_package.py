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

drc = json.loads((EV / 'DRC.json').read_text())
erc = json.loads((EV / 'ERC.json').read_text())
assert not drc['unconnected_items'] and not drc['schematic_parity']
assert not any(v['severity'] == 'error' for v in drc['violations'])
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
assert len(refs) == 194 and len(rows) == 89 and not data['accessories_excluded_from_PCB_placement']
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
(A / 'ASSEMBLY_NOTES.txt').write_text(
    'MOSS CORE V0.7 — PROTOTYPE — ENGINEERING REVIEW\n'
    '194 placed components, 89 grouped purchase articles. Use the matched BOM and positions in this folder.\n'
    'F1: Littelfuse 08853.15DR, soldered SMD. No separate fuse holder, cartridge or cover.\n'
    'J8: six positions; pins 3/4 have no harness wires or crimp contacts.\n'
    'J14/J15: JST B2B-XH-A(LF)(SN), pin 1 fused 3S positive, pin 2 GND.\n'
    'F2/F3: Littelfuse 0451001.MRL, 1 A; quantities grouped by exact MPN.\n'
    'MOD1: Waveshare 29035 SMD module, factory 5 V setting. Confirm sourcing and castellated soldering method; no paste apertures are provided.\n'
    'No payment or production authorization. See README and CONNECTORS for wiring and remaining bench qualification.\n')
(F / 'FABRICATION_NOTES.txt').write_text(
    'MOSS CORE V0.7 — PROTOTYPE\n4 copper layers, 80 x 75 mm, 1.6 mm board.\n'
    'Layer order: F.Cu, In1.Cu, In2.Cu, B.Cu.\n'
    'Minimum plated hole: 0.20 mm. Use the supplied separate PTH/NPTH drill files, including slots.\n'
    'The exported mask, paste and silkscreen layers correspond to this exact PCB.\n'
    'Confirm stackup, copper build, DFM and any impedance requirements during engineering review.\n'
    'No payment or production authorization.\n')
report = dict(status='CURRENT_PROTOTYPE_EXPORT', board_sha256=before, component_count=len(refs), article_count=len(rows),
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

date = '20261030'
prefix = 'MOSS_CORE_V07_PROTOTYPE_'
outputs = []
outputs.append(archive(D / (prefix + 'GERBERS_' + date + '.zip'), F.iterdir(), F))
outputs.append(archive(D / (prefix + 'ASSEMBLY_NOTES_' + date + '.zip'), A.iterdir(), A))
files = [f for f in P.rglob('*') if f.is_file() and f.suffix != '.zip' and f.name not in ('PACKAGE.json', 'MANIFEST.json') and not f.name.startswith('.')]
manifest = {str(f.relative_to(P)): dict(bytes=f.stat().st_size, sha256=sha(f)) for f in sorted(files)}
(P / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
outputs.append(archive(D / (prefix + 'REVIEW_' + date + '.zip'), files + [P / 'MANIFEST.json'], P))
(P / 'PACKAGE.json').write_text(json.dumps(dict(**report, archives=outputs), indent=2) + '\n')
print(json.dumps(dict(**report, archives=outputs), indent=2), flush=True)
