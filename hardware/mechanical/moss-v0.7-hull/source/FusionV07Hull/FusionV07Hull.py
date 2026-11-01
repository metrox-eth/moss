import adsk.core, adsk.fusion, json, traceback, os
from pathlib import Path
BASE=globals().get('MOSS_MECHANICAL_ROOT')
if not BASE: BASE=str(Path(__file__).resolve().parents[2])
CFG=json.loads((Path(BASE)/'source/mechanical_parameters.json').read_text())
SRC=str(Path(BASE)/CFG['source_native_smt'])
def run(context):
 try:
  app=adsk.core.Application.get()
  if app.activeDocument and app.activeDocument.name.startswith('MOSS 0.7 - Core mounting 74x71 - LOCAL PROTOTYPE'):app.activeDocument.close(False)
  doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MOSS 0.7 - Core mounting 74x71 - LOCAL PROTOTYPE'
  d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.DirectDesignType;root=d.rootComponent;tm=adsk.fusion.TemporaryBRepManager.get()
  bodies=tm.createFromFile(SRC);assert bodies and len(bodies)==1
  hull=tm.copy(bodies[0]);bb=hull.boundingBox
  trans=adsk.core.Matrix3D.create();trans.translation=adsk.core.Vector3D.create(*[a/10-b for a,b in zip(CFG['hull_min_corner_mm'],[bb.minPoint.x,bb.minPoint.y,bb.minPoint.z])]);assert tm.transform(hull,trans)
  original=tm.copy(hull);assert hull.isSolid and hull.lumps.count==1
  # Remove complete obsolete mounts, healing the native floor/rib surfaces.
  # This runs before new mounts are added so overlapping INA feet cannot affect them.
  cleanup_body=root.bRepBodies.add(hull);removal_log=[]
  for group in CFG['obsolete_mount_face_removals']:
   faces=adsk.core.ObjectCollection.create()
   for face in cleanup_body.faces:
    bb=face.boundingBox;lo=[bb.minPoint.x*10,bb.minPoint.y*10,bb.minPoint.z*10];hi=[bb.maxPoint.x*10,bb.maxPoint.y*10,bb.maxPoint.z*10]
    boxes=group.get('boxes',[[group['min'],group['max']]])
    if not any(all(lo[i]>=low[i] and hi[i]<=high[i] for i in range(3)) for low,high in boxes):continue
    if group.get('preserve_rear_wall_microfaces') and hi[0]<-158.5 and face.area*100<2:continue
    if group.get('preserve_rear_wall_planes') and abs(hi[0]-lo[0])<.00001 and abs(lo[0]+159)<.00001:continue
    faces.add(face)
   count=faces.count;assert count>0,group['name'];before=cleanup_body.volume*1000
   root.features.deleteFaceFeatures.add(faces)
   assert cleanup_body.isSolid and cleanup_body.lumps.count==1
   delta=before-cleanup_body.volume*1000;assert delta>.1,group['name']
   removal_log.append(dict(group,face_count=count,removed_volume_mm3=delta))
  hull=tm.copy(cleanup_body);cleanup_body.deleteMe()
  def p(x,y,z):return adsk.core.Point3D.create(x/10,y/10,z/10)
  def box(lo,hi):
   return tm.createBox(adsk.core.OrientedBoundingBox3D.create(p(*[(a+b)/2 for a,b in zip(lo,hi)]),adsk.core.Vector3D.create(1,0,0),adsk.core.Vector3D.create(0,1,0),*[(b-a)/10 for a,b in zip(lo,hi)]))
  def cyl(x,y,z,r,h):return tm.createCylinderOrCone(p(x,y,z),r/10,p(x,y,z+h),r/10)
  def op(tool,kind):
   assert tm.booleanOperation(hull,tool,kind);assert hull.isSolid and hull.lumps.count==1
  diff=adsk.fusion.BooleanTypes.DifferenceBooleanType;un=adsk.fusion.BooleanTypes.UnionBooleanType
  # Keep the original native material in the documented fan-clip regions.
  # The old Cytron bridge overlaps the negative clip reservation; retain that
  # local attachment while removing the larger obsolete frame around it.
  for region in CFG['cytron_recenter']['protected_native_fan_clip_regions_mm']:
   keep=tm.copy(original);assert tm.booleanOperation(keep,box(*region),adsk.fusion.BooleanTypes.IntersectionBooleanType)
   op(keep,un)
  helper={};exec((Path(BASE)/'source/centered_cytron_support.py').read_text(),helper)
  op(helper['build_centered_cytron'](tm,CFG['cytron_recenter']),un)
  pts=CFG['core_mount_xy']+CFG['hub_screw_xy']+CFG['hub_rear_support_xy'];boss=CFG['boss']
  for x,y in pts:
   op(tm.createCylinderOrCone(p(x,y,boss['bottom_z']),boss['foot_radius']/10,p(x,y,boss['post_start_z']),boss['post_radius']/10),un);op(cyl(x,y,boss['post_start_z'],boss['post_radius'],boss['top_z']-boss['post_start_z']),un)
  for x,y in CFG['core_mount_xy']+CFG['hub_screw_xy']:op(cyl(x,y,boss['pilot_bottom_z'],boss['pilot_radius'],boss['pilot_height']),diff)
  body=root.bRepBodies.add(hull);body.name='Hull V0.7 - Core 74x71 mounting - Hoco support preserved'
  appearance=d.appearances.addByCopy(body.appearance,'MOSS black hull')
  for key in ['metal_f0','surface_albedo']:
   prop=adsk.core.ColorProperty.cast(appearance.appearanceProperties.itemById(key))
   if prop:prop.value=adsk.core.Color.create(14,16,18,255)
  body.appearance=appearance
  added=tm.copy(hull);assert tm.booleanOperation(added,tm.copy(original),diff)
  removed=tm.copy(original);assert tm.booleanOperation(removed,tm.copy(hull),diff)
  def info(b):
   bb=b.boundingBox;return {'volume_mm3':b.volume*1000,'solid':b.isSolid,'lumps':b.lumps.count,'bounds_mm':[[v.x*10,v.y*10,v.z*10] for v in [bb.minPoint,bb.maxPoint]]}
  evidence={'source':SRC,'native_source_transform_cm':trans.asArray(),'original':info(original),'result':info(body),'added':info(added),'removed':info(removed),'legacy_mount_removals':removal_log,'cytron_recenter':CFG['cytron_recenter'],'operations':'Remove obsolete Jetson-caddy, Waveshare/servo, INA219 and ESP32 supports. Center the Cytron frame by Y+27mm with unchanged Z47.4 seating and 55.88x78.74mm pitch; preserve motor/fan clearance with two rounded motor reliefs and rear gussets between fans. Core floor boss pattern updated to 74x71 mm at unchanged Z10 seating. Preserve hub mounts, motor and battery interfaces. No global remesh.','status':'Native Fusion mechanical prototype; no physical fit test'}
  for changed in [added,removed]:
   bb=changed.boundingBox
   assert all(v>=lo/10-1e-8 for v,lo in zip([bb.minPoint.x,bb.minPoint.y,bb.minPoint.z],CFG['allowed_edit_region']['min']))
   assert all(v<=hi/10+1e-8 for v,hi in zip([bb.maxPoint.x,bb.maxPoint.y,bb.maxPoint.z],CFG['allowed_edit_region']['max']))
  os.makedirs(BASE+'/cad',exist_ok=True);os.makedirs(BASE+'/stl',exist_ok=True)
  ex=d.exportManager
  assert ex.execute(ex.createSTEPExportOptions(BASE+'/cad/Hull_MOSS_V07_NATIVE_MATCHED.step',root))
  stl=ex.createSTLExportOptions(body,BASE+'/stl/Hull_MOSS_V07_NATIVE_MATCHED.stl');stl.unitType=adsk.fusion.DistanceUnits.MillimeterDistanceUnits;stl.isBinaryFormat=True;stl.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert ex.execute(stl)
  assert ex.execute(ex.createFusionArchiveExportOptions(BASE+'/cad/Hull_MOSS_V07_NATIVE_MATCHED.f3d'))
  assert tm.exportToFile([body],BASE+'/cad/Hull_MOSS_V07_NATIVE_MATCHED.smt')
  open(BASE+'/evidence/FUSION_NATIVE_BUILD.json','w').write(json.dumps(evidence,indent=2))
  cam=app.activeViewport.camera;cam.eye=p(-330,-460,440);cam.target=p(-10,0,20);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;cam.isSmoothTransition=False;app.activeViewport.camera=cam
  app.activeViewport.refresh();app.activeViewport.saveAsImageFile(BASE+'/MOSS_V07_NATIVE_HULL.png',1400,1000)
 except:
  open(BASE+'/evidence/FUSION_NATIVE_ERROR.txt','w').write(traceback.format_exc())
  raise
