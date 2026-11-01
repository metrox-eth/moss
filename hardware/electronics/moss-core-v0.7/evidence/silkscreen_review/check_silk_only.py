#!/usr/bin/env python3
"""Read-only comparison of KiCad native boards after a reference-ink update.

Reference/Value presentation and Fab/Silk text nodes are removed from the
protected comparison. A separate exact whitelist can permit new Silk leader
segments. Actual reference/value strings and every pre-existing non-text graphic
remain protected. No pads, models, copper, zone fills or board settings are ignored.
Standard library only; no KiCad process, router or source mutation is invoked.
"""
from pathlib import Path
from decimal import Decimal
import argparse, collections, hashlib, json, math, re, sys

TOKEN=re.compile(r'\s+|;[^\n]*|\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
NUMBER=re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')
PRESENTATION_LAYERS={'F.Fab','B.Fab','F.SilkS','B.SilkS'}
PRINTED_LAYERS={'F.SilkS','B.SilkS'}
SORT_CHILDREN={'kicad_pcb','footprint','pad','model','zone','setup','effects','font','stroke'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def value(token):
    if isinstance(token,list):return None
    if token.startswith('"'):
        try:return json.loads(token)
        except json.JSONDecodeError:return token[1:-1]
    return token
def tag(node):return value(node[0]) if isinstance(node,list) and node else None
def children(node,name):return [n for n in node if isinstance(n,list) and tag(n)==name]
def child(node,name):return next(iter(children(node,name)),None)
def field(node,name,index=1,default=None):
    n=child(node,name)
    return value(n[index]) if n is not None and len(n)>index else default
def parse(text):
    root=[];stack=[root]
    for m in TOKEN.finditer(text):
        token=m.group()
        if token.isspace() or token.startswith(';'):continue
        if token=='(':
            node=[];stack[-1].append(node);stack.append(node)
        elif token==')':
            if len(stack)==1:raise ValueError('Unexpected closing parenthesis')
            stack.pop()
        else:stack[-1].append(token)
    if len(stack)!=1 or len(root)!=1:raise ValueError('Unbalanced or multiple native roots')
    return root[0]
def atom(token):
    if token.startswith('"'):return ('quoted',value(token))
    if NUMBER.fullmatch(token):
        d=Decimal(token)
        return ('number','0' if d==0 else str(d.normalize()))
    return ('atom',token)
def canonical(node):
    if not isinstance(node,list):return atom(node)
    if not node:return ('list',)
    if tag(node) in SORT_CHILDREN:
        # Child objects are unordered; vector/point and polygon vertex order is
        # not sorted because their containers are deliberately absent above.
        atoms=[canonical(x)for x in node if not isinstance(x,list)]
        objs=sorted((canonical(x)for x in node if isinstance(x,list)),key=lambda x:json.dumps(x,separators=(',',':')))
        return ('list',tuple(atoms),tuple(objs))
    return ('list',tuple(canonical(x)for x in node))
def normalized_layer(name):return {'F.Silkscreen':'F.SilkS','B.Silkscreen':'B.SilkS'}.get(name,name)
def layer(node):return normalized_layer(field(node,'layer'))
def property_node(fp,name):
    return next((n for n in children(fp,'property')if len(n)>2 and value(n[1])==name),None)
def identity(fp):
    ref=property_node(fp,'Reference');val=property_node(fp,'Value')
    return {'uuid':field(fp,'uuid'),'reference':value(ref[2])if ref else None,
            'value':value(val[2])if val else None}
def allowed_text(node):
    if layer(node)not in PRESENTATION_LAYERS:return False
    if tag(node)in ('fp_text','gr_text','gr_text_box'):return True
    return tag(node)=='property' and len(node)>2 and value(node[1])in ('Reference','Value')
def protected(node,ignored_leaders=None):
    if not isinstance(node,list):return node
    out=[]
    for n in node:
        if isinstance(n,list)and field(n,'uuid')in(ignored_leaders or set()):
            assert tag(n)in('gr_line','fp_line')and layer(n)in PRINTED_LAYERS
            continue
        if isinstance(n,list) and allowed_text(n):
            if tag(n)=='property':
                # Keep electrical identity while discarding the field's layer,
                # location, font, visibility and its presentation-object UUID.
                out.append(n[:3])
            continue
        out.append(protected(n,ignored_leaders))
    return out
def sections(board,ignored_leaders=None):
    fps=children(board,'footprint');other=[];cu=[];zones=[];edges=[]
    for n in board[1:]:
        if tag(n)=='footprint':continue
        if field(n,'uuid')in(ignored_leaders or set()):continue
        if allowed_text(n):continue
        if tag(n)in ('segment','via','arc'):cu.append(n)
        elif tag(n)=='zone':zones.append(n)
        elif layer(n)=='Edge.Cuts':edges.append(n)
        else:other.append(n)
    canon_list=lambda nodes:sorted((canonical(n)for n in nodes),key=lambda x:json.dumps(x,separators=(',',':')))
    return {'footprint_identity':sorted((identity(fp)for fp in fps),key=lambda x:x['uuid']),
            'footprints_protected':canon_list([protected(fp,ignored_leaders)for fp in fps]),
            'pads':canon_list([n for fp in fps for n in children(fp,'pad')]),
            'models':canon_list([n for fp in fps for n in children(fp,'model')]),
            'copper_and_vias':canon_list(cu),'zones_and_stored_fills':canon_list(zones),
            'outline':canon_list(edges),'other_protected_board_content':canon_list(other)}
def native_uuid_objects(board):
    result={}
    def walk(n,owner=None):
        if not isinstance(n,list):return
        if tag(n)=='footprint':owner=identity(n)['reference']
        uid=field(n,'uuid')
        if uid:
            if uid in result:raise ValueError('Duplicate native object UUID: '+uid)
            result[uid]=(n,owner)
        for sub in n:
            if isinstance(sub,list):walk(sub,owner)
    walk(board);return result
def validate_leaders(old,new,manifest=None):
    if manifest is None:return {'status':'NO_LEADERS_DECLARED','valid':True,'objects':[],'rejected':[]},set()
    before=native_uuid_objects(old);after=native_uuid_objects(new)
    refs={identity(fp)['reference']for fp in children(new,'footprint')}
    records=[];errors=[];seen=set();permitted=set();tol=0.000002
    for leader in manifest.get('leaders',[]):
        ref=leader.get('ref');side=normalized_layer(leader.get('side'));width=leader.get('width_mm')
        points=leader.get('points_mm',[]);uuids=leader.get('graphic_uuids',[])
        if ref not in refs or side not in PRINTED_LAYERS or not isinstance(width,(int,float))or not math.isfinite(width)or width<.15-1e-9 or len(points)<2 or len(uuids)!=len(points)-1:
            errors.append({'ref':ref,'reason':'Malformed leader declaration or non-Silk/sub-minimum stroke'});continue
        for i,uid in enumerate(uuids):
            reasons=[]
            if not isinstance(uid,str)or not uid:
                errors.append({'ref':ref,'reason':'Missing/non-string declared UUID'});continue
            if uid in seen:reasons.append('Duplicate declared UUID')
            seen.add(uid)
            if uid in before:reasons.append('Leader UUID already existed in baseline; edits/removals are forbidden')
            if uid not in after:
                errors.append({'ref':ref,'uuid':uid,'reason':'Declared leader missing from candidate'});continue
            node,owner=after[uid];kind=tag(node);native_side=layer(node)
            stroke=child(node,'stroke')or[];native_width=float(field(stroke,'width',default=-1))
            if kind not in('gr_line','fp_line'):reasons.append('Object is not a line segment')
            if native_side not in PRINTED_LAYERS or native_side!=side:reasons.append('Wrong/native non-Silk layer')
            if not math.isfinite(native_width)or native_width<.15-1e-9 or abs(native_width-width)>tol:reasons.append('Native width differs from declaration or below0.15mm')
            if field(stroke,'type',default='default')not in('default','solid'):reasons.append('Non-solid leader stroke')
            # Board shapes use board coordinates. An fp_line is allowed only
            # when its manifest explicitly supplies native local coordinates;
            # this avoids guessing a back-side transform from global points.
            frame='board'
            if kind=='fp_line':
                frame='footprint_local'
                if owner!=ref or leader.get('coordinate_frame')!='footprint_local':reasons.append('fp_line needs matching owner and explicit native footprint_local points')
            endpoints=[]
            for key,expected in [('start',points[i]),('end',points[i+1])]:
                n=child(node,key)
                actual=[float(value(v))for v in n[1:3]]if n is not None and len(n)>=3 else None
                endpoints.append(actual)
                if actual is None or len(expected)!=2 or any(not math.isfinite(float(v))for v in expected+actual)or any(abs(a-float(e))>tol for a,e in zip(actual,expected)):reasons.append('Native '+key+' does not match declared endpoint')
            row={'reference':ref,'uuid':uid,'native_kind':kind,'face':native_side,'width_mm':native_width,
                 'start_mm':endpoints[0],'end_mm':endpoints[1],'coordinate_frame':frame,'native_object_sha256':digest(canonical(node))}
            if reasons:errors.append({**row,'reasons':reasons})
            else:records.append(row);permitted.add(uid)
    return {'status':'PASS_EXACT_NEW_SILK_LEADER_WHITELIST'if not errors else'FAIL_LEADER_WHITELIST',
            'valid':not errors,'objects':records,'rejected':errors,'native_endpoint_tolerance_mm':tol,
            'existing_non_text_graphics_must_remain_exact':True},permitted
def text_record(n,owner=None):
    t=tag(n);text=None
    if t=='property' and len(n)>2:text=value(n[2])
    elif t=='fp_text' and len(n)>2:text=value(n[2])
    elif t in ('gr_text','gr_text_box') and len(n)>1:text=value(n[1])
    if text is None:return None
    effects=child(n,'effects')or[];font=child(effects,'font')or[];size=child(font,'size')
    hidden=field(n,'hide')=='yes' or any(not isinstance(x,list)and value(x)=='hide'for x in n)
    record={'owner':owner,'kind':t,'uuid':field(n,'uuid'),'text':text,'layer':layer(n),
            'hidden':hidden,'font_size_mm':[float(value(x))for x in size[1:]]if size else None,
            'stroke_mm':float(field(font,'thickness'))if field(font,'thickness')is not None else None,
            'native_text_sha256':digest(canonical(n))}
    record['reference_label']=bool(owner and(text==owner or text=='${REFERENCE}'))
    return record
def texts(board):
    out=[]
    for n in board[1:]:
        if tag(n)=='footprint':
            owner=identity(n)['reference']
            for x in n:
                if isinstance(x,list):
                    r=text_record(x,owner)
                    if r:out.append(r)
        else:
            r=text_record(n)if isinstance(n,list)else None
            if r:out.append(r)
    return out
def style_review(old,new):
    original={x['native_text_sha256']for x in old};changed=[];fail=[]
    inherited_small=[]
    for n in new:
        if n['layer']not in PRINTED_LAYERS or n['hidden']:continue
        s=n['font_size_mm'];stroke=n['stroke_mm']
        issues=[]
        if not s or len(s)<2 or s[1]<0.8-1e-9:issues.append('font_height_below_0.8mm_or_unknown')
        if stroke is None or stroke<0.15-1e-9:issues.append('stroke_below_0.15mm_or_unknown')
        if n['native_text_sha256']not in original:
            changed.append(n)
            if issues:fail.append({**n,'issues':issues})
        elif issues:inherited_small.append({**n,'issues':issues})
    printed_refs=[x for x in new if x['reference_label']and x['layer']in PRINTED_LAYERS and not x['hidden']]
    return {'changed_or_new_printed_texts':changed,'new_printed_style_violations':fail,
            'inherited_small_printed_texts_not_new_failures':inherited_small,
            'native_reference_labels_printed':len(printed_refs),
            'references_with_printed_native_labels':sorted({x['owner']for x in printed_refs}),
            'requirements':{'minimum_font_height_mm':0.8,'minimum_stroke_mm':0.15,'minimum_opening_clearance_mm':0.15},
            'opening_clearance_result':'NOT_CHECKED_BY_THIS_AST_SCRIPT; use native text-stroke/mask geometry, final DRC and previews.',
            'sources':['https://www.pcbway.com/helpcenter/design_instruction/How_to_make_my_silkscreen_clear_and_beautiful_on_PCB__.html',
                       'https://www.pcbway.com/helpcenter/Engineering_Questions/Spacing_between_silkscreen_and_openings.html']}
def bom_notes_exception(before,after):
    a=dict(before);b=dict(after);old=a.pop('notes',None);new=b.pop('notes',None)
    exact=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    identical=exact(a)==exact(b)
    valid_notes=isinstance(old,list)and isinstance(new,list)and all(isinstance(x,str)for x in old+new)
    return {'accepted':identical and valid_notes,'inventory_and_all_non_notes_data_exact':identical,
            'non_notes_data_sha256':{'baseline':hashlib.sha256(exact(a).encode()).hexdigest(),
                                     'candidate':hashlib.sha256(exact(b).encode()).hexdigest()},
            'notes_before':old,'notes_after':new,
            'removed_notes':[x for x in (old or [])if x not in (new or [])]if valid_notes else None,
            'added_notes':[x for x in (new or [])if x not in (old or [])]if valid_notes else None,
            'scope':'Only the top-level notes array may differ; all purchasing rows and other metadata remain exact JSON data.'}
def byte_comparison(before,after):
    names={p.relative_to(before).as_posix()for p in (before/'electrical').rglob('*')if p.is_file()and p.suffix!='.kicad_pcb'and not p.name.endswith(('.lck','.kicad_prl'))}
    names|={p.relative_to(after).as_posix()for p in (after/'electrical').rglob('*')if p.is_file()and p.suffix!='.kicad_pcb'and not p.name.endswith(('.lck','.kicad_prl'))}
    names.update(['delivery/assembly/MOSS_CORE_V07_PROTOTYPE_BOM.csv','delivery/assembly/MOSS_CORE_V07_PROTOTYPE_POSITIONS.csv'])
    out=[]
    for n in sorted(names):
        a=before/n;b=after/n
        ha=sha(a)if a.is_file()else None;hb=sha(b)if b.is_file()else None
        record={'path':n,'baseline_sha256':ha,'candidate_sha256':hb,'identical':ha is not None and ha==hb}
        record['accepted']=record['identical']
        if n=='electrical/BOM_PCBWAY_ASSEMBLY.json' and ha is not None and hb is not None and ha!=hb:
            exception=bom_notes_exception(json.loads(a.read_text()),json.loads(b.read_text()))
            record['notes_only_exception']=exception;record['accepted']=exception['accepted']
        out.append(record)
    return out
def compare(before,after,leader_manifest=None):
    old=parse(before.read_text());new=parse(after.read_text())
    assert tag(old)==tag(new)=='kicad_pcb','Expected native KiCad board roots'
    leaders,ids=validate_leaders(old,new,leader_manifest)
    if leader_manifest is not None:
        for key,path in [('baseline_sha256',before),('candidate_sha256',after)]:
            if key in leader_manifest and leader_manifest[key]!=sha(path):
                leaders['valid']=False;leaders['rejected'].append({'reason':'Leader manifest '+key+' does not match actual board'})
                leaders['status']='FAIL_LEADER_WHITELIST'
    a=sections(old);b=sections(new,ids)
    checks={n:{'baseline_sha256':digest(a[n]),'candidate_sha256':digest(b[n]),'equal':a[n]==b[n]}for n in a}
    old_protected=digest(canonical(protected(old)));new_protected=digest(canonical(protected(new,ids)))
    return {'baseline_board_sha256':sha(before),'candidate_board_sha256':sha(after),
            'protected_native_tree_equal':old_protected==new_protected,
            'protected_native_tree_sha256':{'baseline':old_protected,'candidate':new_protected},
            'sections':checks,'baseline_text_count':len(texts(old)),'candidate_text_count':len(texts(new)),
            'new_silk_leaders':leaders,
            'silk_style':style_review(texts(old),texts(new)),
            'footprint_differences':[i['reference']for i in a['footprint_identity']if i not in b['footprint_identity']]}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',type=Path,required=True,help='Baseline design directory')
    ap.add_argument('--candidate',type=Path,required=True,help='Frozen candidate design directory')
    ap.add_argument('--leader-manifest',type=Path,help='REFERENCE_LAYOUT.json listing exact new leader UUIDs and geometry')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    a=args.baseline/'electrical/MOSS_Core_V07_Prototype.kicad_pcb';b=args.candidate/'electrical/MOSS_Core_V07_Prototype.kicad_pcb'
    manifest=json.loads(args.leader_manifest.read_text())if args.leader_manifest else None
    report=compare(a,b,manifest);report['source_file_comparison']=byte_comparison(args.baseline,args.candidate)
    if args.leader_manifest:report['leader_manifest_sha256']=sha(args.leader_manifest)
    report['all_source_bytes_identical']=all(x['identical']for x in report['source_file_comparison'])
    report['electrical_and_physical_equivalence_pass']=report['protected_native_tree_equal']and report['new_silk_leaders']['valid']and all(x['equal']for x in report['sections'].values())and all(x['accepted']for x in report['source_file_comparison'])
    report['new_reference_style_pass']=not report['silk_style']['new_printed_style_violations']
    report['status']='PASS_PROTECTED_DESIGN_UNCHANGED'if report['electrical_and_physical_equivalence_pass']else'FAIL_PROTECTED_DESIGN_CHANGED'
    report['limits']=['Native-file comparison only; no new electrical simulation or physical board test.',
                      'This is not the final legibility/clearance approval; mask clearances and actual exported ink still need their geometry/preview checks.',
                      'Historic small Fab text is excluded from printed-silkscreen checks. Reference/value strings remain protected.',
                      'The only source-file exception is an explicitly recorded top-level BOM_PCBWAY_ASSEMBLY.json notes change; all other BOM data and supplier CSVs remain protected.']
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','electrical_and_physical_equivalence_pass','new_reference_style_pass','candidate_board_sha256']},indent=2))
    return 0 if report['electrical_and_physical_equivalence_pass']and report['new_reference_style_pass']else 1
if __name__=='__main__':sys.exit(main())
