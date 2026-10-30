from pathlib import Path
import json, math, hashlib, re
import numpy as np
from scipy.interpolate import CubicHermiteSpline
import trimesh
import connector_visuals as cv

P=Path(__file__).resolve().parents[1]; R=P.parent
A=P/'assets'; O=P/'output'; O.mkdir(exist_ok=True)
anchors=json.loads((P/'source/PCB_CONNECTOR_ANCHORS.json').read_text())['connectors']
def mouth(ref): return list(anchors[ref]['routing_mouth_world_mm'])
def start(ref,extra=5):
    if ref in cv.CORE:return list(cv.CORE[ref][0])
    if ref in cv.USB:return list(cv.USB[ref][0])
    if ref=='J10':return [-55.5,50.1,14.995]
    return (np.array(mouth(ref))+np.array(anchors[ref]['outward_world_unit'])*extra).tolist()
routes=[]
def route(id,label,ref,way,end,n=2,od=1.0,col=None,sleeve=True,lid=False,notes=''):
    points=([start(ref)] if ref else [])+way+[end]
    routes.append(dict(id=id,label=label,ref=ref,control_points_mm=points,conductors=n,wire_od_mm=od,
      colours=col or ['#bd302d','#20292c'],sleeve=sleeve,lid=lid,notes=notes))

# R92 world mm. Device-end positions remain explicitly conceptual reservations.
route('H01','Battery supply','J10',[[-55.5,48,18],[-31,48,18],[-7,47,17],[12,45,15],[12,56,35],[17,60,57],[24,60,61.8],[36,60,61.8]],[47,60,62],2,2.6,notes='Battery cable outlet is a proposed reservation, not measured. Retain pack fuse. Route passes through the new rounded divider notch.')
route('H02','Cytron supply','J11',[[-84,11,19],[-85,-8,21],[-85,-31,25],[-94,-50,40],[-114,-52,54]],[-124,-43,54],2,2.6)
route('H03','Cytron control','J2',[[-32.5,44,17],[-53,47,19],[-77,46,19],[-91,49,39],[-98,51,49],[-117,51,51],[-124,48,66]],[-124,39.36,66],5,1.0,['#d4b64b','#ededdd','#28866b','#357aa8','#20292c'])
route('H04','Left encoder','J3',[[-18,43,17],[-42,43,17],[-66,43,17],[-82,35,18],[-84,16,19],[-93,4,23],[-108,2,23]],[-112,8,22.6],4,1.0,['#20292c','#bd302d','#d4b64b','#eeeeea'])
route('H05','Right encoder','J4',[[-43.25,42.5,16],[-63,42.5,16],[-80,31,16],[-82,13,17],[-93,-1,19],[-119,-1,21]],[-130,-8,22.6],4,1.0,['#20292c','#bd302d','#d4b64b','#eeeeea'])
route('H06a','Left motor / shunt input','J12',[[-85,-10.8,20],[-88,-33,28],[-100,-54,43],[-121,-55,54]],[-134,-43,54],1,2.6,['#347ba1'])
route('H06b','Left motor / shunt output',None,[[-81.405,-13.335,16.395],[-88,-7,18],[-98,1,20],[-109,3,21]],[-111,8,22.6],1,2.6,['#347ba1'],notes='Starts at J12.2 cable exit. Device connector is not vendor-identified.')
route('H06c','Left motor / direct return',None,[[-137,-43,54],[-135,-55,53],[-112,-57,46],[-94,-44,29],[-94,-13,24],[-100,1,24]],[-114,8,23.5],1,2.6,['#d9dfdf'])
route('H07a','Right motor / shunt input','J13',[[-84,-23,18],[-90,-40,29],[-100,-51,47]],[-114,-43,54],1,2.6,['#347ba1'])
route('H07b','Right motor / shunt output',None,[[-81.405,-25.535,16.395],[-87,-24,18],[-94,-13,19],[-111,-4,20]],[-128,-8,22.6],1,2.6,['#347ba1'])
route('H07c','Right motor / direct return',None,[[-117,-43,54],[-111,-50,47],[-96,-42,30],[-96,-12,23],[-114,-2,24]],[-132,-8,23.5],1,2.6,['#d9dfdf'])
route('H08_chassis','STOP / chassis half','J8',[[-73.6,.1,23],[-82,-3,24],[-84,-28,20],[-76,-44,14],[-48,-45,12.3],[-10,-45,12.2],[13,-42,13],[18,-25,12.3],[18,10,12.3],[18,38,12.3],[18,70,12.3],[18,85,28],[16,85,48]], [18,80,57],4,.8,['#347ba1','#eeeeea','#2e8b6e','#d6b648'],notes='Inline disconnect near STOP button. Closed-lid route includes service loop. Candidate connector geometry only.')
route('H08_lid','STOP / removable lid tail',None,[[18,65,57],[21,65,61],[29,66,62],[41,66,62],[47,58,62],[72,58,62],[82,65,62],[76,72,62],[58,72,64]], [57,65,68],4,.8,['#347ba1','#eeeeea','#2e8b6e','#d6b648'],lid=True,notes='Moves with lid after unplugging. Service loop above battery provides slack to lift lid and reach latch. Two independent NC circuits; actual switch contacts unresolved. Uses rounded divider notch.')
route('O01','Arm bus input','J5',[[-58,-42,17],[-48,-47,17],[-10,-47,17],[19,-49,19],[28,-72,24],[73,-82,35],[111,-76,48]], [117,-45,67],3,1.6,['#d6b648','#bd302d','#20292c'],notes='Proposed arm-platform cable entry, not a verified existing passage. Arm harness stays on chassis; only the STOP tail moves with the removable lid. Existing servo chain retained.')
route('O02','Speaker lead','J7',[[10,-26,17],[11,-42,17],[-6,-49,18],[-13,-58,19]], [-22,-61,18],2,1.2,notes='Speaker mating position is a reservation; reuse factory lead if suitable.')
route('O03_left','Left cooling fan','J15',[[-27.75,-34.3,25],[-33,-44,22],[-55,-48,19],[-82,-47,20],[-85,-35,22],[-85,0,22],[-86,45,30],[-94,57,49],[-115,62,46],[-140,62,46],[-146,56,35]], [-148,53,25],2,1.0,notes='Proposed fan lead outlet; keep air aperture clear.')
route('O03_right','Right cooling fan','J14',[[-39.25,-34.3,25],[-44,-44,23],[-65,-49,20],[-88,-49,26],[-96,-59,45],[-116,-64,46],[-140,-64,46],[-146,-58,35]], [-148,-53,25],2,1.0,notes='Proposed fan lead outlet; keep air aperture clear.')
route('U01','Orange Pi power','J20',[[12,13,15],[17,6,21],[14,-8,35],[2,-16,42],[-16.5,-14,39]], [-16.52,-8.5,33.89],1,3.5,['#333b3e'],False,notes='Complete standard C-to-C 5V/3A cable; plug model/bend radius provisional.')
route('U02','Core USB data','J1',[[13,-7.2,16],[20,-1,21],[20,31,24],[17,50,25],[5,51,25]], [-6,56,26],1,3.5,['#333b3e'],False,notes='Complete standard USB data cable. Hub socket allocation is illustrative.')
route('U03','Hub upstream','', [[-29.07,-8.5,33.89],[-30,-18,40],[-4,-22,44],[20,-15,34],[21,24,31],[20,50,30]], [0,64,25],1,3.8,['#333b3e'],False,notes='Complete existing or commercial cable. Hub captive-lead length not modeled.')


# Connector correction: all wire ends are located at the rear of a mating housing.
# The motor loom has one common six-way plug (4 signals + 2 motor wires).
rr={r['id']:r for r in routes}
def change(rid,points): rr[rid]['control_points_mm']=points
change('H01',[start('J10'),[-55.5,56,16],[-45,59,17],[-29,59,18],[-6,57,20],[12,55,31],[17,60,57],[24,60,61.8],[36,60,62],[48,56,61.8],[64,56,61.8],[72,60,62],[82,60,62]])
change('H02',[start('J11'),[-84,11,19],[-85,-8,21],[-85,-31,25],[-94,-50,40],[-115,-54,54],[-124.34,-45.4,54]])
change('H03',[start('J2'),[-32.5,43,17],[-53,47,19],[-77,46,19],[-91,49,39],[-98,52,49],[-117,53,57],[-124,39.359,71],[-124,39.359,65.4]])
change('H04',[start('J3'),[-18,43,17],[-42,43,17],[-66,43,17],[-82,35,18],[-87,19,33],[-88,7.8,26],[-100,7.8,22.614]])
change('H05',[start('J4'),[-43.25,42.5,16],[-63,42.5,16],[-80,31,16],[-85,6,27],[-93,1,29],[-108,0,34],[-134,0,34],[-153,-2,34],[-153,-7.8,25],[-142,-7.8,22.614]])
change('H06a',[[-81.405,-10.795,16.395],[-85,-10.8,20],[-88,-33,28],[-100,-54,43],[-126,-57,54],[-136.84,-45.4,54]])
change('H06b',[[-81.405,-13.335,16.395],[-87,-10,25],[-90,0,29],[-90,7.8,22],[-100,7.8,16.364]])
change('H06c',[[-131.84,-45.4,54],[-131,-55,53],[-112,-57,46],[-94,-44,29],[-88,-13,30],[-87,7.8,34],[-100,7.8,28.864]])
change('H07a',[[-81.405,-22.995,16.395],[-84,-23,18],[-90,-40,29],[-100,-52,47],[-116.84,-45.4,54]])
change('H07b',[[-81.405,-25.535,16.395],[-88,-24,30],[-95,-5,29],[-108,-1,34],[-132,-1,34],[-151,-4,32],[-154,-7.8,21],[-142,-7.8,16.364]])
change('H07c',[[-111.84,-45.4,54],[-109,-53,50],[-96,-42,34],[-92,-12,28],[-108,2,34],[-138,1,34],[-153,-7.8,33],[-142,-7.8,28.864]])
# Disconnect remains near STOP, but now has the full 24.77mm mating envelope.
rr['H08_chassis']['control_points_mm'][-3:]=[[18,83,27],[21,83,49],[21,89,61],[18,82,58]]
rr['H08_lid']['control_points_mm'][0]=[18,57.23,58]
rr['H08_lid']['control_points_mm'][1]=[18,52,60]
for rid in ['O03_left','O03_right']:
    rr[rid]['control_points_mm'][-1]=[-148,54 if rid=='O03_left' else -54,37]
change('U01',[start('J20'),[22,13,17],[22,5,27],[21,-8,39],[6,-23,43],[-13,-25,39],cv.USB['Pi_power'][0]])
# Hub is moved 10mm rearward in this packaging proposal for connector clearance.
# Hub port positions come from the photo-based HB1 reference model.
change('U02',[start('J1'),[22,-7.2,18],[22,15,35],[19,49,55],[-1,55,59],[-31.2,63,60],[-31.2,78.5,61.5],cv.USB['Hub_downstream'][0]])
change('U03',[cv.USB['Hub_upstream_A'][0],[-51,-61,39],[-30,-61,42],[-5,-57,44],[19,-39,42],[21,5,39],[19,49,38],[15,68,25],[6,78.5,25]])
rr['U03']['notes']='HB1 captive USB-A lead connected to the Orange Pi DATA USB-C port through an illustrative short OTG adapter. Only the routed portion is shown; the manufacturer specifies 800mm total cable. Excess cable storage and actual adapter dimensions remain to resolve.'
for rid in ['H06b','H06c','H07b','H07c']:
    rr[rid]['notes']='Power leg changes to the existing thin six-way motor pigtail near the motor; the transition, gauge and terminal compatibility must be confirmed with the assembler. Visual wire order is not an electrical pinout.'
for rid in ['H04','H05']:
    rr[rid]['notes']='Four signal wires share the physical six-way motor plug with two power leads. Owner confirmed the current motor uses the workshop-photo connector. Vendor, pinout and mounting clocking remain unverified.'

def curve(points,step=0.9):
    p=np.array(points,float); d=np.linalg.norm(np.diff(p,axis=0),axis=1)
    good=np.r_[True,d>0.01];p=p[good];d=np.linalg.norm(np.diff(p,axis=0),axis=1);t=np.r_[0,np.cumsum(d)]
    der=np.zeros_like(p);der[0]=(p[1]-p[0])/d[0];der[-1]=(p[-1]-p[-2])/d[-1]
    for i in range(1,len(p)-1):der[i]=.78*((p[i]-p[i-1])/d[i-1]+(p[i+1]-p[i])/d[i])/2
    f=CubicHermiteSpline(t,p,der,axis=0)
    tt=np.unique(np.r_[np.linspace(0,t[-1],max(12,int(t[-1]/step)+1)),t])
    return f(tt)

def frames(v):
    tangent=np.gradient(v,axis=0);tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-10)
    normal=[];prev=np.array([0.,0.,1.])
    for t in tangent:
        n=prev-t*np.dot(prev,t)
        if np.linalg.norm(n)<.01:n=np.cross(t,[1,0,0] if abs(t[0])<.8 else [0,1,0])
        n/=np.linalg.norm(n);normal.append(n);prev=n
    normal=np.array(normal);binorm=np.cross(tangent,normal)
    return tangent,normal,binorm

def tube(v,r,sides=10,open_seam=False):
    _,n,b=frames(v)
    theta=np.linspace(.07,2*np.pi-.07,sides) if open_seam else np.arange(sides)*2*np.pi/sides
    rad=np.asarray(r)[:,None,None] if np.ndim(r) else r
    verts=(v[:,None,:]+rad*(np.cos(theta)[None,:,None]*n[:,None,:]+np.sin(theta)[None,:,None]*b[:,None,:])).reshape(-1,3)
    faces=[]
    for i in range(len(v)-1):
        for j in range(sides-1 if open_seam else sides):
            a=i*sides+j;bb=i*sides+(j+1)%sides;c=(i+1)*sides+j;dd=(i+1)*sides+(j+1)%sides
            faces.extend([[a,bb,dd],[a,dd,c]])
    if not open_seam:
        for j in range(1,sides-1):faces.extend([[0,j+1,j],[(len(v)-1)*sides,(len(v)-1)*sides+j,(len(v)-1)*sides+j+1]])
    return trimesh.Trimesh(vertices=verts,faces=np.array(faces),process=False)

def rgb(s):return np.array([int(s[i:i+2],16) for i in (1,3,5)]+[255],dtype=np.uint8)
scene={}; route_records=[]
def add(name,mesh,color,group,route_id=None):
    scene[name]={'vertices':np.asarray(mesh.vertices),'faces':np.asarray(mesh.faces,dtype=np.int32),'color':np.array(color),'group':group,'route_id':route_id}
def box(name,center,size,color,group='CONNECTOR',direction=None):
    m=trimesh.creation.box(extents=size)
    if direction is not None:
        xf=trimesh.geometry.align_vectors([0,1,0],direction);m.apply_transform(xf)
    m.apply_translation(center);add(name,m,color,group)

for r in routes:
    if r['id'] in ['H06a','H07a']:
        r['control_points_mm'][0][1]=anchors[r['ref']]['pads'][0]['world_xy_mm'][1]
    pts=curve(r['control_points_mm']);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    _,normal,binorm=frames(pts);n=r['conductors'];od=r['wire_od_mm'];offset=0 if n==1 else od*(.54 if n==2 else .9)
    wirelengths=[]
    for w in range(n):
        theta=2*np.pi*w/n
        v=pts+offset*(normal*np.cos(theta)+binorm*np.sin(theta))
        targets=None
        if r['ref'] in cv.CORE: targets=cv.core_points(r['ref'])
        elif r['ref']=='J10': targets=[np.array(start('J10'))+[-2.5,0,0],np.array(start('J10'))+[2.5,0,0]]
        elif r['ref'] in ['J11','J12','J13']:
            pads=anchors[r['ref']]['pads']; targets=[np.array([pts[0,0],p['world_xy_mm'][1],pts[0,2]]) for p in pads[:n]]
        if targets is not None:
            delta=targets[w]-v[0];v+=np.clip(1-s/13,0,1)[:,None]**2*delta
        targets_end=None
        if r['id']=='H04':targets_end=cv.motor_points('left',[1,2,3,4])
        if r['id']=='H05':targets_end=cv.motor_points('right',[1,2,3,4])
        if r['id']=='H03':targets_end=[np.array([-124+(i-2)*2.54,39.359,65.4]) for i in range(5)]
        if r['id']=='O01':targets_end=[np.array([117+(i-1)*2.5,-45,67]) for i in range(3)]
        if r['id']=='H02':targets_end=[np.array([-126.84,-45.4,54]),np.array([-121.84,-45.4,54])]
        if r['id']=='H01':targets_end=[np.array([82,57.5,62]),np.array([82,62.5,62])]
        if r['id']=='H08_chassis':targets_end=[np.array([18+xx,82,58+zz]) for xx,zz in [(-1.5,-1.5),(1.5,-1.5),(-1.5,1.5),(1.5,1.5)]]
        if r['id']=='H08_lid':
            target=np.array([18+[-1.5,1.5,-1.5,1.5][w],57.23,58+[-1.5,-1.5,1.5,1.5][w]])
            v+=np.clip(1-s/12,0,1)[:,None]**2*(target-v[0])
        if targets_end is not None:
            v+=np.clip(1-(s[-1]-s)/16,0,1)[:,None]**2*(targets_end[w]-v[-1])
        rad=np.full(len(v),od/2)
        if r['id'] in ['H06b','H06c','H07b','H07c']:
            # Existing motor lead at the contact, heavier external harness upstream.
            blend=np.clip((s[-1]-s-16)/10,0,1);rad=.625+(od/2-.625)*blend
        m=tube(v,rad,12);col=rgb(r['colours'][w%len(r['colours'])]);group='LIDWIRE' if r['lid'] else 'WIRE'
        add(f'{group}__{r["id"]}__wire_{w+1}',m,col,group,r['id'])
        wirelengths.append(float(np.linalg.norm(np.diff(v,axis=0),axis=1).sum()))
    radius=offset+od/2+.35
    if r['sleeve'] and s[-1]>45:
        sel=(s>13)&(s<s[-1]-16);v=pts[sel]
        if len(v)>3:
            group='LIDWIRE' if r['lid'] else 'SLEEVE'
            add(f'{group}__{r["id"]}__split_sleeve',tube(v,radius,14,True),rgb('#303b41'),group,r['id'])
            # Counter-wound fine strands give a visible braided texture without hiding branches.
            _,nn,bb=frames(v);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(v,axis=0),axis=1))]
            for sign in [-1,1]:
                th=sign*ss*2*np.pi/7.0
                vv=v+(radius+.07)*(nn*np.cos(th[:,None])+bb*np.sin(th[:,None]))
                add(f'{group}__{r["id"]}__braid_{sign}',tube(vv,.09,5),rgb('#647078'),group,r['id'])
            # Short strain-relief bands at sleeve ends.
            for j in [0,len(v)-5]:
                vv=v[j:j+5]
                if len(vv)>1:add(f'{group}__{r["id"]}__band_{j}',tube(vv,radius+.22,12),rgb('#171e22'),group,r['id'])
    route_records.append({**r,'points_mm':pts.round(4).tolist(),'centreline_mm':round(float(s[-1]),1),'individual_wire_lengths_mm':[round(x,1) for x in wirelengths],
      'sleeve_outer_diameter_mm':round(2*radius,2),'length_definition':'Modeled connector-exit-to-exit geometric path incl. drawn service slack; not a validated wire cut length.',
      'endpoint_accuracy':'Dimensioned visual mating housings for Core; motor six-way topology photo-confirmed. Candidate/provisional device interfaces are listed in CONNECTOR_PLACEMENT.json.'})
# Dimensioned connector reconstructions + exact native fixed Core headers.
connector_records=cv.add_models(add,box)
cv.context_models(add,box,tube,curve)
(O/'CONNECTOR_PLACEMENT.json').write_text(json.dumps({'status':'VISUAL_INTERFACE_STUDY_NOT_FIT_CERTIFICATION','connectors':connector_records},indent=2)+'\n')

for ref,rids in [('J11',['H02','H02']),('J12',['H06a','H06b']),('J13',['H07a','H07b'])]:
    for i,pad in enumerate(anchors[ref]['pads']):
        y=pad['world_xy_mm'][1];rid=rids[i]
        v=np.array([[-81.6,y,16.395],[-75.5,y,16.395]])
        add(f'CONNECTOR__{rid}__{ref}_ferrule_{i}',tube(v,.85,12),rgb('#a1abad'),'CONNECTOR',rid)

# Ties are removable, and are placed only at accepted integrated-hull anchor positions.
mount_json=A/'tie_anchors_variant.json'
mount_files=list(A.glob('*anchor*'))
tie_stations=[('T01',18,-25,9.113,90),('T02',18,38,9.113,90),('T03',18,70,9.113,90),('T04',-48,-45,9.116,0),('T05',-10,-45,8.973,0)]
for name,x,y,roof,ang in tie_stations:
    th=np.linspace(0,2*np.pi,85)
    # A strap passes below the bridge and around the wires; its rectangular profile is a visual allowance.
    side=np.array([-math.sin(math.radians(ang)),math.cos(math.radians(ang)),0.])
    height=7.7 if name in ['T04','T05'] else 4.9
    ctr=np.array([x,y,roof+(3.9 if name in ['T04','T05'] else 1.1)]);radial=np.cos(th)[:,None]*side*4.5+np.sin(th)[:,None]*np.array([0,0,height]);v=ctr+radial
    axis=np.array([math.cos(math.radians(ang)),math.sin(math.radians(ang)),0.]);radial/=np.linalg.norm(radial,axis=1)[:,None]
    verts=np.stack([v-axis*1.25-radial*.32,v+axis*1.25-radial*.32,v+axis*1.25+radial*.32,v-axis*1.25+radial*.32],axis=1).reshape(-1,3)
    faces=[]
    for i in range(len(v)-1):
        for j in range(4):
            a=i*4+j;b=i*4+(j+1)%4;cc=(i+1)*4+j;dd=(i+1)*4+(j+1)%4;faces.extend([[a,b,dd],[a,dd,cc]])
    add('TIE__'+name,trimesh.Trimesh(vertices=verts,faces=faces,process=False),rgb('#c2a257'),'TIE')
    box('TIE__'+name+'__head',ctr+side*4.8+[0,0,1],[3.2,3.2,2.5],rgb('#c2a257'),'TIE')

# Base scene: latest context assets only. Outdated Core geometry is never imported.
context=np.load(A/'NON_CORE_CONTEXT_MESH.npz')
for key in context.files:
    if not key.endswith('_vertices'):continue
    name=key[:-9];v=context[key];f=context[name+'_faces']
    if name=='Hull_V07' and (A/'HULL_WITH_TIES_AND_NOTCH.npz').exists():
        newhull=np.load(A/'HULL_WITH_TIES_AND_NOTCH.npz');v=newhull['Hull_V07_vertices'];f=newhull['Hull_V07_faces']
    if not len(v) or not len(f):continue
    if name=='Hoco_HB1_USB_A_body_envelope':continue
    if name.startswith('OrangePi_cooler') or (name.startswith('Encoder_') and name.endswith('_connector')):continue
    if name in ['Hoco_cradle','Hoco_HB1_USB_A_body_envelope']:v=v+np.array([0,10,0])
    group='CONTEXT'
    if name=='Hull_V07':group='HULL'
    elif name.startswith('OrangePi_'):group='PI'
    elif name.startswith('Upper_cover'):group='LID'
    elif 'Emergency_Stop' in name:group='STOP'
    color=context[name+'_facecolors'] if name+'_facecolors' in context else context[name+'_color']
    color=np.asarray(color)
    if color.max()<=1:color=np.clip(color*255,0,255).astype(np.uint8)
    centers=v[f].mean(axis=1)
    if name=='OrangePi_native_9':
        color=np.tile(rgb('#176c3d')[:3],(len(f),1));color[centers[:,2]>32.805]=rgb('#242a2f')[:3];color[(centers[:,2]>32.805)&(centers[:,2]<33.01)]=rgb('#898f93')[:3]
    if name=='OrangePi_native_4':
        color=np.tile(rgb('#20262a')[:3],(len(f),1));color[centers[:,2]>35.7]=rgb('#bc9b55')[:3]
    if name in ('OrangePi_native_6','OrangePi_native_7','OrangePi_native_8'):color=rgb('#494039')
    if name=='Hull_V07' or name=='Hoco_cradle':color=rgb('#242a2e')
    if name=='Hoco_HB1_USB_A_body_envelope':color=rgb('#3a4247')
    if name=='Battery_140x73x48_envelope':color=rgb('#3b727b')
    scene[group+'__'+name]={'vertices':v,'faces':f,'color':color,'group':group,'route_id':None}
# Native speaker geometry, re-tessellated from the original R92 STEP (not redrawn).
sp=np.load(A/'Speaker_3W_4Ohm_original.npz');sv=sp['vertices'];sf=sp['faces'];sc=sv[sf].mean(1)
col=np.tile(rgb('#414548'),(len(sf),1));col[sc[:,2]<13.5]=rgb('#a3aaa7');col[(sc[:,2]>24.5)]=rgb('#787f81')
scene['CONTEXT__Speaker_R92_original']={'vertices':sv,'faces':sf,'color':col,'group':'CONTEXT','route_id':None}
hub=np.load(A/'HOCO_HB1_VISUAL.npz')
for k in hub.files:
    if k.endswith('_vertices'):
        n=k[:-9];scene['CONTEXT__'+n]={'vertices':hub[k],'faces':hub[n+'_faces'],'color':np.r_[hub[n+'_color']*255,255],'group':'CONTEXT','route_id':None}
core=np.load(A/'current_core_mesh.npz')
scene['CORE__Core']={'vertices':core['Core_vertices'],'faces':core['Core_faces'],'color':core['Core_facecolors_rgba'],'group':'CORE','route_id':None}
# The tie bridges are already fused into Hull_V07; no separate floating overlays.

# Cooler's actual measured height is preserved, with an explicitly illustrative fin body.
box('PI__Cooler_visual',[ -38,13,42],[31,26,7],rgb('#3a4146'),'PI')
for x in np.linspace(-51,-25,12):box('PI__Cooler_fin_'+str(round(x,2)),[x,13,45.6],[.75,26,4],rgb('#565e63'),'PI')

npz={}
for name,d in scene.items():
    npz[name+'_vertices']=np.asarray(d['vertices'],np.float32);npz[name+'_faces']=np.asarray(d['faces'],np.int32)
    c=np.asarray(d['color'])
    if c.ndim==1:npz[name+'_color']=c[:3]/255.
    else:npz[name+'_facecolors']=c[:,:3]/255.
np.savez_compressed(A/'HARNESS_SCENE.npz',**npz)

gltf=trimesh.Scene()
for name,d in scene.items():
    mesh=trimesh.Trimesh(vertices=np.asarray(d['vertices'])*.001,faces=d['faces'],process=False)
    colour=np.asarray(d['color'])
    if colour.ndim==1:mesh.visual.face_colors=colour
    else:mesh.visual.face_colors=colour
    mesh.metadata={'routing_group':d['group'],'route_id':d['route_id'] or ''}
    gltf.add_geometry(mesh,node_name=name,geom_name=name)
gltf.metadata={'units':'metres','native_model_units':'mm','purpose':'Conceptual routed harness and integrated tie-loop study, not manufacturing release','board_sha256':'cffb4a378502802a778fcee618310e6f3fa5c49ad201b0c372728368ae3520d1'}
gltf.export(O/'MOSS_HARNESS_ASSEMBLY.glb')
harness=trimesh.Scene()
for name,d in scene.items():
    if d['group'] not in ['WIRE','SLEEVE','CONNECTOR','TIE','LIDWIRE','LIDCONNECTOR']:continue
    mesh=trimesh.Trimesh(vertices=np.asarray(d['vertices'])*.001,faces=d['faces'],process=False)
    mesh.visual.face_colors=d['color'];harness.add_geometry(mesh,node_name=name,geom_name=name)
harness.export(O/'MOSS_HARNESS_ONLY.glb')
(O/'ROUTE_LENGTHS.json').write_text(json.dumps({'units':'mm','status':'CAD_ROUTING_ESTIMATES_NOT_CUT_LENGTHS','routes':route_records,'tie_stations':tie_stations},indent=2)+'\n')
(P/'source/ROUTE_CONTROL_POINTS.json').write_text(json.dumps(routes,indent=2)+'\n')
report={'board_sha256':gltf.metadata['board_sha256'],'routes':len(routes),'scene_meshes':len(scene),'triangles':sum(len(d['faces']) for d in scene.values()),'units_GLTF':'metres','units_source':'mm','conceptual_geometry':['Simplified connector housings reconstructed from public dimensions; fixed board connectors from KiCad','Inline stop connector','Battery envelope and outlet; photo-based HB1 visual model, shifted +10mm Y; 800mm commercial lead excess not represented','Sleeve diameters, wire OD, bend radii and routing','Cooler illustration','Arm exit location'],'outputs':['MOSS_HARNESS_ASSEMBLY.glb','MOSS_HARNESS_ONLY.glb','ROUTE_LENGTHS.json']}
(O/'MODEL_SCOPE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
print('Route lengths mm',[(r['id'],r['centreline_mm']) for r in route_records])
