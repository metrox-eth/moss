"""MOSS harness studio film. CAD geometry, true camera motion, no raster retouching.

Frames are piped directly to FFmpeg; no temporary frame sequence on the system disk.
The exact source scene is also delivered in the offline viewer.
"""
from pathlib import Path
import argparse,json,math,subprocess,time,os
import numpy as np,vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
from PIL import Image,ImageDraw,ImageFont

P=Path(__file__).resolve().parents[1];R=P.parent;O=P/'video';O.mkdir(exist_ok=True)
ap=argparse.ArgumentParser();ap.add_argument('--stills',action='store_true');ap.add_argument('--test',action='store_true');args=ap.parse_args()
W,H,FPS,DURATION=1920,1080,24,42
VW,VH,S=1776,690,1.5;RW,RH=int(VW*S),int(VH*S)
STUDIO=(61,87,106);WHITE=(234,240,239);MINT=(108,248,199);SALMON=(254,148,126)
import imageio_ffmpeg
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
CAPTIONS=[
 (0,3,'I want MOSS to be easier to build.','A custom cable harness is the next idea I’m exploring with AI.'),
 (3,7,'Start with the connections.','One six-wire plug per motor. Separate power, USB and STOP paths.'),
 (7,10,'Then bring the loom together.','Removable sleeves. Accessible branches. Less loose wiring.'),
 (10,14,'Print the cable supports into the hull.','Five integrated tie loops hold the main routing corridors.'),
 (14,18,'One motor. One six-wire connector.','4 encoder wires + 2 motor wires. Cutaway view.'),
 (18,22,'Two circuits. Two different connectors.','STOP → JST J8. Battery → XT30 J10. Four low-current STOP wires; a separate battery feed.'),
 (22,26,'USB has its own path.','Orange Pi DATA → hub → Core J1. Core J20 supplies the Pi POWER port.'),
 (26,30,'Unplug the lid. Keep the loom in place.','STOP service loop and disconnect. Cutaway, then exploded service view.'),
 (30,35,'Could PCBWay make this kit?','They list Cable Wire Harness Assembly. I’m preparing the enquiry.'),
 (35,38,'From an idea to something I can build.','Prototype CAD, routing notes and a 3D viewer are on GitHub.'),
]
def ease(x):x=np.clip(x,0,1);return float(x*x*(3-2*x))
def ramp(t,a,b):return ease((t-a)/(b-a))
def mix(a,b,t):return np.asarray(a)+(np.asarray(b)-a)*t

ren=vtk.vtkRenderer();ren.SetBackground(.035,.055,.070);ren.SetBackground2(.12,.16,.19);ren.GradientBackgroundOn();ren.SetUseFXAA(True);ren.AutomaticLightCreationOff()
win=vtk.vtkRenderWindow();win.SetSize(RW,RH);win.SetOffScreenRendering(1);win.SetMultiSamples(0);win.AddRenderer(ren)
# SSAO disabled: it introduced screen-space banding on smooth CAD surfaces.
ren.SetPass(None)
key=vtk.vtkLight();key.SetLightTypeToSceneLight();key.SetPositional(True);key.SetConeAngle(48);key.SetExponent(4);key.SetColor(1,.94,.85);key.SetIntensity(1.25);ren.AddLight(key)
rim=vtk.vtkLight();rim.SetLightTypeToSceneLight();rim.SetColor(.64,.81,1);rim.SetIntensity(.72);ren.AddLight(rim)
fill=vtk.vtkLight();fill.SetLightTypeToSceneLight();fill.SetColor(.83,.91,1);fill.SetPosition(160,-50,300);fill.SetFocalPoint(-30,0,20);fill.SetIntensity(.27);ren.AddLight(fill)
actors={};keep=[];z=np.load(P/'assets/HARNESS_SCENE.npz');batches={}
def category(n):
 g=n.split('__')[0]
 if g in ['WIRE','SLEEVE','CONNECTOR','LIDWIRE','LIDCONNECTOR']:
  rid=n.split('__')[1]
  if g=='LIDWIRE' and any(s in n for s in ['split_sleeve','braid_','band_']):g='LIDSLEEVE'
  return (g,rid)
 if g=='CONTEXT':
  if 'Cytron' in n:return ('CYTRON','')
  if 'Drive_Motor_Left' in n or 'Encoder_positive' in n or 'Motor_left' in n:return ('MOTORLEFT','')
  if 'Drive_Motor_Right' in n or 'Encoder_negative' in n or 'Motor_right' in n:return ('MOTORRIGHT','')
  if 'Hoco_cradle' in n:return ('HULL','')
  if 'Hoco_' in n:return ('HUB','')
 if g=='MOUNT':return ('OMIT','')
 return (g,'')
for k in z.files:
 if not k.endswith('_vertices'):continue
 n=k[:-9];cat=category(n)
 if cat[0]=='OMIT':continue
 v=z[k];f=z[n+'_faces'];col=z[n+'_facecolors'] if n+'_facecolors' in z else np.broadcast_to(z[n+'_color'],(len(f),3))
 b=batches.setdefault(cat,{'v':[],'f':[],'c':[],'o':0});b['v'].append(v);b['f'].append(f+b['o']);b['c'].append(col);b['o']+=len(v)
for cat,b in batches.items():
 v=np.concatenate(b['v']);f=np.concatenate(b['f']).astype(np.int64);c=np.concatenate(b['c'])
 pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(v,deep=True));cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True));poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
 scal=numpy_to_vtk((c*255).clip(0,255).astype(np.uint8),deep=True);poly.GetCellData().SetScalars(scal)
 normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(40);normals.SplittingOn()
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());mapper.SetScalarModeToUseCellData();mapper.ScalarVisibilityOn()
 actor=vtk.vtkActor();actor.SetMapper(mapper);pr=actor.GetProperty();pr.SetAmbient(.18);pr.SetDiffuse(.82);pr.SetSpecular(.27);pr.SetSpecularPower(38);pr.SetInterpolationToPhong();ren.AddActor(actor);actors[cat]=actor;keep.extend([pts,cells,poly,scal,normals,mapper,actor])
cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,0,1)
cap=vtk.vtkWindowToImageFilter();cap.SetInput(win);cap.SetInputBufferTypeToRGB();cap.ReadFrontBufferOff()
fontpath=P/'assets/branding/SpaceGrotesk.ttf'
def font(size,weight=500):
 f=ImageFont.truetype(str(fontpath),size);f.set_variation_by_axes([weight]);return f
corelogo=Image.open(P/'assets/branding/MOSS_CORE_V07.png').convert('RGBA')
pcbway=Image.open(P/'assets/branding/PCBWay_white.png').convert('RGBA')
family=Image.open(P/'assets/branding/Meet_the_fam_V07_PCBWay.png').convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
def paste_logo(im,logo,xy,width):
 tile=logo.resize((width,round(width*logo.height/logo.width)),Image.Resampling.LANCZOS);im.paste(tile,xy,tile)

def set_pose(t):
 focus=np.array([-10,0,32.]);scale=154;az=-55+t*3;elev=55
 if 3<=t<10:focus=np.array([-10,15,39.]);scale=135;az=-48+(t-3)*8;elev=53
 if 10<=t<14:
  q=ramp(t,11.4,13.7);focus=mix([-10,10,31],[14,10,15],q);scale=151-91*q;az=10-26*q;elev=60-13*q
 if 14<=t<18:focus=np.array([-103,8,24.]);scale=28-4*ramp(t,14,18);az=-28+(t-14)*7;elev=27
 if 18<=t<22:focus=np.array([-38,4,25.]);scale=70;az=-136;elev=69
 if 22<=t<26:focus=np.array([-38,52,33.]);scale=55-6*ramp(t,22,26);az=27+(t-22)*10;elev=58
 if 26<=t<30:
  q=ramp(t,27.7,29.5);focus=mix([25,68,63],[-2,18,75],q);scale=40+91*q;az=100-30*q;elev=52+6*q
 if 30<=t<35:focus=np.array([-15,4,33.]);scale=151;az=-55+(t-30)*6;elev=56
 if 35<=t<38:focus=np.array([-15,0,32.]);scale=147-10*ramp(t,35,38);az=-25+(t-35)*5;elev=57
 direction=np.array([math.cos(math.radians(az))*math.cos(math.radians(elev)),math.sin(math.radians(az))*math.cos(math.radians(elev)),math.sin(math.radians(elev))])
 cam.SetFocalPoint(*focus);cam.SetPosition(*(focus+direction*600));cam.SetParallelScale(scale);cam.SetViewUp(0,0,1)
 # Localised key light follows the studio camera; the cool rim separates dark loom.
 key.SetFocalPoint(*focus);key.SetPosition(*(focus+direction*270+[-90,55,140]));key.SetConeAngle(55 if scale>100 else 36)
 rim.SetFocalPoint(*focus);rim.SetPosition(*(focus-direction*220+[90,80,180]))
 fill.SetIntensity(.42 if 18<=t<26 else .27)
 for (g,rid),a in actors.items():
  visible=g!='LID';op=1.;shift=np.zeros(3)
  if 3<=t<10:
   visible=g in ['WIRE','CONNECTOR','SLEEVE','LIDWIRE','LIDSLEEVE','LIDCONNECTOR']
   if g in ['SLEEVE','LIDSLEEVE']:op=ramp(t,7,8);visible=visible and op>.001
   else:op=ramp(t,3,4.1);shift[2]=35*(1-op)
  if 10<=t<14:
   visible=g!='LID';q=ramp(t,10,11.4)
   if g=='HULL':shift[2]=-70*(1-q);op=q
   elif g not in ['WIRE','CONNECTOR','SLEEVE','LIDWIRE','LIDSLEEVE','LIDCONNECTOR']:op=ramp(t,11,12.1)
  if 14<=t<18:
   visible=g in ['MOTORLEFT','CORE'] or (rid in ['H04','H06b','H06c'] and g in ['WIRE','CONNECTOR','SLEEVE'])
  if 18<=t<22:
   visible=g in ['CORE','PI'] or (rid in ['H01','H08_chassis','H08_lid'] and g in ['WIRE','CONNECTOR','LIDWIRE','LIDCONNECTOR','SLEEVE','LIDSLEEVE'])
  if 22<=t<26:
   visible=g in ['CORE','PI','HUB'] or (rid in ['U01','U02','U03'] and g in ['WIRE','CONNECTOR'])
  if 26<=t<30:
   keep_cutaway=g in ['CORE','PI','STOP'] or rid in ['H08_chassis','H08_lid']
   if not keep_cutaway:op=ramp(t,27.7,28.6);visible=visible and op>.001
   q=ramp(t,26.5,27.2);rise=55*ramp(t,27.2,29)
   if g in ['LID','STOP','LIDWIRE','LIDSLEEVE','LIDCONNECTOR']:shift=[0,-8*q,rise]
   if g=='LID':visible=t>=28.5;op=.45*ramp(t,28.5,29.5)
  a.SetVisibility(visible and op>.001);a.GetProperty().SetOpacity(op);a.SetPosition(*shift)

def render_tile():
 ren.ResetCameraClippingRange();win.Render();cap.Modified();cap.Update();arr=vtk_to_numpy(cap.GetOutput().GetPointData().GetScalars())
 return Image.fromarray(np.flipud(arr.reshape(RH,RW,3)).copy()).resize((VW,VH),Image.Resampling.LANCZOS)

def label(im,point,xy,title,colour=MINT):
 ren.SetWorldPoint(*point,1);ren.WorldToDisplay();x,y,_=ren.GetDisplayPoint();end=(72+x/S,118+VH-y/S)
 d=ImageDraw.Draw(im);x,y=xy;fw=font(27,650);width=round(d.textlength(title,font=fw))+36;height=50
 d.line([(x+width/2,y+height/2),end],fill=colour,width=2);d.ellipse((end[0]-4,end[1]-4,end[0]+4,end[1]+4),fill=colour)
 d.rounded_rectangle((x,y,x+width,y+height),radius=7,fill=(20,35,44),outline=colour,width=2);d.text((x+18,y+height/2),title,font=fw,fill=WHITE,anchor='lm')

def frame(t):
 if t>=38:return family.copy()
 set_pose(t);im=Image.new('RGB',(W,H),STUDIO);d=ImageDraw.Draw(im)
 d.arc((730,-370,1190,90),3,178,fill=MINT,width=5);d.arc((-280,740,110,1130),210,410,fill=SALMON,width=5)
 d.text((76,43),'MOSS / BUILD NOTES',font=font(28,650),fill=MINT)
 d.text((76,79),'MOSS, the litter-picking rover',font=font(22,450),fill=WHITE)
 paste_logo(im,corelogo,(1548,38),300)
 tile=render_tile();im.paste(tile,(72,118));d=ImageDraw.Draw(im)
 d.line((72,846,72,990),fill=MINT,width=4)
 _,_,title,sub=next(c for c in CAPTIONS if c[0]<=t<c[1]);tf=font(52,650);sf=font(31,450)
 assert d.textlength(title,font=tf)<1740,title
 assert d.textlength(sub,font=sf)<1740,sub
 d.text((95,857),title,font=tf,fill=WHITE);d.text((98,939),sub,font=sf,fill=WHITE)
 d.text((76,1020),'CORE V0.7  /  HARNESS CONCEPT · PHYSICAL FIT STILL TO VERIFY',font=font(18,500),fill=(183,204,211))
 d.line((74,1050,1846,1050),fill=(112,138,153),width=1);d.line((74,1050,74+int(1772*t/DURATION),1050),fill=MINT,width=3)
 if 18<=t<22:
  label(im,[-73.625,.1,18.8],(210,260),'STOP · J8',MINT)
  label(im,[-55.5,43,15],(1350,264),'BATTERY · XT30',SALMON)
 if 22<=t<26:
  label(im,[-31.2,78.5,37],(1260,218),'USB HUB',MINT)
 if 26<=t<27.6:
  label(im,[18,74,58],(1300,232),'LID CONNECTOR',MINT)
 if 30<=t<35:
  paste_logo(im,pcbway,(117,153),280)
 return im

times=[1.3,5,8.7,12.8,16,20,24,27,29.6,32,36,40]
if args.stills or args.test:
 t0=time.time();sheet=Image.new('RGB',(1280,6*360),STUDIO)
 for i,t in enumerate(times if args.stills else [1.3,16,20,24]):
  im=frame(t);im.save(O/f'REVIEW_{t:04.1f}.jpg',quality=95);thumb=im.resize((640,360),Image.Resampling.LANCZOS);sheet.paste(thumb,((i%2)*640,(i//2)*360));print('frame',t,round(time.time()-t0,2),flush=True)
 sheet.save(O/'STORYBOARD.jpg',quality=94);win.Finalize();raise SystemExit

output=O/'MOSS_Harness_Story.mp4';partial=O/'MOSS_Harness_Story.partial.mp4'
cmd=[FFMPEG,'-v','warning','-nostdin','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(O/'AUDIO_MIX.wav'),'-map','0:v','-map','1:a','-t',str(DURATION),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2','-c:a','aac','-b:a','192k','-movflags','+faststart',str(partial)]
t0=time.time()
with (O/'RENDER.log').open('wb') as log:
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
 try:
  for i in range(FPS*DURATION):
   p.stdin.write(frame(i/FPS).tobytes())
   if i%(FPS*2)==0:print(f'{i//FPS}/{DURATION}s rendered; elapsed {time.time()-t0:.1f}s',flush=True)
  p.stdin.close();assert p.wait(timeout=60)==0
 finally:
  if p.poll() is None:p.terminate()
  win.Finalize()
os.replace(partial,output)
(O/'RENDER_QA.json').write_text(json.dumps({'duration_s':DURATION,'fps':FPS,'size':[W,H],'supersampling':S,'lighting':'Localised warm studio key + cool rim + soft fill; FXAA + Lanczos.','camera':'True 3D camera movement; stationary camera for STOP/battery callouts; labels projected from model coordinates.','captions':CAPTIONS,'elapsed_s':time.time()-t0,'frames':FPS*DURATION},indent=2)+'\n')
print(output,flush=True)
