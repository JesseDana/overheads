# Plan file format

A plan is one JSON document per production. The standalone page keeps each one in the browser's localStorage under `shotplans:<id>` (with `shotplans:index` listing the ids); Share → Plan file downloads it, and the production menu imports one. Inside claude.ai the same documents live in the artifact's `scenes` collection, which is how Claude can read and write plans.

The app repairs bad data on load without saying so, so if you generate plans with a script or an AI, load the result and check it. Set and Shots, Fit, and selection are view state in the app only; nothing about them is stored in the document.
- **Numbers and ids.**
  - Units are feet and degrees; y points down, and `r` is clockwise from up.
  - Write numbers as numbers, not strings.
  - Ids must match `[A-Za-z0-9_-]{1,40}` and be unique across the whole document (groups, shots, beats, cast, rig and items share one space). Colours are `#rrggbb`. Anything else is replaced on load.
  - Stamp `updatedAt` with the current time in ms. Also write `schemaVersion: 2`.
- **Production** (one document). It holds `name`, `sensor` (`ff` or `s35`, used only for cameras with no body), `ar` (aspect for every shot: native, 1.33, 1.66, 1.78, 1.85, 2.00 or 2.39; default 1.78), `axisOn` (show the 180° line), `fig` (`picto` for pictogram figures; absent for rounded), `notes`, `estimated`, `layerState` (per layer `hidden`, `locked`; layer ids arch, furn, light, cast, note), `cast` (`id`, `name`, `color`), `rig` (the location's cameras: `id`, `name`, `color`, and optional `body`, `mode`, `sq`), `locs` (the location library: `id`, `name`, `notes`), `groups` (the script's scenes, in story order: each `id`, `locId`, optional `ownArch: true` when the scene has its own walls, and optional strings `num` (e.g. "1.5"), `name`, `ie` (INT, EXT or INT/EXT), `time`, `syn`, `intent`, `notes`), `shots` (each `id`, `name`, `grp` (its scene's id), optional `letter` (capitals, e.g. `C` or `AA`; overrides the automatic letter), `type`, `desc`, `tools`, `notes`, `ar`, `axis`: `off`, or `castId|castId`, absent for auto; and `beats` with `id` and `name`), and `items`.
  - Keep `shots` in scene order; the app re-sorts them by `groups` on load. A shot with an unknown `grp` joins the scene of the shot before it; a document with no `groups` gets one scene holding every shot. A shot with no char or cam items is a shot with no plan yet.
  - **Who owns a set piece.** `wall`, `window`, `door` and `img` carry `loc` (a location id), or `grp` (a scene id) when that scene has `ownArch`. `furn`, `light`, `frame` and `text` carry `grp`: each scene has its own copies, so writing a piece for three scenes means three items. `char` and `cam` carry `shot` as before. A scene's `locId` decides which walls it sees.
  - A document from before v41 (no `locs`) is migrated on load: one location named after the document (or one per distinct `loc` text on the scenes), walls go to it, and the first scene keeps the furniture and lights while every other scene at that location gets copies with ids `<id>_<sceneId>`. Ids made during migration are deterministic so merges stay item by item. Write `locs`, `locId`, `loc` and `grp` explicitly rather than relying on migration.
  - `body` is one of gff, gs35, fx3, fx5, fx30, fx2, fx6, fx9, burano, venice2, c50, c70, c80, c400, c300m3, c500m2, r5c, amini, aminilf, a35. `mode` is an index into that body's recording modes (0 first). `sq` is 1, 1.3, 1.5, 1.6, 1.8 or 2.
  - A rig camera's `color` is stored but not shown; cameras draw in ink.
  - A hidden layer is left out of Fit and of the PDF.
- **Items.**
  - `wall`: `x1 y1 x2 y2 t name`. Wall names are what the frames call the background.
  - `window`: `x y r w`. `door`: `x y r w flip`; x and y are the hinge end.
  - `furn`: `shape x y w h r label`; `h` is depth. The label titles its controls.
  - `light`: `type` (point or broad), `x y r level spread w name`.
  - `frame`: `type` (diff, silk, bounce or neg), `size x y r name`. The app calls these diffusion frames.
  - `text`: `text x y size`.
  - `char`: `shot`, `cast`, `k`. Write one per person per shot.
  - `cam`: `shot rig held k`. One per rig camera per shot. Name comes from the rig entry. Optional `body`, `mode`, `sq` on the item override the rig for that shot only. Optional `photos`: `{beatId or "all": {src, r, tl, hf, ar, src2, f35}}` (scout photos; upload to the artifact's assets and write the `/_blob/` URL).
- **Poses (`k`).**
  - `k` has exactly one pose per beat of that item's shot, by position.
  - Both: `x y r`, plus `out` when the person or camera isn't in that beat. Optional `cv: [x, y]` bends the move from the previous beat into this one.
  - Talent: `ps` is stand, walk, bar (30-inch stool) or chair. Optional `look`: a cam or char item id in the same shot; the facing then follows that item.
  - Camera: `f` lens in mm (any value), `h` lens height in ft (the app steps in 3 inches), `tl` tilt in degrees, used with `tm:"man"`; without `tm` and with an aim the tilt is automatic (eyes on the upper third). `aim` is a char item id in the same shot, `ap` the framing (l, c or r), `aims` further char ids held in the same frame.
  - `held:true` (locked off) only when every pose matches. In the app a locked-off camera changes in every beat at once.
- **Distances.** The readout and PDF give each person's distance to the plane of focus (depth along the camera's axis), so two people matched for focus read the same. The talent sheet's distance box is the straight-line distance to the lens. Matching OTS frames means the same camera-to-subject distance and the same lens.
- **Mirroring.** A mirrored shot reflects left–right as the cameras see it, then slides so the chosen person lands on the new person's own spot; cameras keep their subject and l/r thirds swap.
- **Adding a beat** means appending a pose to every char and cam in that shot. Deleting a middle beat means splicing every `k` at that index. In the app, a change in one beat carries to the following beats that stood the same.
- **Merging.** When two devices edit the same production, changes merge item by item; if both changed the same item, the local version wins and the other is one Undo away.
