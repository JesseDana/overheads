# Shot Plans regression suite

Playwright (sync API) + pytest. It drives the real app file in headless Chrome, the way the claude.ai artifact
host wraps it, and checks behaviour that rounds 1 and 2 fixed. It never edits the app.

## Run

```
cd review/tests
python3 -m pytest -q                                  # v-current: ../shotplans/shot-plans.html
SHOTPLANS_APP=/path/to/other/shot-plans.html python3 -m pytest -q   # any copy
python3 -m pytest -q test_sync.py -k merge            # one area
python3 -m pytest -q -n 4                             # if pytest-xdist is installed
```

Needs: python3, pytest, playwright (Python), Chrome at /usr/bin/google-chrome (override with SHOTPLANS_CHROME),
and poppler (`pdfinfo`, `pdftotext`) for the PDF tests. jsPDF is served from `review/harness/node_modules`.
The full run takes about 4 minutes; each test opens its own browser context, so tests are independent and can
run in any order.

## How it works

- `sp.py`: builds the page like `harness/harness.py` (same host stub, same `SHOTPLANS_APP` rule), seeds scenes into
  localStorage or into an in-page mock of the host db (`DBMOCK`, adapted from `work/r2-data-integrity/lib.py`, with
  separate collections for usage and snapshots), and wraps the page in `App` with small helpers (plan-to-screen
  coordinates, mouse and touch drags, state reads).
- `sp.room_scene()`: a small 16 x 14 ft room built for tests: shot 1 has Ann (moves between beats), Bob, camera A
  locked off and camera B moving; shot 2 has Ann and camera C. Tests that need the owner's real scene use
  `seeds/workshop.json`.
- State is read only through the app's read-only handle `window.__shotplans` (`S`, `cur`, `inShot`, `poseT`,
  `poseAt`, `frameInfo`, `lightTerms`). A few tests set the view or a pose directly, then re-render through the
  app's own resize handler.
- `conftest.py`: one browser per session, one context per `open_app(...)` call.

| File | Area |
|---|---|
| test_touch.py | phone tap-through, 30 px swallow, touch drag threshold |
| test_plan.py | centre grab, Fit vs phone panels, snap to neighbouring beat, seats, box select, hidden-layer chip, add into hidden layer, spawn in room, group move, tablet side column |
| test_cameras.py | locked off: aim and auto tilt across beats, lens per beat, unlock/relock, migration, cut row for moving cameras |
| test_history.py | undo/redo navigation and labels, redo, no-op drags, nudge merging |
| test_keyboard.py | nudge, turn, Cmd+D/A, PageUp/Down, digits, ?, Delete, Esc, typing in fields |
| test_lighting.py | diff/silk, neg, bounce, backlight direction; exposure per camera; rim side; unlit and hidden lighting |
| test_frames.py | cut words, face angle and ◀ ▶ side, BG walls, furniture in frame, tap a frame card |
| test_export.py | shot list sheet and copied text, PDF page count and text layer |
| test_sync.py | db: content-based detection, 3-way merge, clash + undo, adopt clears undo, deletes, deferred snapshots, unsaved replay, focus; local two-tab |
| test_normalize.py | malformed and legacy scenes load, list and save |

## Known limits

- The db mock is not the host: it echoes `hasPendingWrites` and delivers snapshots synchronously after a write.
  Real latency, offline behaviour and `fromCache` snapshots are not modelled.
- Tests assert on wording where wording is the feature (cut words, toasts, shot list lines). A deliberate copy change
  will need the test updated.
- Visual quality (what a person sees) is not judged here; screenshots remain a manual review step.
