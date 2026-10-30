"""Editable conceptual STEP conduits, exact cubic-Hermite centreline conversion.

No contact, braid, connector fit, validated bend radius or fabrication claim.
The displayed full-length cylinders represent the chosen route envelopes.
"""
from pathlib import Path
import hashlib
import json
import shutil
import time
import numpy as np
from scipy.interpolate import CubicHermiteSpline
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_AbscissaPoint

def curve_length(shape):
    return sum(GCPnts_AbscissaPoint.Length_s(BRepAdaptor_Curve(e.wrapped),1e-7) for e in shape.Edges())

P=Path(__file__).resolve().parents[1]
O=P/'output'
A=P/'assets'
SOURCE=O/'ROUTE_LENGTHS.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hermite_geometry(points):
    """Same recipe as build_harness.curve; convert each interval to Bezier."""
    p=np.array(points,float)
    d=np.linalg.norm(np.diff(p,axis=0),axis=1)
    p=p[np.r_[True,d>0.01]]
    d=np.linalg.norm(np.diff(p,axis=0),axis=1)
    t=np.r_[0,np.cumsum(d)]
    der=np.zeros_like(p)
    der[0]=(p[1]-p[0])/d[0]
    der[-1]=(p[-1]-p[-2])/d[-1]
    for i in range(1,len(p)-1):
        der[i]=.78*((p[i]-p[i-1])/d[i-1]+(p[i+1]-p[i])/d[i])/2
    f=CubicHermiteSpline(t,p,der,axis=0)
    tt=np.unique(np.r_[np.linspace(0,t[-1],max(12,int(t[-1]/.9)+1)),t])
    edges=[]
    for i,dt in enumerate(d):
        poles=[p[i],p[i]+der[i]*dt/3,p[i+1]-der[i+1]*dt/3,p[i+1]]
        edges.append(cq.Edge.makeBezier([cq.Vector(*q) for q in poles]))
    return cq.Wire.assembleEdges(edges),p,der,f(tt)


def main():
    started=time.time()
    source_hash=sha(SOURCE)
    routes=json.loads(SOURCE.read_text())['routes']
    assert len(routes)==20
    center_assembly=cq.Assembly(name='MOSS_HARNESS_CENTRELINES_CONCEPT_MM')
    envelope_assembly=cq.Assembly(name='MOSS_HARNESS_OUTER_ROUTE_ENVELOPES_CONCEPT_MM')
    report={
        'status':'EDITABLE_CONCEPT_CAD_NOT_FABRICATION_OR_COLLISION_RELEASE',
        'units':'mm','source':str(SOURCE),'source_sha256':source_hash,
        'method':'Exact piecewise cubic Bezier conversion of the build_harness.py cubic Hermite recipe; same control points and derivatives. Rounded recorded samples verified against reconstructed Hermite samples.',
        'envelope_definition':'Full-length circular outer route reservations: sleeve_outer_diameter_mm when sleeve=true, otherwise wire_od_mm. These are not literal braid, contacts or individual conductors.',
        'fallback':'If one sweep fails or yields invalid geometry, preserve its named centreline wire in the routing assembly. No changed route or reduced radius is substituted.',
        'routes':[],
    }
    for route in routes:
        wire,p,der,recreated=hermite_geometry(route['control_points_mm'])
        recorded=np.asarray(route['points_mm'],float)
        assert recorded.shape==recreated.shape,(route['id'],recorded.shape,recreated.shape)
        reconstruction_error=float(np.linalg.norm(recorded-recreated,axis=1).max())
        assert reconstruction_error<.0001,(route['id'],reconstruction_error)
        assert wire.isValid()
        center_assembly.add(wire,name=route['id'],color=cq.Color(.92,.55,.14))
        sampled_length=float(np.linalg.norm(np.diff(recorded,axis=0),axis=1).sum())
        step_length=curve_length(wire)
        diameter=route['sleeve_outer_diameter_mm'] if route['sleeve'] else route['wire_od_mm']
        info={
            'id':route['id'],'label':route['label'],
            'curve_type':'Exact piecewise cubic Bezier (same cubic Hermite curve)',
            'curve_segments':len(wire.Edges()),'wire_valid':wire.isValid(),
            'step_curve_length_mm':step_length,
            'sampled_polyline_length_mm':sampled_length,
            'recorded_rounded_length_mm':route['centreline_mm'],
            'difference_vs_sampled_polyline_mm':step_length-sampled_length,
            'difference_vs_recorded_rounded_mm':step_length-route['centreline_mm'],
            'max_sample_reconstruction_error_mm':reconstruction_error,
            'envelope_diameter_mm':diameter,
            'diameter_source':'sleeve_outer_diameter_mm' if route['sleeve'] else 'wire_od_mm',
            'start_mm':p[0].tolist(),'end_mm':p[-1].tolist(),
        }
        try:
            plane=cq.Plane(origin=tuple(p[0]),normal=tuple(der[0]))
            swept=cq.Workplane(plane).circle(diameter/2).sweep(wire,isFrenet=False,transition='round',clean=False).val()
            if not swept.isValid() or len(swept.Solids())!=1:
                raise ValueError(f'Invalid envelope or solid count {len(swept.Solids())}')
            envelope_assembly.add(swept,name=route['id'],color=cq.Color(.20,.25,.28))
            info.update({'envelope_status':'VALID_SINGLE_SOLID','solid_count':1,'volume_mm3':swept.Volume()})
        except Exception as exc:
            envelope_assembly.add(wire,name=route['id']+'_CENTRELINE_ONLY_SWEEP_FAILED',color=cq.Color(1,.3,.05))
            info.update({'envelope_status':'CENTRELINE_ONLY_SWEEP_FAILED','sweep_error':str(exc)})
        report['routes'].append(info)
        print(route['id'],info['envelope_status'],round(step_length,4),round(step_length-sampled_length,5),flush=True)
    center_path=O/'MOSS_HARNESS_CENTRELINES.step'
    envelope_path=O/'MOSS_HARNESS_ROUTING.step'
    center_assembly.save(str(center_path),'STEP')
    envelope_assembly.save(str(envelope_path),'STEP')
    center_reimport=cq.importers.importStep(str(center_path)).val()
    envelope_reimport=cq.importers.importStep(str(envelope_path)).val()
    report['route_count']=len(routes)
    report['successful_sweeps']=sum(r['envelope_status']=='VALID_SINGLE_SOLID' for r in report['routes'])
    report['failed_sweep_ids']=[r['id'] for r in report['routes'] if r['envelope_status']!='VALID_SINGLE_SOLID']
    report['roundtrip']={
        'centerline_edge_count':len(center_reimport.Edges()),
        'expected_centerline_edge_count':sum(r['curve_segments'] for r in report['routes']),
        'centerline_route_names_preserved':all(("PRODUCT('"+r['id']+"'") in center_path.read_text() for r in routes),
        'routing_route_names_preserved':all(("PRODUCT('"+r['id']+"'") in envelope_path.read_text() for r in routes),
        'total_reimported_centerline_length_mm':curve_length(center_reimport),
        'total_original_curve_length_mm':sum(r['step_curve_length_mm'] for r in report['routes']),
        'routing_solid_count':len(envelope_reimport.Solids()),
        'routing_all_solids_valid':all(s.isValid() for s in envelope_reimport.Solids()),
    }
    assert report['roundtrip']['centerline_edge_count']==report['roundtrip']['expected_centerline_edge_count']
    assert report['roundtrip']['routing_solid_count']==report['successful_sweeps']
    assert report['roundtrip']['routing_all_solids_valid']
    assert report['roundtrip']['centerline_route_names_preserved'] and report['roundtrip']['routing_route_names_preserved']
    # Use the same 1e-7 mm quadrature tolerance for both curve wrappers.
    assert abs(report['roundtrip']['total_reimported_centerline_length_mm']-report['roundtrip']['total_original_curve_length_mm'])<.00001
    copies=[
        'Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.step',
        'Hull_MOSS_V07_Harness_Tie_Loops_PROTOTYPE.stl',
        'tie_anchor_fit_coupon.step','tie_anchor_fit_coupon.stl',
        'tie_anchor_fit_coupon.png','hull_tie_variant_QA.json',
    ]
    report['copied_verified_hull_and_coupon']=[]
    for name in copies:
        shutil.copy2(P/'cad'/name,O/name)
        assert sha(P/'cad'/name)==sha(O/name)
        report['copied_verified_hull_and_coupon'].append(name)
    report['outputs']={path.name:{'sha256':sha(path),'bytes':path.stat().st_size} for path in [center_path,envelope_path]}
    report['source_unchanged']=sha(SOURCE)==source_hash
    report['elapsed_seconds']=time.time()-started
    (O/'HARNESS_STEP_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='routes'},indent=2),flush=True)


if __name__=='__main__':
    main()
