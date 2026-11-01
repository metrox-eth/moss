"""Read-only physical-pad, exact-MPN and assembly-inventory cross-check.

Run with KiCad's bundled Python after export_package.py generated NETLIST.xml.
This checks consistency of the supplied files, not manufacturer suitability.
"""
from pathlib import Path
import argparse, collections, hashlib, json, xml.etree.ElementTree as ET
import pcbnew as k
import wx

app = wx.App(False)
quiet = wx.LogNull()
P = Path(__file__).resolve().parents[1]
E = P / 'electrical'
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, default=P / 'evidence/DESIGN_CONTRACT.json')
args = ap.parse_args()
B = E / 'MOSS_Core_V07_Prototype.kicad_pcb'
inputs = [B, E / 'circuit.json', E / 'BOM_PCBWAY_ASSEMBLY.json', P / 'evidence/NETLIST.xml']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hashes = {str(p.relative_to(P)): sha(p) for p in inputs}
board = k.LoadBoard(str(B))
parts = json.loads(inputs[1].read_text())['parts']
contract = {p['ref']: p for p in parts}
assert len(contract) == len(parts) == 222
native = {f.GetReference(): f for f in board.GetFootprints()}
assert len(native) == len(list(board.GetFootprints())) and set(native) == set(contract)
bm = json.loads(inputs[2].read_text())['parts']
articles = {}
for row in bm:
    assert row['quantity'] == len(row['references'])
    for ref in row['references']:
        assert ref not in articles, ('Duplicate BOM reference', ref)
        articles[ref] = row
assert len(articles) == 208 and len(bm) == 96

xml = ET.parse(inputs[3]).getroot()
schematic = {c.attrib['ref']: c for c in xml.findall('./components/comp')}
assert set(schematic) == set(contract)
sch_nets = {}
for net in xml.findall('./nets/net'):
    for node in net.findall('node'):
        key = (node.attrib['ref'], node.attrib['pin'])
        assert key not in sch_nets
        sch_nets[key] = net.attrib['name']

pins = 0
for ref, part in contract.items():
    f = native[ref]
    fields = {p.GetName(): p.GetText() for p in f.GetFields()}
    assert fields['MPN'] == part['mpn'], (ref, 'Native MPN mismatch')
    ident = f.GetFPID()
    fp = str(ident.GetLibNickname()) + ':' + str(ident.GetLibItemName())
    assert fp == part['fp_local'], (ref, 'Native footprint mismatch')
    sch = schematic[ref]
    assert sch.findtext('footprint') == fp
    sch_fields = {p.attrib['name']: p.text for p in sch.findall('./fields/field')}
    assert sch_fields.get('MPN') == part['mpn'], (ref, 'Schematic MPN mismatch')
    if ref in articles:
        row = articles[ref]
        assert row['mpn'] == part['mpn'] and row['footprint'] == part['fp'], (ref, 'BOM mismatch')
    observed = collections.defaultdict(set)
    for pad in f.Pads():
        number = pad.GetNumber()
        if number:
            observed[number].add(pad.GetNetname())
    assert set(observed) == set(part['pins']), (ref, 'Physical pad number mismatch', set(observed), set(part['pins']))
    for number, definition in part['pins'].items():
        expected = definition[1]
        actual = observed[number]
        sch_net = sch_nets.get((ref, number), '')
        if expected is None:
            assert all(not n or n.startswith('unconnected-') for n in actual), (ref, number, actual)
            assert not sch_net or sch_net.startswith('unconnected-'), (ref, number, sch_net)
        else:
            assert actual == {expected}, (ref, number, expected, actual)
            assert sch_net == expected, (ref, number, expected, sch_net)
        pins += 1

assert hashes == {str(p.relative_to(P)): sha(p) for p in inputs}
report = dict(status='PASS', file_hashes=hashes, native_footprints=222,
              assembled_components=208, grouped_purchase_articles=96,
              physical_pin_definitions_checked=pins,
              scope='Native physical pad nets and numbers, exact MPN fields, local footprint IDs, schematic netlist and grouped BOM are mutually consistent. No files modified.',
              limits='Not an independent datasheet/package-geometry review, electrical simulation or hardware test.')
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
