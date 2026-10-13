"""Split the lantern bail handle into two flat-printing halves with alignment pins.

The handle lies in the XY plane and is symmetric about z=0, so cutting at z=0
gives two halves that each print flat face down. Layer lines then run along the
handle, which is its strongest direction under bending.

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

# Tube centerline is a circle about the origin from about -40 to 220 degrees.
ARC_RADIUS = 166.55
PIN_ANGLES = [-30, 10, 50, 90, 130, 170, 210]
# Centers of the rectangular end blocks.
BLOCK_PINS = [(-89.5, -126.5), (88.7, -126.5)]

PIN_D = 4.0          # printed pin diameter
HOLE_D = 4.4         # hole diameter (0.2 mm radial clearance)
HOLE_DEPTH = 5.5     # per half; tube half-height is 8.35, leaving ~2.8 mm above
PIN_GAP = 0.5        # pin is this much shorter than the two holes combined
MOUTH_CHAMFER = 0.5  # cone at the hole mouth to absorb elephant's foot
PIN_FLAT = 0.4       # flat shaved off the pin so it prints lying down
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
    duplicate of the tube surface lying within ~1 um of it, and two end blocks
    that only add sharp corners (~0.4 cm3) where the shell's ends are rounded.
    Unioning near-coincident surfaces leaves sliver triangles that slicers
    report as errors, so keep only the shell, which is the largest closed body."""
    bodies = trimesh.load(path).split(only_watertight=True)
    return to_manifold(max(bodies, key=lambda b: b.volume))


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


def main():
    solid = load_solid(SRC)

    centers = [(ARC_RADIUS * np.cos(np.radians(a)), ARC_RADIUS * np.sin(np.radians(a)))
               for a in PIN_ANGLES] + BLOCK_PINS
    holes = mf.Manifold.batch_boolean(
        [pin_hole().translate((x, y, 0)) for x, y in centers], mf.OpType.Add)
    solid = solid - holes

    # Both halves print cut face down. Flipping half B over (about the Y axis)
    # to mate with half A mirrors it in X, so B is A mirrored in X. The shell is
    # not exactly left-right symmetric (end blocks differ by ~0.8 mm), so two
    # copies of A would not line up.
    half_a = solid.trim_by_plane((0, 0, 1), 0)
    half_b = half_a.mirror((1, 0, 0))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in [("handle-half-a", half_a), ("handle-half-b", half_b)]:
        mesh = to_trimesh(part)
        mesh.apply_translation((0, 0, -mesh.bounds[0, 2]))
        assert mesh.is_watertight, name
        mesh.export(OUT / f"{name}.stl")
        print(f"{name}: {mesh.extents.round(1)} mm, {mesh.volume / 1000:.1f} cm3")

    # A plate of pins with one spare.
    n = len(centers) + 1
    pins = mf.Manifold.batch_boolean(
        [pin().translate((0, i * (PIN_D + 3), 0)) for i in range(n)], mf.OpType.Add)
    mesh = to_trimesh(pins)
    mesh.export(OUT / f"handle-pins-x{n}.stl")
    print(f"pins: {n} x {PIN_D} mm dia, {2 * HOLE_DEPTH - PIN_GAP} mm long")


if __name__ == "__main__":
    main()
