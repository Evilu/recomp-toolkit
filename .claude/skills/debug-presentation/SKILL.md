---
name: debug-presentation
description: Diagnose wrong pictures in a ported game - flicker, black or flashing menus, smearing, boxes around sprites, doubled or shrunken images, stale regions. Use when what the window shows differs from what the game should draw.
---

# Debug presentation

A frame passes through several stages, and each can be captured separately:

| Stage | How to see it |
| --- | --- |
| Direct3D target as the device drew it | smoke `dump` → `_scene.ppm`; app `scene_*.ppm` |
| Guest surface handed to the presenter | smoke `dump` → `_present.ppm`; app `present_*.ppm` |
| Presenter's composed output | smoke `dumpc` → `_composite.ppm` |
| The window | user screenshot or recording |

**Start by finding the first stage that is wrong.** If the scene is right and the present is
wrong, the game is fine and the bug is in the kit's composition. Compare the same frame across
stages side by side, and consecutive frames at one stage, before forming a theory.

## Causes found so far

| Symptom | Cause | Where |
| --- | --- | --- |
| Boxes around blended sprites, smearing, stale squares | the R8 coverage mask was blended with the colour target, so blended draws never marked their pixels and the CPU write-back kept old pixels | `graphics/d3d8-wgpu/src/host_gpu/render.rs` (only target 0 blends) |
| A smaller picture over an older full-size one | Enhanced mode renders the world at window resolution and composes it with the guest frame; the layers drifted | per-game `[render] classic = true` |
| Menu mostly black, flashing | a second Flip per drawn frame sealed an empty frame, shown from a recycled target | `host/present_thread.cpp` drops pictureless frames in Classic |
| Menu backgrounds missing in Classic | a game with a Direct3D device draws menus with DirectDraw blits; its menus classify as gameplay | Classic presents the guest surface for every class |
| GPU validation panic on a blit | copy within one texture | staged through a temporary texture |

## Method

- Count before assuming: seal reasons, lock targets and callers, per-frame draws. During the GTA2
  port three plausible theories were built as fixes and removed when the measurements did not
  change.
- Remember which frames repeat: the windowed presenter shows the last frame again at the display
  rate, so a frame type that appears once per game frame may fill most of the screen time.
- When a game locks its render target every frame (DMA's `Vid_GetSurface`), each lock reads the
  GPU image back; that is expected, not a bug by itself.
- Keep fixes general when the cause is in the kit, and per-game (a `game.toml` setting) when the
  game's pattern is unusual. Revert experiments that did not change the measurements.
