"""Fusion API entry point: mesh the checked STEP with Fusion's native exporter."""
from pathlib import Path
import json
import hashlib
import adsk.core
import adsk.fusion

BASE=globals().get('MOSS_MECHANICAL_ROOT')
if not BASE:BASE=str(Path(__file__).resolve().parents[1])


def run(context):
    root=Path(BASE)
    source=root/'cad/Hull_MOSS_V07_Core_Stack.step'
    app=adsk.core.Application.get()
    options=app.importManager.createSTEPImportOptions(str(source))
    doc=app.importManager.importToNewDocument(options)
    assert doc
    doc.name='MOSS V0.7 - Core 74x71 - checked STEP native print export'
    design=adsk.fusion.Design.cast(app.activeProduct)
    bodies=[b for b in design.rootComponent.bRepBodies if b.isSolid]
    assert len(bodies)==1,len(bodies)
    body=bodies[0]
    b=body.boundingBox
    assert abs((b.maxPoint.x-b.minPoint.x)*10-328)<.01
    manager=design.exportManager
    stl=root/'stl/Hull_MOSS_V07_NATIVE_MATCHED.stl'
    mesh=manager.createSTLExportOptions(body,str(stl))
    mesh.unitType=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    mesh.isBinaryFormat=True
    mesh.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    assert manager.execute(mesh)
    f3d=root/'cad/Hull_MOSS_V07_Core_74x71_EDITABLE.f3d'
    assert manager.execute(manager.createFusionArchiveExportOptions(str(f3d)))
    report={'operation':'Import the independently checked STEP, export STL with native Fusion mesh engine. No geometry edit.',
            'source_step_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'solid_count':len(bodies),'native_volume_mm3':body.volume*1000,
            'f3d_scope':'Editable imported BRep; no reconstructed parametric history claimed.',
            'artifacts':{str(p.relative_to(root)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [stl,f3d]}}
    (root/'evidence/FUSION_NATIVE_PRINT_EXPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    doc.close(False)
