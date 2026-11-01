"""Native rear support rebuild: same Cytron pitch/seat, centered on rear Y=0.

The two fixed motor axes and fan clearances determine the underside relief.
All coordinates below are millimetres in the R92 world frame.
"""
import adsk.core, adsk.fusion

def build_centered_cytron(tm, cfg):
    union=adsk.fusion.BooleanTypes.UnionBooleanType
    diff=adsk.fusion.BooleanTypes.DifferenceBooleanType
    inter=adsk.fusion.BooleanTypes.IntersectionBooleanType
    def p(x,y,z):return adsk.core.Point3D.create(x/10,y/10,z/10)
    def box(lo,hi):
        return tm.createBox(adsk.core.OrientedBoundingBox3D.create(
            p(*[(a+b)/2 for a,b in zip(lo,hi)]),adsk.core.Vector3D.create(1,0,0),
            adsk.core.Vector3D.create(0,1,0),*[(b-a)/10 for a,b in zip(lo,hi)]))
    def op(target,tool,kind):
        assert tm.booleanOperation(target,tool,kind)
        return target
    def cylinder(x,y,z0,z1,r):return tm.createCylinderOrCone(p(x,y,z0),r/10,p(x,y,z1),r/10)
    def rounded(x0,x1,y0,y1,z0,z1,r):
        b=box([x0+r,y0,z0],[x1-r,y1,z1])
        op(b,box([x0,y0+r,z0],[x1,y1-r,z1]),union)
        for x in [x0+r,x1-r]:
            for y in [y0+r,y1-r]:op(b,cylinder(x,y,z0,z1,r),union)
        return b
    frame=rounded(-155.94,-92.06,-43.37,43.37,39.5,45,4)
    op(frame,rounded(-147.94,-100.06,-35.37,35.37,39.49,45.01,4),diff)
    x,z=cfg['motor_axis_xz_mm'];radius=cfg['motor_relief_radius_mm']
    op(frame,tm.createCylinderOrCone(p(x,-50,z),radius/10,p(x,50,z),radius/10),diff)
    # Raise the rear rail underside above both 3010 fans (top Z40.75).
    op(frame,box([-160,-44,39.49],[-147.939,44,41.05]),diff)
    # Rear-wall attachment remains between the fans and away from their clips.
    op(frame,box([-159.01,-26.5,41.05],[-155.93,26.5,45]),union)
    for y in cfg['rear_gusset_y_mm']:
        top=41.05;depth=8.5
        gusset=box([-159.01,y-3,top-depth-.01],[-159+depth,y+3,top+.01])
        n=adsk.core.Vector3D.create(-1,0,1);n.normalize()
        half=tm.createBox(adsk.core.OrientedBoundingBox3D.create(
            p(-159+n.x*50,y,top-depth+n.z*50),n,
            adsk.core.Vector3D.create(0,1,0),10,10,10))
        op(gusset,half,inter);op(frame,gusset,union)
    for x in [-151.94,-96.06]:
        for y in [-39.37,39.37]:
            op(frame,cylinder(x,y,44.9,47.4,3.5),union)
            op(frame,cylinder(x,y,41.9,47.5,1.35),diff)
    assert frame.isSolid and frame.lumps.count==1
    return frame
