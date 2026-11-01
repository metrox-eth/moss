from pathlib import Path
import json, math, hashlib, re
import numpy as np
from scipy.interpolate import CubicHermiteSpline
import trimesh
import connector_visuals as cv

P=Path(__file__).resolve().parents[1]; R=P.parent
A=P/'assets'; O=P/'output'; O.mkdir(exist_ok=True)
anchors=json.loads((P/'source/PCB_CONNECTOR_ANCHORS.json').read_text())['connectors']
def start(ref,extra=5):
    if ref in cv.CORE:return list(cv.CORE[ref][0])
    if ref in cv.USB:return list(cv.USB[ref][0])
    if ref=='J10':return cv.BATTERY_EXIT.tolist()
    if ref=='J11':return [-81.405,11.005,16.395]
    raise KeyError(ref)
routes=[]
def route(id,label,ref,way,end,n=2,od=1.0,col=None,sleeve=True,lid=False,notes='',wire_ods=None):
    points=([start(ref)] if ref else [])+way+[end]
    routes.append(dict(id=id,label=label,ref=ref,control_points_mm=points,conductors=n,wire_od_mm=od,
      wire_ods_mm=wire_ods or [od]*n,colours=col or ['#bd302d','#20292c'],sleeve=sleeve,lid=lid,notes=notes))

# FinalPCB7d88... Native R92 frame, millimetres. All current Core exits are
# derived from the native fixed headers; cablebody seating remains declared.
route('H01','Battery supply','J10',[[-55.5,40,38],[-47,49,38],[-27,52,38],[-6,55,39],[13,57,46],[17,60,58],[36,60,62],[48,56,62],[64,56,62],[72,60,62]],[82,60,62],2,2.6,['#20292c','#bd302d'],notes='Core vertical XT30. Retain the external15A pack fuse. Battery outlet is a packaging reservation, not measured; route uses the divider notch.')
route('H02','Cytron supply','J11',[[-87,11,20],[-88,-10,26],[-90,-34,32],[-101,-58,44],[-119,-59,54]],[-124.34,-45.4,54],2,2.6,notes='Separate J11 supply remains. Group with H03 near the driver in one loom assembly; do not count J2 as the driver supply.')
route('H03','Cytron combined link','J2',[[-37.5,37.5,36],[-37.5,44,47],[-42,51,56],[-62,55,61],[-82,55,62]],[-93,52,62],9,1.8,['#d4b64b','#ededdd','#28866b','#357aa8','#20292c','#347ba1','#d9dfdf','#9967b0','#e59a4b'],notes='Nine-wire common trunk: PWM1,DIR1,PWM2,DIR2,GND and four bridge outputs. Cavity10 empty. Fanout at Cytron is integral to this same cable assembly; J11 remains the separate supply.',wire_ods=[1.5]*5+[1.8]*4)
route('H04','Left motor and encoder','J3',[[-75,-8.5,33],[-83,-8.5,37],[-88,-3,37],[-89,7.8,33],[-93,7.8,24]],[-100,7.8,22.614],6,1.8,['#347ba1','#d9dfdf','#20292c','#bd302d','#d4b64b','#eeeeea'],notes='One six-wire Core plug to the supplied six-wire motor pigtail. First article maps physical stock cavities by continuity to M1/M2,GND,VCC,C1/C2; visual stock cavity order is not an approved wirelist.',wire_ods=[1.8,1.8,1.5,1.5,1.5,1.5])
route('H05','Right motor and encoder','J4',[[-77,-19.9,32],[-87,-20,32],[-93,-2,30],[-110,0,31],[-135,0,33],[-153,-2,32],[-154,-7.8,23]],[-142,-7.8,22.614],6,1.8,['#347ba1','#d9dfdf','#20292c','#bd302d','#d4b64b','#eeeeea'],notes='One six-wire Core plug. Retain supplied motor pigtail; stock physical cavity assignment requires the same recorded continuity map as H04.',wire_ods=[1.8,1.8,1.5,1.5,1.5,1.5])
route('H08_chassis','STOP / chassis half','J8',[[-18,36,24],[-11,41,25],[3,43,24],[13,46,20],[18,55,17],[18,70,17],[18,83,28],[21,83,49],[21,81,61]],[18,74,58],4,.7,['#347ba1','#eeeeea','#2e8b6e','#d6b648'],notes='J8 cavities1,2,5,6 only. PicoBlade51021/51047 disconnect near STOP. Two separate NC circuits,28AWG.')
route('H08_lid','STOP / removable lid tail',None,[[18,65,58],[18,65,62],[29,66,63],[41,66,63],[47,58,62],[72,58,62],[82,65,62],[76,72,62],[58,72,64]],[57,65,68],4,.7,['#347ba1','#eeeeea','#2e8b6e','#d6b648'],lid=True,notes='Service loop moves with the lid after disconnecting X08. Documented new-kit switch has two independent NC contact pairs; identify the old unmarked switch by continuity before reuse.')
route('O01','Arm bus input','J5',[[-58,-35,28],[-48,-45,23],[-10,-47,23],[19,-49,24],[28,-72,28],[73,-82,38],[111,-76,50]],[117,-45,67],3,1.6,['#d6b648','#bd302d','#20292c'],notes='Vertical SPOX mate. Existing arm chain retained; proposed arm-platform cable entry is not an existing hole qualification.')
route('O02','Speaker lead','J7',[[5,-29,27],[11,-41,26],[-4,-55,25]],[-22,-61,18],2,1.2,notes='Vertical PH mate. Differential BTL pair: neither wire is GND. Retain factory lead where compatible; speaker terminal outlet is reserved.')
route('O03_left','Fan 1 / left cooling fan','J14',[[-52,-41,30],[-73,-45,31],[-86,-43,33],[-90,-20,35],[-91,8,37],[-91,50,44],[-113,62,46],[-140,62,46],[-146,58,39]],[-148,54,37],2,1.0,notes='Fan1 uses J14. Proposed lead corner on30mm fan. Fused3S positive andGND, noPWM/tach.')
route('O03_right','Fan 2 / right cooling fan','J15',[[-45,-43,31],[-65,-49,32],[-88,-51,35],[-98,-61,44],[-116,-64,46],[-140,-64,46],[-146,-58,39]],[-148,-54,37],2,1.0,notes='Fan2 uses J15. Same12V fan pair, positive/GND. Air aperture kept clear in the declared route.')
route('U01','Orange Pi POWER','J20',[[21,13,18],[21,4,29],[19,-12,40],[7,-26,43],[-13,-27,39]],cv.USB['Pi_power'][0],1,3.5,['#333b3e'],False,notes='Commercial C-to-C5V3A cable. J20 is power OUT to Pi POWER only; body/bend dimensions depend on the purchased cable.')
route('U02','Core USB data','J1',[[21,-7.2,19],[21,13,36],[19,44,51],[3,55,59],[-20,63,61],[-31.2,73,61]],cv.USB['Hub_downstream'][0],1,3.5,['#333b3e'],False,notes='Commercial USB data cable: hub downstream to Core J1. Hub captive cable and four occupied downstream ports retained.')
route('U03','Hub upstream / Pi DATA',None,[cv.USB['Hub_upstream_A'][0],[-51,-61,39],[-30,-61,42],[-5,-57,44],[19,-39,43],[20,-10,42],[20,24,36],[19,51,31],[14,72,25]],[6,78.5,25],1,3.8,['#333b3e'],False,notes='HB1 captive USB-A lead via short OTG adapter into Pi DATA. Manufacturer800mm total lead requires excess storage; scene represents only routed portion.')
rr={r['id']:r for r in routes}
# At Cytron the combined9-way link fans to its5-way control header and four
# winding output terminals. Supply remains H02/J11, not a tenth wire in J2.
rr['H03']['end_paths_mm']=[]
for i in range(5):
 x=-124+(i-2)*2.54
 rr['H03']['end_paths_mm'].append([[-105,52,61.5],[-117,49,61.5],[x,44,65.8],[x,41,67.0],[x,39.359,67.0],[x,39.359,65.4]])
rr['H03']['power_branch_points_mm']=[[-93,52,62],[-88,43,62],[-87,10,62],[-89,-36,61],[-104,-58,59],[-124.34,-54,57]]
rr['H03']['power_terminal_points_mm']=[[-136.84,-45.4,54],[-131.84,-45.4,54],[-116.84,-45.4,54],[-111.84,-45.4,54]]
for i,x in enumerate([-136.84,-131.84,-116.84,-111.84]):
 rr['H03']['end_paths_mm'].append(rr['H03']['power_branch_points_mm'][1:]+[[x,-45.4,54]])

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

def packed_offsets(r):
    n=r['conductors'];ods=np.array(r['wire_ods_mm'])
    if r['id']=='H03': q=np.array([[0,0],[-2.45,0],[2.45,0],[0,-2.45],[0,2.45],[-1.2,-1.2],[1.2,-1.2],[-1.2,1.2],[1.2,1.2]],float)
    elif r['id']in['H04','H05']:q=np.array([[-.95,0],[.95,0],[-.95,-1.7],[.95,-1.7],[-.95,1.7],[.95,1.7]])
    elif n==1:q=np.zeros((1,2))
    else:
      rad=max(ods)/(2*math.sin(math.pi/n))+.08
      q=np.array([[rad*math.cos(2*math.pi*w/n),rad*math.sin(2*math.pi*w/n)]for w in range(n)])
    for i in range(n):
      for j in range(i):assert np.linalg.norm(q[i]-q[j])>=(ods[i]+ods[j])/2-.001,(r['id'],i,j)
    return q,float(max(np.linalg.norm(q,axis=1)+ods/2)+.35)

for r in routes:
    pts=curve(r['control_points_mm']);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    _,normal,binorm=frames(pts);n=r['conductors'];offsets,radius=packed_offsets(r)
    wirelengths=[];wire_paths=[];wireendpoint=[]
    for w in range(n):
        od=r['wire_ods_mm'][w];v=pts+offsets[w,0]*normal+offsets[w,1]*binorm
        targets=None
        if r['ref'] in cv.CORE:targets=cv.core_points(r['ref'])
        elif r['ref']=='J10':targets=[np.array([*next(p['world_xy_mm']for p in anchors['J10']['pads']if p['pad']==str(i+1)),pts[0,2]])for i in range(n)]
        elif r['ref']=='J11':targets=[np.array([pts[0,0],p['world_xy_mm'][1],pts[0,2]])for p in sorted(anchors['J11']['pads'],key=lambda p:p['pad'])]
        if targets is not None:
            v+=np.clip(1-s/16,0,1)[:,None]**2*(targets[w]-v[0])
        if r['id']=='H08_lid':v+=np.clip(1-s/12,0,1)[:,None]**2*(np.array([18+(w-1.5)*1.25,65,58])-v[0])
        targets_end=None
        if r['id']=='H04':targets_end=cv.motor_points('left',[0,5,1,4,3,2])
        if r['id']=='H05':targets_end=cv.motor_points('right',[0,5,1,4,3,2])
        if r['id']=='O01':targets_end=[np.array([117+(i-1)*2.5,-45,67])for i in range(3)]
        if r['id']=='H02':targets_end=[np.array([-126.84,-45.4,54]),np.array([-121.84,-45.4,54])]
        if r['id']=='H01':targets_end=[np.array([82,57.5,62]),np.array([82,62.5,62])]
        if r['id']=='H08_chassis':targets_end=[np.array([18+(i-1.5)*1.25,74,58])for i in range(4)]
        if targets_end is not None:v+=np.clip(1-(s[-1]-s)/18,0,1)[:,None]**2*(targets_end[w]-v[-1])
        if 'end_paths_mm'in r:
            if w<5:tail=curve([v[-1].tolist()]+r['end_paths_mm'][w])
            else:
                tail=curve(r['power_branch_points_mm']);ts=np.r_[0,np.cumsum(np.linalg.norm(np.diff(tail,axis=0),axis=1))]
                _,tn,tb=frames(tail);th=2*math.pi*(w-5)/4
                tail+=1.4*(tn*math.cos(th)+tb*math.sin(th))
                tail+=np.clip(1-ts/20,0,1)[:,None]**2*(v[-1]-tail[0])
                target=np.array(r['power_terminal_points_mm'][w-5]);tail+=np.clip(1-(ts[-1]-ts)/35,0,1)[:,None]**2*(target-tail[-1])
            v=np.vstack([v,tail[1:]])
        m=tube(v,od/2,12);col=rgb(r['colours'][w%len(r['colours'])]);group='LIDWIRE'if r['lid']else'WIRE'
        add(f'{group}__{r["id"]}__wire_{w+1}',m,col,group,r['id'])
        wirelengths.append(float(np.linalg.norm(np.diff(v,axis=0),axis=1).sum()));wire_paths.append(v.round(4).tolist())
        wireendpoint.append({'circuit':w+1,'start_world_mm':v[0].tolist(),'end_world_mm':v[-1].tolist(),'core_cavity':([1,2,5,6][w]if r['ref']=='J8'else w+1)if r['ref']in anchors else None})
    if r['sleeve']and s[-1]>45:
        sel=(s>17)&(s<s[-1]-18);v=pts[sel]
        if len(v)>3:
            group='LIDWIRE'if r['lid']else'SLEEVE'
            add(f'{group}__{r["id"]}__split_sleeve',tube(v,radius,14,True),rgb('#303b41'),group,r['id'])
            _,nn,bb=frames(v);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(v,axis=0),axis=1))]
            for sign in[-1,1]:
                th=sign*ss*2*np.pi/7.0;vv=v+(radius+.07)*(nn*np.cos(th[:,None])+bb*np.sin(th[:,None]))
                add(f'{group}__{r["id"]}__braid_{sign}',tube(vv,.09,5),rgb('#647078'),group,r['id'])
            for j in[0,len(v)-5]:
                vv=v[j:j+5]
                if len(vv)>1:add(f'{group}__{r["id"]}__band_{j}',tube(vv,radius+.22,12),rgb('#171e22'),group,r['id'])
    if r['id']=='H03':
        branch=curve(r['power_branch_points_mm']);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(branch,axis=0),axis=1))];bp=branch[(ss>22)&(ss<ss[-1]-36)]
        add('SLEEVE__H03__four_bridge_outputs',tube(bp,2.65,14,True),rgb('#303b41'),'SLEEVE','H03')
    route_records.append({**r,'points_mm':pts.round(4).tolist(),'centreline_mm':round(float(s[-1]),1),'individual_wire_lengths_mm':[round(x,1)for x in wirelengths],
      'individual_wire_points_mm':wire_paths,'wire_endpoints':wireendpoint,'sleeve_outer_diameter_mm':round(2*radius,2),'packing_offsets_mm':offsets.tolist(),
      'length_definition':'Individual drawn wire paths, including Cytron terminal fanout; centreline is common trunk only where it branches. Not validated cut lengths.',
      'endpoint_accuracy':'Core cavity positions follow final nativePCB; reconstructed cable seats are declared reservations. Stock motor cavity order in the picture is illustrative until factory continuity mapping.'})
# Dimensioned connector reconstructions + exact native fixed Core headers.
connector_records=cv.add_models(add,box)
cv.context_models(add,box,tube,curve)
(O/'CONNECTOR_PLACEMENT.json').write_text(json.dumps({'status':'VISUAL_INTERFACE_STUDY_NOT_FIT_CERTIFICATION','connectors':connector_records},indent=2)+'\n')

for i,pad in enumerate(sorted(anchors['J11']['pads'],key=lambda p:p['pad'])):
    y=pad['world_xy_mm'][1];v=np.array([[-81.6,y,16.395],[-75.5,y,16.395]])
    add(f'CONNECTOR__H02__J11_ferrule_{i}',tube(v,.85,12),rgb('#a1abad'),'CONNECTOR','H02')

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
cc=core['Core_facecolors_rgba'].copy();green=(cc[:,1]>cc[:,0]*1.2)&(cc[:,1]>cc[:,2]*1.2)&(cc[:,1]<210)
cc[green,:3]=[27,31,34]
scene['CORE__Core']={'vertices':core['Core_vertices'],'faces':core['Core_faces'],'color':cc,'group':'CORE','route_id':None}

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
gltf.metadata={'units':'metres','native_model_units':'mm','purpose':'FinalPCB-aligned prototype harness routing; physical first article still required','board_sha256':json.loads((P/'source/PCB_CONNECTOR_ANCHORS.json').read_text())['sha256']}
gltf.export(O/'MOSS_HARNESS_ASSEMBLY.glb')
harness=trimesh.Scene()
for name,d in scene.items():
    if d['group'] not in ['WIRE','SLEEVE','CONNECTOR','TIE','LIDWIRE','LIDCONNECTOR']:continue
    mesh=trimesh.Trimesh(vertices=np.asarray(d['vertices'])*.001,faces=d['faces'],process=False)
    mesh.visual.face_colors=d['color'];harness.add_geometry(mesh,node_name=name,geom_name=name)
harness.export(O/'MOSS_HARNESS_ONLY.glb')
(O/'ROUTE_LENGTHS.json').write_text(json.dumps({'units':'mm','status':'CAD_ROUTING_ESTIMATES_NOT_CUT_LENGTHS','routes':route_records,'tie_stations':tie_stations},indent=2)+'\n')
(P/'source/ROUTE_CONTROL_POINTS.json').write_text(json.dumps(routes,indent=2)+'\n')
report={'board_sha256':gltf.metadata['board_sha256'],'hull_source_sha256':hashlib.sha256((A/'HULL_WITH_TIES_AND_NOTCH.npz').read_bytes()).hexdigest(),'Core_mount_pattern_mm':[74,71],'routes':len(routes),'custom_wire_count':sum(r['conductors']for r in routes if not r['id'].startswith('U')),'scene_meshes':len(scene),'triangles':sum(len(d['faces']) for d in scene.values()),'units_GLTF':'metres','units_source':'mm','conceptual_geometry':['Current native fixed PCB headers; cable housings dimensioned from manufacturer drawings with cavities/latches, not vendor mating CAD','Inline stop connector','Battery envelope and outlet; photo-based HB1 visual model, shifted +10mm Y; 800mm commercial lead excess not represented','Sleeve diameters, wire OD, bend radii and routing','Cooler illustration','Arm exit location'],'outputs':['MOSS_HARNESS_ASSEMBLY.glb','MOSS_HARNESS_ONLY.glb','ROUTE_LENGTHS.json']}
(O/'MODEL_SCOPE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
print('Route lengths mm',[(r['id'],r['centreline_mm']) for r in route_records])
