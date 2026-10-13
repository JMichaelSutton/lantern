"""Cut the lantern bail handle into flat-printing sections with alignment pins.

The handle lies in the XY plane and is symmetric about z=0. It is split
lengthwise at z=0 so every piece prints flat face down, with layer lines along
the handle (its strongest direction). Each half is then cut radially into three
sections that fit a 220 x 215 mm bed. The cuts in the two halves are staggered
like brickwork, so no joint goes all the way through the handle.

Decorative inset grooves are cut where the CAD faces meet: arc to bend, and
bend to end barrel.

Usage: python3 tools/split_handle.py [input.stl] [output_dir]
Requires: trimesh, manifold3d, numpy, scipy
"""

import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "models/handle/new-handle.stl"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "models/handle/print"

BED = (220, 215)
BED_MARGIN = 4  # per side

# Radial cut angles (degrees, CCW from +X) for each half. The 18 degree offset
# between halves puts ~52 mm of the other half across every joint.
CUTS = {"upper": (31, 131), "lower": (49, 149)}

# Tube centerline is a circle about the origin from -45 to 225 degrees. Pins sit
# at least 5 degrees (~14 mm) from any cut so no hole is split.
ARC_RADIUS = 166.65
PIN_ANGLES = [-30, 10, 36, 44, 70, 90, 110, 136, 144, 170, 210]
BARREL_PINS = [(-82.6, -126.5), (82.2, -126.5)]  # mid-barrel

# CAD face boundaries, measured from the source mesh's tessellation.
ARC_END_ANGLES = (-45, 225)  # arc meets the elbow
BARREL_START_X = (-98, 98)   # elbow meets the straight end barrel
GROOVE_WIDTH = 0.8
GROOVE_DEPTH = 0.5

PIN_D = 4.0          # printed pin diameter
HOLE_D = 4.4         # hole diameter (0.2 mm radial clearance)
HOLE_DEPTH = 5.5     # per half; tube half-height is 8.33, leaving ~2.8 mm above
PIN_GAP = 0.5        # pin is this much shorter than the two holes combined
MOUTH_CHAMFER = 0.5  # cone at the hole mouth to absorb elephant's foot
PIN_FLAT = 0.4       # flat shaved off the pin so it prints lying down
SPARE_PINS = 2
SEGMENTS = 64


def to_manifold(mesh):
    return mf.Manifold(mf.Mesh(
        vert_properties=np.asarray(mesh.vertices, np.float32),
        tri_verts=np.asarray(mesh.faces, np.uint32),
    ))


def to_trimesh(manifold):
    m = manifold.to_mesh()
    # process=False: manifold output is already clean, and trimesh's vertex
    # merging can weld near-coincident vertices and break the topology.
    return trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts, process=False)


def load_solid(path):
    """The source STL holds four bodies: the watertight handle shell, an open
    duplicate of the tube surface lying within ~1 um of it, and two end
    cylinders that only add sharp rims where the shell's barrels are rounded.
    Unioning near-coincident surfaces leaves sliver triangles that slicers
    report as errors, so keep only the shell, which is the largest closed body."""
    bodies = trimesh.load(path).split(only_watertight=True)
    return to_manifold(max(bodies, key=lambda b: b.volume))


def frame(origin, normal):
    """Transform taking world coords to a frame where the plane is z=0."""
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    x = np.cross([0, 0, 1], n) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    rot = np.array([x, y, n])
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = -rot @ np.asarray(origin, float)
    return m


def transform(shape, m):
    return shape.transform(np.asarray(m[:3, :], np.float64))


def groove(solid, origin, normal, keep):
    """Ring groove following the local tube profile in the plane through
    `origin` with `normal`. `keep(points)` picks which crossing of the plane is
    the intended one (a plane through the ring cuts the tube twice)."""
    to_local = frame(origin, normal)
    to_world = np.linalg.inv(to_local)
    section = transform(solid, to_local).slice(0)
    polys = [p for p in section.to_polygons()
             if keep((to_world @ [*p.mean(axis=0), 0, 1])[:3])]
    profile = mf.CrossSection(polys, mf.FillRule.Positive)
    ring = profile.offset(2, mf.JoinType.Round) - profile.offset(-GROOVE_DEPTH, mf.JoinType.Round)
    ring = ring.extrude(GROOVE_WIDTH).translate((0, 0, -GROOVE_WIDTH / 2))
    return transform(ring, to_world)


def pin_hole():
    """Hole spanning both halves, centered on z=0, with chamfered mouths."""
    r = HOLE_D / 2
    bore = mf.Manifold.cylinder(2 * HOLE_DEPTH, r, r, SEGMENTS).translate((0, 0, -HOLE_DEPTH))
    cone = mf.Manifold.cylinder(MOUTH_CHAMFER, r + MOUTH_CHAMFER, r, SEGMENTS)
    return bore + cone + cone.mirror((0, 0, 1))


def pin():
    """Pin lying along X with a flat underside and chamfered ends."""
    r, c = PIN_D / 2, 0.4
    length = 2 * HOLE_DEPTH - PIN_GAP
    body = (
        mf.Manifold.cylinder(c, r - c, r, SEGMENTS)
        + mf.Manifold.cylinder(length - 2 * c, r, r, SEGMENTS).translate((0, 0, c))
        + mf.Manifold.cylinder(c, r, r - c, SEGMENTS).translate((0, 0, length - c))
    )
    body = body.rotate((0, 90, 0))
    body = body.trim_by_plane((0, 0, 1), -r + PIN_FLAT)
    return body.translate((0, 0, r - PIN_FLAT))


def wedge(a0, a1):
    """Prism covering the sector between two angles (a1 - a0 < 180)."""
    a = np.radians(np.linspace(a0, a1, 64))
    pts = np.vstack([[0, 0], np.c_[500 * np.cos(a), 500 * np.sin(a)]])
    return mf.CrossSection([pts]).extrude(40).translate((0, 0, -20))


def lay_flat(mesh):
    """Rotate about Z to the angle that best fits the bed, center on origin."""
    hull = mesh.vertices[:, :2]
    best = None
    for t in np.radians(np.arange(0, 180, 0.5)):
        c, s = np.cos(t), np.sin(t)
        e = np.ptp(hull @ np.array([[c, s], [-s, c]]), axis=0)
        slack = min(BED[0] - e[0], BED[1] - e[1])
        if best is None or slack > best[0]:
            best = (slack, t)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(best[1], [0, 0, 1]))
    lo, hi = mesh.bounds
    mesh.apply_translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    return mesh


def main():
    solid = load_solid(SRC)

    for a in ARC_END_ANGLES:
        d = np.array([np.cos(np.radians(a)), np.sin(np.radians(a)), 0])
        solid = solid - groove(solid, (0, 0, 0), (-d[1], d[0], 0), lambda p, d=d: p @ d > 0)
    for x in BARREL_START_X:
        solid = solid - groove(solid, (x, 0, 0), (1, 0, 0), lambda p: p[1] < -100)

    centers = [(ARC_RADIUS * np.cos(np.radians(a)), ARC_RADIUS * np.sin(np.radians(a)))
               for a in PIN_ANGLES] + BARREL_PINS
    holes = mf.Manifold.batch_boolean(
        [pin_hole().translate((x, y, 0)) for x, y in centers], mf.OpType.Add)
    solid = solid - holes

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.stl"):
        old.unlink()

    limit = (BED[0] - 2 * BED_MARGIN, BED[1] - 2 * BED_MARGIN)
    for half, (c0, c1) in CUTS.items():
        whole = solid.trim_by_plane((0, 0, 1 if half == "upper" else -1), 0)
        middle = whole ^ wedge(c0, c1)
        ends = (whole - wedge(c0, c1)).decompose()
        # Right end holds the -45 degree arc end (x > 0), left end the 225.
        ends.sort(key=lambda p: -p.bounding_box()[0])
        pieces = {"1-right": ends[0], "2-middle": middle, "3-left": ends[1]}
        for name, part in pieces.items():
            if half == "lower":
                # Flip over (a rotation, not a mirror) so the cut face is down.
                part = part.rotate((0, 180, 0))
            mesh = lay_flat(to_trimesh(part))
            assert mesh.is_watertight, (half, name)
            e = mesh.extents
            assert e[0] <= limit[0] and e[1] <= limit[1], (half, name, e)
            fname = f"handle-{half}-{name}.stl"
            mesh.export(OUT / fname)
            print(f"{fname}: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm")

    n = len(centers) + SPARE_PINS
    pins = mf.Manifold.batch_boolean(
        [pin().translate((0, i * (PIN_D + 3), 0)) for i in range(n)], mf.OpType.Add)
    mesh = to_trimesh(pins)
    mesh.export(OUT / f"handle-pins-x{n}.stl")
    print(f"pins: {n} ({len(centers)} + {SPARE_PINS} spare), "
          f"{PIN_D} mm dia, {2 * HOLE_DEPTH - PIN_GAP} mm long")


if __name__ == "__main__":
    main()
