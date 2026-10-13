# Image analysis: reference.png

Protocol: `grimoire/intake/image_analysis.md`. Pixel measurements come from a row scan of the
1080x1080 reference (object pixels = max channel < 150; background is a baked grey/white checker).
Unit used below: 1 u = body width = 396 px.

## Layer 1. Identification
- Work type: fragrance flacon (perfume bottle) with separate overcap. Broad class: cosmetic packaging, glass container.
- primaryDomain: `object`. Confidence 0.95.

## Layer 2. Form and silhouette
- Bounding volume: one tall rounded cuboid (body) with a coaxial short cylinder-like collar and a squared overcap on top.
- Symmetry: bilateral about the vertical axis in this view (left edge x=342, right edge x=738, centre x=540).
- Shape language: geometric with large fillets.
- Proportions (observed, front projection):
  - Body: W 1.00 u (396 px), H 1.62 u (y 350 to 992, 642 px). Sides taper very slightly toward the base (W 396 at y 600, 386 at y 920).
  - Top shoulder fillet radius about 0.08 u; bottom corner fillet about 0.12 u.
  - Collar/neck: W 0.24 u (96 px), H 0.08 u (y 318 to 350).
  - Overcap: W 0.35 u (138 px), H 0.27 u (y 213 to 318), small edge fillet; lower 10 px chamfers in to the collar.

## Layer 3. Decomposition
- Macro: `body` (glass flacon), `overcap`.
- Meso: body = `glass-upper` (transparent green zone, y 352 to 566) + `lacquer-lower` (opaque black zone, y 566 to 992); `collar` between body and cap.
- Micro: `emblem` (interlocking double-G mark inside a raised ring, centre (540, 650), outer diameter about 0.46 u), `wordmark` (one line of green serif caps, y about 752), `subline` (one line of small wide-tracked caps, y about 918).

## Layer 4. Spatial relationships
- `<collar, attached-to, body top>` contact: butt, centred.
- `<overcap, above, collar>` contact: socket (cap sleeves over collar).
- `<glass-upper, above, lacquer-lower>` contact: flush-with, horizontal split line at 0.33 of body height from top.
- `<emblem, embedded-in, lacquer-lower front face>` relief: raised ring, about 0.01 u.
- `<wordmark|subline, flush-with, lacquer-lower front face>` printed.

## Layer 5. Materials (PBR)
- Overcap: black dielectric, gloss; observed albedo near (2,2,2) with soft vertical highlight bands at the edges. roughness about 0.25, metalness 0.
- Glass upper: transparent green glass over green liquid; observed mid colour (1,105,79) brightening to (1,119,92) toward the split. Inference: tinted glass + liquid; treated as transmissive physical material, ior 1.5.
- Lacquer lower: opaque black gloss coating over glass; albedo (0,0,0) to (8,8,8). roughness about 0.2, clearcoat 1.
- Emblem fill: same green as upper glass (0,114,85); ring: black gloss relief with grey edge highlights (55,55,55).
- Text: printed green ink (0,35,23 on the subline sample; wordmark brighter green).

## Layer 6. Colour and finish
- Green: vivid blue-green, mid-low value. Stops top to bottom: #01694F (0.03), #017559 (0.5), #01775C (0.98 of the green zone).
- Black: neutral, very low value, gloss finish.

## Layer 7. Identity features
1. Two-zone body: green transparent top third, black opaque bottom two thirds, hard horizontal split.
2. Squared black overcap narrower than the body, on a thin collar.
3. Interlocking double-G emblem in a raised ring, green fill, centred in the upper part of the black zone.
4. Green serif wordmark below the emblem; small tracked subline near the base.
5. Large-radius vertical edges and rounded shoulders.

## Layer 8. Uncertainty
- Body depth (front-to-back) is hidden in this single front view. Inference: about 0.45 u, typical for this flask class. Speculative.
- Back face, side faces and base are hidden; assumed plain and mirror of the front without print.
- Interior liquid level is not separable from glass tint; modelled as one tinted transmissive volume.
- The checker background is baked into the PNG (not real alpha), so silhouette masks come from the threshold scan above.
