"""HOCO HB1 photo-based visual CAD; dimensions from HOCO's public product page.

Not manufacturer CAD. Overall envelope 78 x 25 x 25 mm; port positions,
fillets, wall thickness and end caps are visually estimated from front photographs.
"""
from pathlib import Path
import json,numpy as np,cadquery as cq
P=Path(__file__).resolve().parents[1];(P/'output').mkdir(exist_ok=True);parts={};assembly=cq.Assembly(name='HOCO_HB1_VISUAL_REFERENCE')
def add(name,s,c):
    v,f=s.tessellate(.035,.12);parts[name+'_vertices']=np.array([q.toTuple() for q in v]);parts[name+'_faces']=np.array(f);parts[name+'_color']=np.array(c)
    assembly.add(s,name=name,color=cq.Color(*c))

# Native R92 world: body X=-78..0, Y=66..91, Z=12..37. Cable at +X end.
body=cq.Workplane('XY').box(76.8,25,25).edges('|X').fillet(4).translate((-39,78.5,24.5)).val()
ports=[-31.2,-42.7,-54.3,-65.9]
for x in ports:
    body=body.cut(cq.Workplane('XY').box(6,14.2,8).translate((x,78.5,35)).val())
add('Hoco_HB1_alloy_shell',body,(.55,.58,.60))
for x in [-77.7,-.3]:
    cap=cq.Workplane('YZ').box(24.5,24.5,.6).edges('|X').fillet(3.8).translate((x,78.5,24.5)).val()
    add('Hoco_endcap_'+str(x),cap,(.20,.23,.25))
for i,x in enumerate(ports):
    shell=cq.Workplane('XY').box(5.9,14,7).translate((x,78.5,33.4)).val()
    shell=shell.cut(cq.Workplane('XY').box(4.8,12.2,8).translate((x,78.5,34)).val())
    add('Hoco_USB_A_'+str(i)+'_shell',shell,(.66,.69,.7))
    add('Hoco_USB_A_'+str(i)+'_dark',cq.Workplane('XY').box(4.8,12.2,.5).translate((x,78.5,30)).val(),(.035,.045,.05))
    add('Hoco_USB_A_'+str(i)+'_tongue',cq.Workplane('XY').box(1.15,10.4,5).translate((x-1.2,78.5,33.2)).val(),(.15,.17,.18))
    for j in range(4):
        add(f'Hoco_USB_A_{i}_contact_{j}',cq.Workplane('XY').box(.2,.75,3.5).translate((x-.58,78.5+(j-1.5)*2.2,33.5)).val(),(.72,.59,.27))
logo=cq.Workplane('XY').text('hoco.',5.6,.06,font='Arial',kind='bold',combine=True).val().rotate((0,0,0),(0,0,1),180).translate((-14.6,78.5,37))
add('Hoco_wordmark',logo,(.87,.89,.90))
g=cq.Solid.makeCylinder(2.6,6,cq.Vector(0,78.5,25),cq.Vector(1,0,0))
add('Hoco_captive_strain_relief',g,(.06,.07,.08))
np.savez_compressed(P/'assets/HOCO_HB1_VISUAL.npz',**parts)
assembly.save(str(P/'output/HOCO_HB1_Visual_Reference.step'),'STEP')
r={'status':'PHOTO_BASED_VISUAL_REFERENCE_NOT_MANUFACTURER_CAD','overall_body_mm':[78,25,25],
 'position_world_mm':{'min':[-78,66,12],'max':[0,91,37]},'ports':'Four top-facing USB-A receptacles; long axes perpendicular to hub length.',
 'source':'https://hocotech.com/product/mobile-accessories/cables/hubs-organizers/usb-hub-hb1-four-ports-usb-2-0-charging-and-data-sync/',
 'photo':'https://hocotech.com/wp-content/uploads/2018/07/hb1-four-usb-hub-silver-ports.jpg',
 'estimated':['Port positions/fillets/wall thickness/end caps/wordmark shape','Colour chosen for visual presentation'],
 'cable':'Manufacturer specifies an 80 cm captive USB-A lead. Only its routed connection and an illustrative USB-C OTG pigtail are shown; excess lead storage is not resolved.'}
(P/'output/HOCO_PROVENANCE.json').write_text(json.dumps(r,indent=2)+'\n');print('HOCO model generated',flush=True)
