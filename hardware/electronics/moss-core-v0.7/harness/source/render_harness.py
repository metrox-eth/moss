from pathlib import Path
import json, math, argparse
import numpy as np, vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];R=P.parent;O=P/'output'
ap=argparse.ArgumentParser();ap.add_argument('--video',action='store_true');args=ap.parse_args()
W,H=1920,1280;S=1.5;RW,RH=int(W*S),int(H*S)
ren=vtk.vtkRenderer();ren.SetBackground(.88,.89,.87);ren.SetBackground2(.98,.98,.96);ren.GradientBackgroundOn();ren.SetUseFXAA(True)
win=vtk.vtkRenderWindow();win.SetSize(RW,RH);win.SetOffScreenRendering(1);win.SetMultiSamples(0);win.AddRenderer(ren)
ren.AutomaticLightCreationOff()
for pos,power in [((-220,-180,450),.85),((100,180,300),.6),((-250,200,180),.35)]:
 l=vtk.vtkLight();l.SetPosition(*pos);l.SetFocalPoint(0,0,30);l.SetIntensity(power);ren.AddLight(l)
actors={};keep=[];z=np.load(P/'assets/HARNESS_SCENE.npz')
for key in z.files:
 if not key.endswith('_vertices'):continue
 n=key[:-9];v=z[key];f=z[n+'_faces'].astype(np.int64)
 pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(v,deep=True));cells=vtk.vtkCellArray();cells.SetData(numpy_to_vtkIdTypeArray(np.arange(len(f)+1,dtype=np.int64)*3,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True));poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
 colors=z[n+'_facecolors'] if n+'_facecolors' in z else np.broadcast_to(z[n+'_color'],(len(f),3))
 scal=numpy_to_vtk((colors*255).clip(0,255).astype(np.uint8),deep=True);poly.GetCellData().SetScalars(scal)
 normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(45);normals.SplittingOn()
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());mapper.SetScalarModeToUseCellData();mapper.ScalarVisibilityOn()
 actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetAmbient(.30);actor.GetProperty().SetDiffuse(.72);actor.GetProperty().SetSpecular(.20);actor.GetProperty().SetSpecularPower(30);actor.GetProperty().SetInterpolationToPhong();ren.AddActor(actor);actors[n]=actor
 keep.extend([pts,cells,poly,scal,normals,mapper,actor])
cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,0,1)
cap=vtk.vtkWindowToImageFilter();cap.SetInput(win);cap.SetInputBufferTypeToRGB();cap.ReadFrontBufferOff()
fontpath=P/'assets/branding/SpaceGrotesk.ttf'
def font(size,weight=500):
 f=ImageFont.truetype(str(fontpath),size)
 try:f.set_variation_by_axes([weight])
 except:pass
 return f
def capture():
 ren.ResetCameraClippingRange();win.Render();cap.Modified();cap.Update();arr=vtk_to_numpy(cap.GetOutput().GetPointData().GetScalars());return Image.fromarray(np.flipud(arr.reshape(RH,RW,3)).copy()).resize((W,H),Image.Resampling.LANCZOS)
def view(mode='installed',angle=-126):
 for n,a in actors.items():
  group=n.split('__')[0];visible=True;a.SetPosition(0,0,0);a.GetProperty().SetOpacity(1)
  if group=='LID':visible=mode=='lid'
  if mode=='loom':visible=group in ['WIRE','SLEEVE','CONNECTOR','MOUNT','TIE','LIDWIRE','LIDCONNECTOR']
  if mode=='lid' and group in ['LID','STOP','LIDWIRE','LIDCONNECTOR']:a.SetPosition(0,0,100)
  if mode=='lid' and group=='LID':a.GetProperty().SetOpacity(.25)
  if mode in ['detail','motor','plugs']:visible=not group=='LID'
  if mode=='motor' and (group in ['HULL','PI'] or 'Cytron' in n):visible=False
  a.SetVisibility(visible)
 if mode=='top':
  cam.SetPosition(-8,0,600);cam.SetFocalPoint(-8,0,0);cam.SetViewUp(0,1,0);cam.SetParallelScale(180)
 elif mode=='motor':
  cam.SetPosition(-70,-78,61);cam.SetFocalPoint(-106,7,23);cam.SetViewUp(0,0,1);cam.SetParallelScale(23)
 elif mode=='plugs':
  cam.SetPosition(-72,85,75);cam.SetFocalPoint(-35,33,17);cam.SetViewUp(0,0,1);cam.SetParallelScale(45)
 elif mode=='detail':
  cam.SetPosition(-45,-150,180);cam.SetFocalPoint(-17,-42,16);cam.SetViewUp(0,0,1);cam.SetParallelScale(57)
 else:
  focus=np.array([-10,0,75 if mode=='lid' else 33]);a=math.radians(angle);e=math.radians(52)
  cam.SetFocalPoint(*focus);cam.SetPosition(*(focus+np.array([math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)])*650));cam.SetViewUp(0,0,1);cam.SetParallelScale(232 if mode=='lid' else 185 if mode=='loom' else 205)
def labeled(im,title,subtitle,mode):
 d=ImageDraw.Draw(im);d.rectangle((0,0,W,142),fill='#142b33');d.text((54,25),'MOSS / '+title,font=font(44,700),fill='#f6f7f4');d.text((56,86),subtitle,font=font(23),fill='#bad2d3')
 d.rounded_rectangle((W-285,35,W-52,78),radius=9,fill='#b8944d');d.text((W-265,44),'ROUTING STUDY',font=font(21,700),fill='#142b33')
 d.rectangle((0,H-88,W,H),fill='#142b33');d.text((54,H-65),'CORE V0.7  /  Removable sleeves  /  Printed tie loops  /  Quick-release lid',font=font(24),fill='#f6f7f4');d.text((55,H-31),'Dimensioned visual study. Motor connector vendor/pinout, cable lengths and fit still require physical validation.',font=font(18),fill='#b4c8ce')
 return im
for filename,mode,title,sub in [
 ('01_HARNESS_INSTALLED.png','installed','Harness integration','Grouped runs, accessible branches and a detachable lid.'),
 ('02_HARNESS_ISOLATED.png','loom','Follow the wiring','Power, controls and sensors formed into a serviceable cable kit.'),
 ('03_HARNESS_TOP.png','top','Designed around the hardware','Five integrated tie loops hold the main routing corridors.'),
 ('04_LID_DISCONNECT.png','lid','Lift. Unplug. Remove.','The STOP button stays with the lid. Its connector is within reach.'),
 ('06_MOTOR_CONNECTOR.png','motor','One motor. One six-wire plug.','Four encoder wires and two motor wires meet at the same connector.'),
 ('07_CORE_CONNECTORS.png','plugs','Mating housings at the right scale','Public catalogue dimensions, positioned on the current board model.'),
 ('05_HARNESS_DETAIL.png','detail','Sleeves and printed tie loops','Openable sleeving protects shared runs. Connector ends remain accessible.')]:
 view(mode);im=labeled(capture(),title,sub,mode);im.save(O/filename);print(filename,flush=True)
win.Finalize()
