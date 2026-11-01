#!/usr/bin/env python3
"""Read-only native KiCad stroke/opening check for the frozen new ink.

Run with KiCad's Python environment. Shapely may be supplied by --python-vendor.
No board is saved and no routing/electrical simulation is invoked.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--design',type=Path,required=True)
ap.add_argument('--layout',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--python-vendor',type=Path)
args=ap.parse_args()
if args.python_vendor:sys.path.insert(0,str(args.python_vendor))
import pcbnew as k
import wx
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
app=wx.App(False);quiet=wx.LogNull()
source=args.design/'electrical/MOSS_Core_V07_Prototype.kicad_pcb'
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
layout=json.loads(args.layout.read_text())
assert source_hash==layout['candidate_sha256'],'Layout/board hash mismatch'
b=k.LoadBoard(str(source));xy=lambda p:(p.x/1e6,p.y/1e6)
ERROR_IU=50  #50nm conservative polygon approximation, not a process allowance.
ROUNDING_MM=0.000102 #Two polygon errors plus2nm native coordinate rounding.
MIN_CLEARANCE=.15
def polygons(s):
    out=[]
    for i in range(s.OutlineCount()):
        c=s.COutline(i);outer=[xy(c.CPoint(j))for j in range(c.PointCount())]
        holes=[]
        for h in range(s.HoleCount(i)):
            q=s.CHole(i,h);holes.append([xy(q.CPoint(j))for j in range(q.PointCount())])
        if len(outer)>=3:out.append(Polygon(outer,holes))
    geom=unary_union(out)
    if not geom.is_valid:raise ValueError('Invalid native polygon conversion')
    return geom
def shape(obj,l):
    s=k.SHAPE_POLY_SET();obj.TransformShapeToPolygon(s,l,0,ERROR_IU,k.ERROR_OUTSIDE)
    return polygons(s)
def glyphs(text):
    s=k.SHAPE_POLY_SET();text.TransformTextToPolySet(s,0,ERROR_IU,k.ERROR_OUTSIDE)
    return polygons(s)
def bbox(obj):
    q=obj.GetBoundingBox();return box(q.GetX()/1e6,q.GetY()/1e6,(q.GetX()+q.GetWidth())/1e6,(q.GetY()+q.GetHeight())/1e6)
front=(k.F_Cu,k.F_Mask,k.F_SilkS);back=(k.B_Cu,k.B_Mask,k.B_SilkS)
openings={k.F_SilkS:[],k.B_SilkS:[]};opening_counts={};conservative_graphics=[]
fps={f.GetReference():f for f in b.GetFootprints()}
all_drawings=list(b.GetDrawings())+[g for f in fps.values()for g in f.GraphicalItems()]
for cu,mask,silk in (front,back):
    counts={'pad_apertures':0,'mask_graphics':0,'untented_vias':0}
    for f in fps.values():
        for p in f.Pads():
            if not p.IsOnLayer(mask):continue
            geom=shape(p,cu)
            if geom.is_empty:geom=bbox(p)
            expansion=p.GetSolderMaskExpansion(mask)/1e6
            if expansion:geom=geom.buffer(expansion)
            openings[silk].append(geom);counts['pad_apertures']+=1
    for g in all_drawings:
        if g.GetLayer()!=mask:continue
        if isinstance(g,k.PCB_SHAPE):geom=shape(g,mask)
        elif isinstance(g,k.PCB_TEXT):geom=glyphs(g)
        else:
            geom=bbox(g);conservative_graphics.append(g.m_Uuid.AsString())
        openings[silk].append(geom);counts['mask_graphics']+=1
    for v in b.GetTracks():
        if not isinstance(v,k.PCB_VIA)or not v.IsOnLayer(cu)or v.IsTented(mask):continue
        radius=v.GetWidth(cu)/2e6+v.GetSolderMaskExpansion(mask)/1e6
        #Extra50nm covers circle polygonization; no intentional gap relaxation.
        openings[silk].append(Point(xy(v.GetPosition())).buffer(radius+ERROR_IU/1e6,resolution=96))
        counts['untented_vias']+=1
    opening_counts[b.GetLayerName(silk)]=counts
unions={l:unary_union(g)for l,g in openings.items()}
assembled={r for row in json.loads((args.design/'electrical/BOM_PCBWAY_ASSEMBLY.json').read_text())['parts']for r in row['references']}
objects=[];direct=set();other_printed=[]
def add_text(t,kind,ref=None):
    l=t.GetLayer()
    if l not in openings or not t.IsVisible():return
    geom=glyphs(t);distance=geom.distance(unions[l])
    objects.append({'kind':kind,'reference':ref,'uuid':t.m_Uuid.AsString(),'text':t.GetShownText(False),
                    'face':b.GetLayerName(l),'font_height_mm':t.GetTextSize().y/1e6,
                    'stroke_mm':t.GetTextThickness()/1e6,'opening_clearance_mm':distance,
                    'meets_0_15mm_with_polygon_rounding_tolerance':distance+ROUNDING_MM>=MIN_CLEARANCE,
                    'glyph_bounds_mm':list(geom.bounds)})
for ref,f in fps.items():
    t=f.Reference()
    if t.GetLayer()in openings and t.IsVisible():
        add_text(t,'native_reference',ref);direct.add(ref)
caption_ids={x['before']['uuid']for x in layout.get('legacy_caption_changes',[])}
for g in all_drawings:
    if isinstance(g,k.PCB_TEXT)and g.GetLayer()in openings and g.IsVisible():
        other_printed.append({'text':g.GetShownText(False),'uuid':g.m_Uuid.AsString(),'face':b.GetLayerName(g.GetLayer())})
        if g.m_Uuid.AsString()in caption_ids:add_text(g,'adjusted_legacy_caption')
by_uuid={g.m_Uuid.AsString():g for g in all_drawings}
for leader in layout.get('leaders',[]):
    for uid in leader['graphic_uuids']:
        g=by_uuid[uid];l=g.GetLayer();assert l in openings and isinstance(g,k.PCB_SHAPE)
        geom=shape(g,l);distance=geom.distance(unions[l])
        objects.append({'kind':'new_leader','reference':leader['ref'],'uuid':uid,'face':b.GetLayerName(l),
                        'stroke_mm':g.GetWidth()/1e6,'opening_clearance_mm':distance,
                        'meets_0_15mm_with_polygon_rounding_tolerance':distance+ROUNDING_MM>=MIN_CLEARANCE})
manual={}
for ref in assembled-direct:
    hits=[t for t in other_printed if re.search(r'(?<![A-Za-z0-9_])'+re.escape(ref)+r'(?![A-Za-z0-9_])',t['text'])]
    if hits:manual[ref]=hits
unidentified=sorted(assembled-direct-set(manual))
violations=[r for r in objects if not r['meets_0_15mm_with_polygon_rounding_tolerance']]
report={'status':'PASS_NEW_INK_OPENING_CHECK'if not violations else'FAIL_NEW_INK_OPENING_CHECK',
        'board_sha256':source_hash,'layout_sha256':hashlib.sha256(args.layout.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'method':'Native TransformTextToPolySet strokes and native pad/mask shapes, including common openings and untented vias; no full-text bounding-box clearance substitution.',
        'minimum_required_clearance_mm':MIN_CLEARANCE,'native_polygon_error_mm':ERROR_IU/1e6,
        'rounding_and_two_polygon_errors_mm':ROUNDING_MM,'conservative_mask_graphic_bbox_fallback_uuids':conservative_graphics,
        'opening_source_counts':opening_counts,'objects_checked':objects,'violations':violations,
        'minimum_observed_clearance_mm':min(x['opening_clearance_mm']for x in objects),
        'coverage':{'assembled_components':len(assembled),'new_native_assembled_reference_labels':len(assembled&direct),
                    'existing_manual_labels':manual,'assembled_identified':len((assembled&direct)|set(manual)),
                    'assembled_without_printed_reference':unidentified,'all_native_reference_labels_printed':len(direct)},
        'limits':['Read-only saved native geometry check, not a fabricated-board test or guarantee of print registration.',
                  'Polygon rounding is reported explicitly; it is not additional PCBWay manufacturing tolerance.',
                  'Actual exported ink and label-to-body association still require preview inspection.']}
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k]for k in ['status','minimum_observed_clearance_mm','coverage']},indent=2))
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'Candidate changed during read-only check'
sys.exit(0 if not violations else 1)
