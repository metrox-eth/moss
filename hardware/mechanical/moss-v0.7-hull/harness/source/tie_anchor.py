"""Small integral cable-tie bridge, millimetres, CadQuery 2.x.

Local X follows the harness. A 2.5 mm tie is threaded in local Y through
the 4.0 mm wide by 2.4 mm high passage, then wraps over the harness.
``z`` is the highest sampled floor point, not the anchor underside.
The 0.6 mm buried slab must be fused into the existing solid hull.
This is prototype geometry; printer fit and tie insertion need a coupon.
"""
from __future__ import annotations

import math
import cadquery as cq
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

FOOTPRINT_X = 10.0
FOOTPRINT_Y = 6.0
PASSAGE_WIDTH = 4.0
PASSAGE_HEIGHT = 2.4
ROOF_THICKNESS = 1.8
EMBED_DEPTH = 0.6
OUTER_CORNER_RADIUS = 0.6


def bridge_anchor() -> cq.Shape:
    """Return one printable bridge with a sub-floor joining slab.

    The short 4 mm roof span is a bridge; the aperture remains rectangular.
    Rounding only exterior vertical edges preserves the full opening.
    """
    h = EMBED_DEPTH + PASSAGE_HEIGHT + ROOF_THICKNESS
    body = (
        cq.Workplane("XY")
        .box(FOOTPRINT_X, FOOTPRINT_Y, h, centered=(True, True, False))
        .translate((0, 0, -EMBED_DEPTH))
        .edges("|Z").fillet(OUTER_CORNER_RADIUS)
    )
    aperture = cq.Workplane("XY").box(
        PASSAGE_WIDTH, FOOTPRINT_Y + 2, PASSAGE_HEIGHT,
        centered=(True, True, False),
    )
    result = body.cut(aperture).val()
    assert result.isValid() and len(result.Solids()) == 1
    return result


def place_at(x: float, y: float, z: float, angle: float = 0) -> cq.Shape:
    """Place at floor datum z; angle is degrees counterclockwise from +X.

    The XY plane is retained: callers must inspect the entire 10 x 6 mm
    footprint on the actual hull and fuse with positive overlap. For a
    curved floor use ``floor_datum`` and inspect its reported height range.
    """
    return bridge_anchor().rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, z))


def surface_hits(hull: cq.Shape, x: float, y: float) -> list[float]:
    intersector = IntCurvesFace_ShapeIntersector()
    intersector.Load(hull.wrapped, 1e-7)
    intersector.Perform(gp_Lin(gp_Pnt(x, y, -10), gp_Dir(0, 0, 1)), 0, 110)
    hits = sorted(intersector.Pnt(i).Z() for i in range(1, intersector.NbPnt() + 1))
    unique = []
    for z in hits:
        if not unique or abs(z - unique[-1]) > 1e-5:
            unique.append(z)
    return unique


def floor_datum(hull: cq.Shape, x: float, y: float, angle: float = 0) -> dict:
    """Sample a 5 x 5 footprint grid and return conservative local floor Z.

    Sampling is only a placement screen, not a geometric proof. The
    caller must check anchor/hull intersection and a single-solid union.
    A footprint crossing a tall rib/lug or an absent floor is rejected.
    """
    a = math.radians(angle)
    values = []
    for dx in (-5, -2.5, 0, 2.5, 5):
        for dy in (-3, -1.5, 0, 1.5, 3):
            px, py = x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a)
            hits = surface_hits(hull, px, py)
            if len(hits) < 2 or hits[0] < -1e-4 or not (1.5 < hits[1] < 12):
                raise ValueError(f"No low floor at {(px, py)}: {hits}")
            values.append(hits[1])
    lo, hi = min(values), max(values)
    if hi - lo > EMBED_DEPTH - 0.15:
        raise ValueError(f"Floor variation {hi-lo:.4f} exceeds joining allowance")
    return {
        "x_mm": x, "y_mm": y, "angle_deg": angle,
        "floor_min_mm": lo, "floor_max_mm": hi,
        "datum_z_mm": hi + 0.01,
        "floor_variation_mm": hi-lo,
        "minimum_sampled_embed_mm": EMBED_DEPTH - (hi-lo) - 0.01,
        "sample_count": len(values),
    }
