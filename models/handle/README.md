# Lantern handle

`new-handle.stl` is the source model: a C-shaped bail, 350 x 312 mm, with a
16.7 mm round tube that tapers through an elbow into a 20.4 mm end barrel on
each side.

## Printing

`print/` holds the handle cut lengthwise in its own plane, so every piece lies
flat with layer lines along the handle (its strongest direction). Each half is
cut into three sections that fit a 220 x 215 mm bed (Creality K2 SE), with at
least 5 mm of margin.

The joints in the upper and lower halves are staggered by 18 degrees (about
52 mm), like brickwork, so no joint goes all the way through the handle.

| File | Size (mm) |
| --- | --- |
| `handle-upper-1-right.stl` | 182 x 178 x 10.2 |
| `handle-upper-2-middle.stl` | 193 x 187 x 8.3 |
| `handle-upper-3-left.stl` | 210 x 205 x 10.2 |
| `handle-lower-1-right.stl` | 210 x 205 x 10.2 |
| `handle-lower-2-middle.stl` | 193 x 187 x 8.3 |
| `handle-lower-3-left.stl` | 182 x 177 x 10.2 |
| `handle-pins-x15.stl` | 13 pins + 2 spare |

Every piece is already rotated to fit the bed, cut face down. Print one of each.

Inset grooves (0.8 mm wide, 0.5 mm deep) ring the tube where the arc meets
each elbow and where each elbow meets its barrel.

Suggested settings:

- Smooth PEI or glass for a clean glue face. Turn on elephant's foot
  compensation (about 0.15 mm) so the seams close without a lip.
- 4 walls. Infill barely matters; the tube is mostly wall.
- PETG or ABS/ASA: use a brim. Long thin parts like to lift at the ends.

## Assembly

`upper-1-right` and `lower-3-left` look almost identical, as do
`upper-3-left` and `lower-1-right`. Pencil the name on each piece's cut face as
it comes off the bed.

1. Dry fit everything first. Pins should push in by hand; if tight, run a
   4.5 mm drill through the holes.
2. Lay out the three upper pieces cut face up: right, middle, left. Glue the
   pins into them.
3. Glue the butt joints between the upper pieces, then glue the full cut face.
4. Lay the lower pieces on top: each lower joint lands mid-way along an upper
   piece. Clamp along the arc until cured.
5. Sand the seams.

## Regenerating

```
pip install trimesh manifold3d numpy scipy
python3 tools/split_handle.py
```

Bed size, cut angles, groove size, and pin size, clearance and positions are
constants at the top of `tools/split_handle.py`.
