# SPDX-License-Identifier: Apache-2.0
"""Create a reading view without changing supplier MPN/designator groups."""
from pathlib import Path
import argparse,csv,hashlib,json,re

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--bom',type=Path,required=True)
ap.add_argument('--circuit',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
bom=json.loads(a.bom.read_text());parts={p['ref']:p for p in json.loads(a.circuit.read_text())['parts']}
rows=[];counts={}
def category(p):
    kind=p['kind'];ref=p['ref']
    if ref.startswith('Q'):return ('Active / semiconductors','Transistors')
    if kind=='ic':return ('Active / semiconductors','Integrated circuits')
    if kind in ('D','LED'):return ('Active / semiconductors','Diodes / LEDs')
    if kind in ('R','C','L','F'):
        return ('Passive',{'R':'Resistors / shunts','C':'Capacitors','L':'Inductors','F':'Fuses'}[kind])
    return ('Electromechanical / other',{'connector':'Connectors','switch':'Switches','mount':'Mounts','testpoint':'Test points'}.get(kind,kind))
def natural(s):return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)',s)]
def numeric(s):
    m=re.match(r'\s*([\d.]+)\s*([pnumkM]?)',s)
    return float(m[1])*{'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'M':1e6,'':1}[m[2]] if m else float('inf')
for r in bom['parts']:
    refs=r['references'];classes={category(parts[ref]) for ref in refs}
    assert len(classes)==1,('Mixed category in existing MPN group',r['mpn'],refs)
    assert r['quantity']==len(refs),(r['mpn'],'quantity mismatch')
    cat,sub=classes.pop();labels=list(dict.fromkeys(parts[ref]['value'] for ref in refs))
    row={'Category':cat,'Subcategory':sub,'Designators':','.join(refs),'Quantity':r['quantity'],
         'Manufacturer Part Number':r['mpn'],'Readable values':' | '.join(labels),
         'Footprint':r['footprint'],'Manufacturer':r.get('manufacturer','')}
    rows.append(row);c=counts.setdefault(cat,{'articles':0,'components':0});c['articles']+=1;c['components']+=r['quantity']
order={'Active / semiconductors':0,'Passive':1,'Electromechanical / other':2}
rows.sort(key=lambda r:(order[r['Category']],r['Subcategory'],numeric(r['Readable values']),natural(r['Designators'])))
dest=a.output/'BOM_CLASSIFIED_REVIEW.csv'
with dest.open('w',newline='')as f:
    out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
original=sorted((r['mpn'],tuple(r['references']),r['quantity'],r['footprint'])for r in bom['parts'])
derived=sorted((r['Manufacturer Part Number'],tuple(r['Designators'].split(',')),r['Quantity'],r['Footprint'])for r in rows)
assert original==derived
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof={'status':'PASS_EXACT_MPN_DESIGNATORS_QUANTITIES_FOOTPRINTS_PRESERVED','source_bom_sha256':sha(a.bom),
       'source_circuit_sha256':sha(a.circuit),'classified_csv_sha256':sha(dest),'totals':{'articles':len(rows),'components':sum(r['Quantity']for r in rows)},
       'category_counts':counts,'category_convention':'Semiconductors groups ICs, transistors, diodes and LEDs for review; this is not a claim that every diode is an active element under every circuit-theory definition.',
       'scope':'Additional reading view only; original supplier files unchanged.'}
(a.output/'BOM_CLASSIFICATION_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
