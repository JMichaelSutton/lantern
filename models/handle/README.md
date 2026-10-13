# Lantern handle

`new-handle.stl` is the source model: a C-shaped bail, 350 x 312 mm, with a
16.7 mm round tube and rectangular end blocks.

## Printing

`print/` holds the handle cut lengthwise in its own plane, so each half lies
flat and the layer lines run along the handle (its strongest direction).

| File | Qty | Notes |
| --- | --- | --- |
| `handle-half-a.stl` | 1 | Cut face down, 10.2 mm tall |
| `handle-half-b.stl` | 1 | Mirror of A. Not interchangeable: the end blocks differ by 0.8 mm |
| `handle-pins-x10.stl` | 1 plate | 9 needed + 1 spare. Prints lying down on a flat |

Each half needs a bed of at least 350 x 312 mm.

Suggested settings:

- Smooth PEI or glass for a clean glue face. Turn on elephant's foot
  compensation (about 0.15 mm) so the seam closes without a lip.
- 4 walls. Infill barely matters; the tube is mostly wall.
- PETG or ABS/ASA: use a brim. Long thin parts like to lift at the ends.

## Assembly

1. Dry fit first. Pins should push in by hand; if tight, run a 4.5 mm drill
   through the holes.
2. Glue the pins into half A.
3. Glue the faces (CA or epoxy for PLA/PETG; acetone weld or epoxy for ABS/ASA),
   flip half B onto A, and clamp along the arc until cured.
4. Sand the seam.

## Regenerating

```
pip install trimesh manifold3d numpy scipy
python3 tools/split_handle.py
```

Pin size, clearance, depth and positions are constants at the top of
`tools/split_handle.py`.
