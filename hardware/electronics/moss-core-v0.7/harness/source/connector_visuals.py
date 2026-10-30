"""Dimensioned visual connector bodies for the harness study.

JST envelopes/pitches from public catalog drawings; not manufacturer mating CAD.
Motor XH-style identification and clocking are photo-based. No electrical pinout
is inferred from these pictures. Native fixed Core connector geometry is retained.
"""
from pathlib import Path
import json
import numpy as np
import cadquery as cq
import trimesh

P=Path(__file__).resolve().parents[1]
CACHE=P/'assets/connector_mesh_cache'; CACHE.mkdir(exist_ok=True)
WHITE=[225,225,207,255]; METAL=[163,171,174,255]; GOLD=[200,164,71,255]
BLACK=[36,43,48,255]; YELLOW=[230,179,48,255]

def shape_mesh(s):
    v,f=s.tessellate(.07,.18)
    return trimesh.Trimesh(vertices=np.array([q.toTuple() for q in v]),faces=np.array(f),process=False)

def cached(name,maker):
    p=CACHE/(name+'.npz')
    if p.exists():
        z=np.load(p);return trimesh.Trimesh(z['v'],z['f'],process=False)
    m=shape_mesh(maker());np.savez_compressed(p,v=m.vertices,f=m.faces);return m

def block(w,l,h,c=(0,0,0)):
    return cq.Workplane('XY').box(w,l,h).translate(c).val()

def frame(outlet,row,out):
    row=np.array(row,float);out=np.array(out,float)
    up=np.cross(row,out)
    return np.column_stack([row,out,up]),np.array(outlet,float)

def transform(mesh,outlet,row,out):
    m=mesh.copy();b,t=frame(outlet,row,out);m.vertices=m.vertices@b.T+t;return m

def housing(n,pitch,width,length,height,outside,hole_od,neck=None):
    """Local +Y is wire exit. Outlet plane Y=0, contacts centred Z=0."""
    neck=neck or (width-.55,height-.55)
    s=block(neck[0],length-outside,neck[1],(0,-(length+outside)/2,0)).fuse(
        block(width,outside,height,(0,-outside/2,0)))
    for i in range(n):
        x=(i-(n-1)/2)*pitch
        hole=cq.Solid.makeCylinder(hole_od/2,length+1,cq.Vector(x,.5,0),cq.Vector(0,-1,0))
        s=s.cut(hole)
        # Contact inspection window on rear collar, not a painted dot.
        s=s.cut(block(min(.7,pitch*.55),min(outside*.55,1.5),height/2,(x,-outside*.55,height/2)))
    # Raised moulded friction/locking feature; simplified from the catalogue.
    latch=block(max(1.2,width*.5),max(.8,outside*.65),.35,(0,-outside*.6,height/2+.10))
    return s.fuse(latch)

# Wire-exit frames, not SMT pad coordinates. Each tuple: (origin,row,+out).
CORE={
 'J2':([-32.5,36.65,13.245],[1,0,0],[0,1,0],'GH',5,1.25,7.5,5.7,3.75,2.2,1.0),
 'J3':([-18,36.65,13.245],[1,0,0],[0,1,0],'GH',4,1.25,6.25,5.7,3.75,2.2,1.0),
 'J4':([-43.25,36.65,13.245],[1,0,0],[0,1,0],'GH',4,1.25,6.25,5.7,3.75,2.2,1.0),
 'J8':([-73.625,.1,17.895],[0,-1,0],[0,0,1],'SH',6,1,7,5,2.8,1.98,.8),
 'J14':([-39.25,-34.8,21.395],[-1,0,0],[0,0,1],'XH',2,2.5,7.3,7.5,5.7,2.8,1.3),
 'J15':([-27.75,-34.8,21.395],[-1,0,0],[0,0,1],'XH',2,2.5,7.3,7.5,5.7,2.8,1.3),
 'J7':([2.8,-26,14.095],[0,-1,0],[1,0,0],'PH',2,2,5.8,6.35,4.5,2,1.4),
 'J5':([-58,-38.55,14.045],[-1,0,0],[0,-1,0],'SPOX',3,2.5,8.9,8,4.2,2.6,1.7),
}
USB={
 'J1':([17,-7.2,13.195],[0,1,0],[1,0,0]),
 'J20':([17,13,13.195],[0,1,0],[1,0,0]),
 'Pi_power':([-16.5241,-18.8774,33.887],[-1,0,0],[0,-1,0]),
 'Pi_data':([-29.0741,-18.9774,33.887],[-1,0,0],[0,-1,0]),
 'Hub_downstream':([-31.2,78.5,56.5],[0,1,0],[0,0,1]),
 'Hub_upstream_A':([-51,-55,37.5],[1,0,0],[0,-1,0]),
}
MOTOR={
 'left':{'origin':[-112,10.8,22.614],'outlet':[-100,7.8,22.614], 'row':[0,0,1], 'out':[1,0,0], 'up':[0,-1,0]},
 'right':{'origin':[-130,-10.8,22.614],'outlet':[-142,-7.8,22.614], 'row':[0,0,1], 'out':[-1,0,0], 'up':[0,1,0]},
}

def core_points(ref):
    a=CORE[ref];p=np.array(a[0]);r=np.array(a[1]);n,pitch=a[4:6]
    points=[p+r*(i-(n-1)/2)*pitch for i in range(n)]
    if ref in ['J2','J3','J4','J5','J7']:points=points[::-1]
    return [points[i] for i in ([0,1,4,5] if ref=='J8' else range(n))]

def motor_points(side,subset):
    d=MOTOR[side];p=np.array(d['outlet']);r=np.array(d['row'])
    return [p+r*(i-2.5)*2.5 for i in subset]

def add_models(add,box):
    records=[]
    for ref,a in CORE.items():
        outlet,row,out,family,n,pitch,width,length,height,outside,od=a
        key=f'{family}_{n}_{pitch}_{width}_{length}_{height}_{outside}'
        m=cached(key,lambda n=n,pitch=pitch,width=width,length=length,height=height,outside=outside,od=od:
            housing(n,pitch,width,length,height,outside,od, (width-1.6,height-1.5) if family=='XH' else None))
        rid={'J2':'H03','J3':'H04','J4':'H05','J8':'H08_chassis','J14':'O03_right','J15':'O03_left','J5':'O01','J7':'O02'}[ref]
        add(f'CONNECTOR__{rid}__{ref}_{family}_housing',transform(m,outlet,row,out),WHITE,'CONNECTOR',rid)
        records.append({'ref':ref,'family':family,'circuits':n,'pitch_mm':pitch,'housing_width_mm':width,
            'housing_axial_length_mm':length,'wire_exit_world_mm':outlet,'mating_axis_world':out,
            'evidence':'Public catalogue dimensions; simplified reconstructed housing, native fixed PCB model retained.'})
    # USB-C: compact commercial cable allowance. Metal tongue enters the socket;
    # jacket sits outside it. Rubber ribs at the wire exit are distinct geometry.
    for key,(outlet,row,out) in USB.items():
        rid={'J1':'U02','J20':'U01','Pi_power':'U01','Pi_data':'U03','Hub_downstream':'U02','Hub_upstream_A':'U03'}[key]
        is_a=key.startswith('Hub_');w,h,l=(15.5,7.4,15) if is_a else (9.8,5.1,10.5)
        body=cached('USB_A_body' if is_a else 'USB_C_body',lambda w=w,h=h,l=l:block(w,l,h,(0,-l/2,0)))
        add(f'CONNECTOR__{rid}__{key}_moulding',transform(body,outlet,row,out),BLACK,'CONNECTOR',rid)
        tip=cached('USB_A_tip' if is_a else 'USB_C_tip',lambda is_a=is_a,l=l:block(12 if is_a else 8.2,7,4.5 if is_a else 2.5,(0,-l-3.5,0)))
        add(f'CONNECTOR__{rid}__{key}_shell',transform(tip,outlet,row,out),METAL,'CONNECTOR',rid)
        for j in range(3):
            rib=cached(f'usb_rib_{int(is_a)}_{j}',lambda j=j:block(5.0,1,4.4,(0,1+j*1.3,0)))
            add(f'CONNECTOR__{rid}__{key}_relief_{j}',transform(rib,outlet,row,out),BLACK,'CONNECTOR',rid)
    # Retain actual motor and encoder disc; replace only incorrect 6x8mm boxes.
    path=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels/Connector_JST.3dshapes/JST_XH_S6B-XH-A_1x06_P2.50mm_Horizontal.step')
    header=cached('KiCad_S6B_XH',lambda:cq.importers.importStep(str(path)).val())
    for side,d in MOTOR.items():
        # KiCad X row / Y rearward / Z board normal. First pin X=0.
        basis=np.column_stack([d['row'],-np.array(d['out']),d['up']])
        m=header.copy();m.vertices=(m.vertices-[6.25,0,0])@basis.T+np.array(d['origin'])
        add(f'CONTEXT__Motor_{side}_six_way_header',m,WHITE,'CONTEXT')
        p=cached('XHP6_photo_proxy',lambda:housing(6,2.5,17.3,7.5,5.7,2.8,1.35,(15.7,4.2)))
        rid='H04' if side=='left' else 'H05'
        add(f'CONNECTOR__{rid}__motor_six_way_plug',transform(p,d['outlet'],d['row'],d['out']),WHITE,'CONNECTOR',rid)
        records.append({'ref':'motor_'+side,'family':'XH-style visual match; exact vendor unverified','circuits':6,'pitch_mm':2.5,'housing_width_mm':17.3,'wire_exit_world_mm':d['outlet'],
            'evidence':'Arduitronics RU00129 product photos and MOSS workshop photos show the same six-wire interface. Retain the supplied pigtail. KiCad XH geometry is a visual reference, not a purchasing identification.'})
    # Cytron control header: one 5-way cable connector over the native 5 pins.
    m=cached('Cytron_control_5',lambda:housing(5,2.54,12.7,8.5,3.4,4.7,1.05))
    add('CONNECTOR__H03__Cytron_five_way',transform(m,[-124,39.359,65.4],[1,0,0],[0,0,1]),WHITE,'CONNECTOR','H03')
    # Ferrules enter each screw terminal; coloured insulated collars remain visible.
    terms=[('H02',-126.84),('H02',-121.84),('H06a',-136.84),('H06c',-131.84),('H07a',-116.84),('H07c',-111.84)]
    for i,(rid,x) in enumerate(terms):
        ferr=cq.Solid.makeCylinder(.85,5.0,cq.Vector(x,-43.2,54),cq.Vector(0,1,0))
        add(f'CONNECTOR__{rid}__Cytron_ferrule_{i}',shape_mesh(ferr),METAL,'CONNECTOR',rid)
        collar=cq.Solid.makeCylinder(1.55,2.2,cq.Vector(x,-45.4,54),cq.Vector(0,1,0))
        add(f'CONNECTOR__{rid}__Cytron_collar_{i}',shape_mesh(collar),[55,98,128,255],'CONNECTOR',rid)
    # Battery pair (XT30-style dimensioned visual, pack lead location provisional).
    def xt30():
        s=block(10.2,12.4,5.2,(0,-6.2,0))
        for x in [-2.5,2.5]:s=s.cut(cq.Solid.makeCylinder(1.28,13.4,cq.Vector(x,.5,0),cq.Vector(0,-1,0)))
        return s
    xt=cached('XT30U_legacy_envelope',xt30)
    # Core battery mating housing, 5mm contact pitch, not old undersized block.
    add('CONNECTOR__H01__Core_XT30_cable',transform(xt,[-55.5,50.1,14.995],[1,0,0],[0,1,0]),YELLOW,'CONNECTOR','H01')
    for key,outlet,direction in [('loom',[82,60,62],[-1,0,0]),('pack',[103,60,62],[1,0,0])]:
        add(f'CONNECTOR__H01__battery_XT30_{key}',transform(xt,outlet,[0,1,0],direction),YELLOW,'CONNECTOR','H01')
    # PicoBlade 51047/51021: official drawing gives 9 mm mated length.
    # Simplified shell and inserted receptacle; 6.75 mm width, 1.25 mm pitch.
    shell=block(6.75,8,3.3,(0,-4,0))
    shell=shell.cut(block(5.55,4,2.45,(0,-.95,0)))
    for x in [-1.25,1.25]:shell=shell.cut(block(.8,1.8,1,(x,-2,1.5)))
    for i in range(4):
        x=(i-1.5)*1.25
        shell=shell.cut(cq.Solid.makeCylinder(.38,9,cq.Vector(x,.5,0),cq.Vector(0,-1,0)))
    add('LIDCONNECTOR__H08_lid__PicoBlade_51047',transform(shape_mesh(shell),[18,65,58],[1,0,0],[0,-1,0]),WHITE,'LIDCONNECTOR','H08_lid')
    recept=block(6.75,1,3.2,(0,-.5,0)).fuse(block(5.45,2.95,2.3,(0,-2.475,0)))
    for i in range(4):
        recept=recept.cut(cq.Solid.makeCylinder(.38,5,cq.Vector((i-1.5)*1.25,.5,0),cq.Vector(0,-1,0)))
    add('CONNECTOR__H08_chassis__PicoBlade_51021',transform(shape_mesh(recept),[18,74,58],[1,0,0],[0,1,0]),WHITE,'CONNECTOR','H08_chassis')
    records.append({'ref':'X08','family':'Molex PicoBlade 4-way','mated_axial_length_mm':9,'pitch_mm':1.25,'housing_width_mm':6.75,
        'housings':['51021-0400','51047-0400'],'contacts':['50058-8000','50133-8000'],
        'wire_spec':'28 AWG; insulation OD 0.50-0.80 mm including tolerance',
        'evidence':'Molex 510470000-SD page 2 confirms mating pair and 9 mm length. Connector contacts and JST SH accept the selected wire range; simplified visual shell.'})
    return records

def context_models(add,box,tube,curve):
    """Context hardware visually modelled to its existing packaging reservations."""
    # The actual HB1 has a captive USB-A lead. An illustrative short OTG
    # adapter couples it to the Orange Pi DATA USB-C port (not to STOP).
    box('CONNECTOR__U03__OTG_A_female_body',[-51,-29,37.5],[16,10,8],BLACK,'CONNECTOR')
    shell=block(13.8,1,6).cut(block(12.2,2,4.8))
    m=shape_mesh(shell);m.apply_translation([-51,-34.1,37.5]);add('CONNECTOR__U03__OTG_A_female_shell',m,METAL,'CONNECTOR','U03')
    a=curve([USB['Pi_data'][0],[-29.07,-24,35],[-37,-29,40],[-46,-21,40],[-51,-24,37.5]])
    add('WIRE__U03__OTG_adapter_pigtail',tube(a,1.7,12),BLACK,'WIRE','U03')
    # Fan visual model: 30x30x10 frame, open centre, hub, swept-looking blades,
    # corner mounting holes. Connector remains the photographed XH-style lead.
    frame_shape=block(30,30,10).cut(cq.Solid.makeCylinder(13,12,cq.Vector(0,0,-6)))
    for x in [-12,12]:
        for y in [-12,12]:frame_shape=frame_shape.cut(cq.Solid.makeCylinder(1.6,12,cq.Vector(x,y,-6)))
    fanmesh=cached('fan3010_frame',lambda:frame_shape)
    def fanplace(m,y):
        q=m.copy();q.vertices=q.vertices@np.array([[0,1,0],[0,0,1],[1,0,0]])+[-154,y,25.75];return q
    for side,y in [('left',42),('right',-42)]:
        add(f'CONTEXT__Fan_{side}_3010_frame',fanplace(fanmesh,y),BLACK,'CONTEXT')
        hub=shape_mesh(cq.Solid.makeCylinder(5.6,8,cq.Vector(0,0,-4)))
        add(f'CONTEXT__Fan_{side}_rotor',fanplace(hub,y),[51,59,63,255],'CONTEXT')
        for j in range(7):
            th=np.deg2rad(j*360/7)
            poly=np.array([[4,-1],[11,-4.5],[12,-1],[7,3],[4,1]])
            rot=np.array([[np.cos(th),-np.sin(th)],[np.sin(th),np.cos(th)]])
            poly=poly@rot.T
            sh=cq.Workplane('XY').polyline(poly.tolist()).close().extrude(1.8).translate((0,0,-1)).val()
            add(f'CONTEXT__Fan_{side}_blade_{j}',fanplace(shape_mesh(sh),y),[61,69,72,255],'CONTEXT')
        # Lead terminates at the moulded frame corner, clear of the blade aperture.
        box(f'CONTEXT__Fan_{side}_lead_guard',[-148,54 if side=='left' else -54,37],[2,3.6,3.2],BLACK,'CONTEXT')
    # Speaker body is restored from the existing native R92 model elsewhere.
    box('CONTEXT__Speaker_terminal',[-22,-61,18],[4,3,1.6],[156,128,67,255],'CONTEXT')
    # Pack-side pigtail is schematic packaging, not a claim about a measured outlet.
    for i,c in enumerate([[184,42,35,255],BLACK]):
        p=curve([[103,57.5+5*i,62],[111,57.5+5*i,62],[111,53+5*i,59],[105,48+5*i,57.5]])
        add(f'WIRE__H01__pack_tail_{i}',tube(p,1.3,12),c,'WIRE','H01')
    # Arm branch stops at a proper cable-to-cable three-way chain connector.
    # This identifies the service connection without claiming the arm base is fitted.
    arm=shape_mesh(housing(3,2.5,8.9,8,4.2,2.6,1.7))
    add('CONNECTOR__O01__arm_chain_service_end',transform(arm,[117,-45,67],[1,0,0],[0,-1,0]),WHITE,'CONNECTOR','O01')
