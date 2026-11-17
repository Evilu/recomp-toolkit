---
name: scripted-runs
description: Drive a ported game without a window using the smoke host's input scripts and frame dumps - skipping intros, navigating menus, reaching gameplay, capturing frames, and counting API calls. Use for any automated check, reproduction from user steps, or before-and-after comparison, instead of opening the app on the user's screen.
---

# Scripted runs

Build the offscreen host once per change: `tools/build.py --game <id> --target smoke`, then

```sh
RECOMP_FRAMES=/tmp/frames RECOMP_FRAME_EVERY=100000 \
  build/<id>/recomp/recomp_smoke --script steps.txt > run.log 2>&1
```

The user may be playing their own copy: never stop processes by name, only ones you started.

## Script verbs (host/script.h)

```
wait 4000                 # milliseconds of guest time
key ESCAPE down           # DirectInput names: ESCAPE RETURN SPACE TAB UP DOWN LEFT RIGHT ...
key ESCAPE up
guestclick 1288 979       # guest pixels at the current display mode
dump name                 # smoke_<name>_present.ppm and smoke_<name>_scene.ppm
dumpc name                # smoke_<name>_composite.ppm: the presenter's composed output
quit
```

Dumps land in `build/recomp/live/frames/`. To read one, convert with
`sips -s format png X.ppm --out X.png`.

- Measure guest coordinates from a dump: a 900-px-wide preview of a 1440-wide mode scales by 0.625.
- Menus take time to accept input after an intro is skipped; wait longer rather than adding clicks.
- A screen that ignores NEXT may need a selection first.
- For flicker, dump ten frames 16 ms apart and compare file sizes or mean brightness: two
  alternating values mean two images are taking turns.

## Reproducing user steps

Turn the user's description into a script ("press right 5 times, hold up 10 seconds") and dump
during the action, not only after it.

## Counters and traces

- `RECOMP_IMPORT_STATS=1`: per-import and per-COM-method call counts at exit; shows which API
  family a game really uses (`IDirect3DDevice3::SetTexture`, `CreateSurface` per frame).
- The run report at exit gives presented frames, draws, readbacks, locks, flips and repeats.
- For one-off questions (why frames seal, what a lock targets), add a temporary `getenv`-gated
  `fprintf`, back up the file first, and restore it before committing.

## The real app

The smoke host does not run the windowed presenter. When a problem shows only in the app:

- `RECOMP_INPUT_SCRIPT=steps.txt` drives the app (`wait`, input verbs and `quit`; no dumps).
- `RECOMP_HOST_DUMP_EVERY=N RECOMP_HOST_DUMP_DIR=dir` writes `present_*.ppm` (the guest frame
  handed to the presenter) and `scene_*.ppm` (the Direct3D target), not the final window image.
- The terminal usually cannot capture the screen. Ask the user for a screenshot or a screen
  recording, and extract frames from a `.mov` with AVFoundation (`AVAssetImageGenerator` in a
  short Swift script); `ffmpeg` may not be installed.
- Save the app's log before relaunching it; the next run overwrites it.
