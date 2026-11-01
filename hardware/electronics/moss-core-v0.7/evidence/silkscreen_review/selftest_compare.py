"""Small native-syntax fixtures for the protected-design comparator."""
from pathlib import Path
import json
from check_silk_only import parse,protected,canonical,sections,style_review,texts,bom_notes_exception,validate_leaders

BASE='''(kicad_pcb (version 20250828) (generator pcbnew)
 (general (thickness 1.6))
 (footprint "MOSS:R0603" (layer "F.Cu") (uuid "fp-1") (at 10 20 90)
  (property "Reference" "R1" (at 0 -1 90) (layer "F.Fab") (uuid "text-1")
   (effects (font (size .6 .6) (thickness .1))))
  (property "Value" "10k" (at 0 1) (layer "F.Fab") (hide yes))
  (pad "1" smd rect (at -.8 0) (size .8 .9) (layers "F.Cu" "F.Mask" "F.Paste") (net "3V3") (uuid "pad-1"))
  (model "R0603.step" (offset (xyz 0 0 2)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))
 (segment (start 10 20) (end 11 21) (width .2) (layer "F.Cu") (net "3V3") (uuid "track-1"))
 (via (at 11 21) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net "3V3") (uuid "via-1"))
 (zone (net "GND") (layer "In1.Cu") (uuid "zone-1") (polygon (pts (xy 0 0) (xy 20 0) (xy 20 20))))
 (gr_line (start 0 0) (end 20 0) (stroke (width .05) (type default)) (layer "Edge.Cuts") (uuid "edge-1")))'''

def same(a,b):return canonical(protected(parse(a)))==canonical(protected(parse(b)))
good=BASE.replace('(at 0 -1 90) (layer "F.Fab")','(at 1 -2 90) (layer "F.SilkS")').replace('(size .6 .6) (thickness .1)','(size .8 .8) (thickness .15)')
tests={'reference_presentation_allowed':same(BASE,good),'numeric_spelling_allowed':same(BASE,BASE.replace('(thickness 1.6)','(thickness 1.6000)')),
       'copper_width_rejected':not same(BASE,good.replace('(width .2)','(width .15)')),
       'pad_net_rejected':not same(BASE,good.replace('(net "3V3") (uuid "pad-1")','(net "GND") (uuid "pad-1")')),
       'reference_renumber_rejected':not same(BASE,good.replace('"Reference" "R1"','"Reference" "R2"')),
       'component_value_rejected':not same(BASE,good.replace('"Value" "10k"','"Value" "100k"')),
       'model_offset_rejected':not same(BASE,good.replace('(xyz 0 0 2)','(xyz 0 0 3)')),
       'zone_vertex_rejected':not same(BASE,good.replace('(xy 20 20)','(xy 20 21)')),
       'outline_rejected':not same(BASE,good.replace('(end 20 0)','(end 21 0)')),
       'via_drill_rejected':not same(BASE,good.replace('(drill .3)','(drill .2)')),
       'footprint_uuid_rejected':not same(BASE,good.replace('"fp-1"','"fp-2"'))}
style=style_review(texts(parse(BASE)),texts(parse(good)))
tests['old_small_Fab_is_not_a_silk_failure']=not style['new_printed_style_violations']
bad=good.replace('(size .8 .8) (thickness .15)','(size .7 .7) (thickness .1)')
tests['new_small_printed_ref_is_rejected']=bool(style_review(texts(parse(BASE)),texts(parse(bad)))['new_printed_style_violations'])
inventory={'notes':['old package name'],'component_count':1,'parts':[{'mpn':'PART1','references':['R1'],'quantity':1}]}
changed={**inventory,'notes':['new package name','Silkscreen-only update']}
tests['explicit_BOM_top_level_notes_change_allowed']=bom_notes_exception(inventory,changed)['accepted']
tests['BOM_quantity_change_rejected']=not bom_notes_exception(inventory,{**changed,'parts':[{'mpn':'PART1','references':['R1'],'quantity':2}]})['accepted']
tests['other_BOM_metadata_change_rejected']=not bom_notes_exception(inventory,{**changed,'component_count':2})['accepted']
line='(gr_line (start 12 2) (end 13 3) (stroke (width .15) (type default)) (layer "F.SilkS") (uuid "leader-1"))'
with_line=good[:-1]+line+')'
manifest={'leaders':[{'ref':'R1','side':'F.Silkscreen','width_mm':.15,'points_mm':[[12,2],[13,3]],'graphic_uuids':['leader-1']}]}
review,ids=validate_leaders(parse(BASE),parse(with_line),manifest)
tests['exact_declared_new_silk_leader_allowed']=review['valid']and canonical(protected(parse(BASE)))==canonical(protected(parse(with_line),ids))
tests['leader_without_whitelist_rejected']=not same(BASE,with_line)
bad_layer=with_line.replace('(layer "F.SilkS") (uuid "leader-1")','(layer "F.Cu") (uuid "leader-1")')
tests['leader_on_copper_rejected']=not validate_leaders(parse(BASE),parse(bad_layer),manifest)[0]['valid']
bad_width=with_line.replace('(stroke (width .15) (type default)) (layer "F.SilkS")','(stroke (width .14) (type default)) (layer "F.SilkS")')
tests['subminimum_or_undeclared_width_rejected']=not validate_leaders(parse(BASE),parse(bad_width),manifest)[0]['valid']
existing={'leaders':[{'ref':'R1','side':'F.SilkS','width_mm':.15,'points_mm':[[0,0],[20,0]],'graphic_uuids':['edge-1']}]}
tests['preexisting_graphic_cannot_be_whitelisted']=not validate_leaders(parse(BASE),parse(with_line),existing)[0]['valid']
assert all(tests.values()),tests
(Path(__file__).resolve().parent/'SELFTEST.json').write_text(json.dumps({'status':'PASS','fixture_checks':tests,'actual_candidate_review_run':False},indent=2)+'\n')
print('PASS',len(tests),'small native-syntax fixture checks; no actual candidate reviewed')
