---
name: port-a-game
description: Port a new 32-bit Windows game to recomp-toolkit, or continue bringing one up - choosing the release, mapping every module the game loads, writing game.toml, and working through the boot-to-gameplay blockers (missing imports, traps, version probes, helper programs). Use when adding a game under games/<id>, or when a ported game stops at a diagnostic.
---

# Port a game

Follow [CONTRIBUTING](../../../CONTRIBUTING.md#add-a-game) for the commands; this is the working
method behind them, from the Global Operations and GTA2 ports. Scripts here run with the kit's
`.venv/bin/python` from the kit root.

## 1. Choose the release

- Pick a release the translator can read: no SafeDisc/SecuROM (encrypted `.text`, `stxt`
  sections, `drvmgt.dll`). When every official executable is protected, look for an unprotected
  community or freeware build and say so in the game's README.
- Unpack installers on the Mac: `unshield` (InstallShield cabs), `msiextract` (MSI), `bsdtar`
  (ISO), `7zz`. A self-extractor 7-Zip cannot open may store its files plainly after the PE
  overlay; read the record format rather than guessing.
- Record SHA-256 for every image you translate.

## 2. Find every module

- Static imports (`pefile`) show only part of it. Grep the executable for `.dll` strings and
  `LoadLibrary` callers: renderers, sound and game-logic DLLs are often loaded by a name read from
  the registry or a config file (GTA2's `rendername`/`videoname`, LithTech's `object.lto`).
- Each translated DLL is an `[modules.aux.*]` entry. Auxiliary bases must be at or above
  `GUEST_SHIM_END` (`0x10000000`, `runtime/memory_map.h`) and must not overlap; raise
  `guest_size` to cover them. Rebase a DLL that prefers a lower address with
  `scripts/rebase_pe.py` and analyse the rebased copy.

## 3. Code maps

Ghidra 12 headless, one program per module at its final base, then the code-map exporter into
`metadata*/`. Re-export and `--regenerate` after fixing a map in Ghidra; never edit generated code.
Some games overflow the translator's stack: build with `ulimit -s 65520` and
`RUST_MIN_STACK=536870912`.

## 4. Bring-up loop

Run the scripted host (see the `scripted-runs` skill) so nothing opens on the user's screen, read
the first diagnostic, fix it, repeat.

| Diagnostic | Usual cause | Fix |
| --- | --- | --- |
| `unsupported import X` | shim missing or stubbed | `scripts/import_gaps.py` lists candidates up front; implement in `runtime/` or `dx/` |
| `untranslated MNEMONIC` trap | instruction not in the translator allowlist | add it in `translator/crates/rk-x86/src/lower.rs` if SLEIGH models it, then `tools/test.py --translator` |
| call through null after a COM call | game uses an interface it never checks for (`IDirectDrawGammaControl`) | implement the interface |
| "Incorrect version of DirectX" | SDK `GetDXVersion` probing a component the kit lacks (DirectMusic) | native replacement recording the version, documented |
| `CreateProcessA ... not the translated image` | helper program: movie player, launcher, settings app, dedicated server, self-relaunch | `[media] bink_players`, `[environment] set`, or a native replacement of the caller |
| crash in an old SDK call | flag meanings changed between SDK versions (Bink 1.0's `0x04000000`) | decide by the argument, not the newer flag |

Use `scripts/xrefs.py IMAGE "string"|0xADDR|DLL!Func` to find call sites and read the code around
them before changing anything.

## 5. Settings the original installer wrote

Put first-run registry values in `[registry]`. Read the comparison code first: values may need
an exact form (GTA2 compares `rendername` with `"softdll.dll"`, extension included). Developer
builds keep state in `build/recomp/registry.json`, shared between games; packaged apps keep it in
their Application Support profile. Delete a stale value there when testing a new default.

## 6. Native replacements

A replacement is `FN_<addr>` in the game's header pointing at a C++ function, listed in
`[translate] native`; regenerate after adding one. Patterns:

```cpp
// Return immediately from a cdecl/stdcall function (pop N argument bytes as the original's ret).
c->eip = rd32(c->r[R_ESP]);
c->r[R_ESP] += 4; // + argument bytes for stdcall
recomp_return(c);

// Run the translated original, then more: the original pops its return address,
// so push it back before calling another translated function.
fn_004caec0(c);
const uint32_t ret = c->eip;
c->r[R_ESP] -= 4;
wr32(c->r[R_ESP], ret);
fn_004caf50(c);
```

Every replacement carries a comment naming the address, what the original does, and a
`DIVERGENCE(original):` line for what changes.

## 7. Finish

- Verify on screen (the `debug-presentation` skill covers frame problems) and let the user play.
- Remove experiments that did not fix the cause; keep the diff to what the evidence supports.
- `tools/check_game_literals.py`, `tools/format.py --write --paths <changed files>`; `cargo fmt`
  reformats unrelated files, so revert those.
- Write `games/<id>/README.md` (release, where it comes from, checksums, how to prepare the
  folder on a Mac, what works, known gaps) and `DEVELOPMENT.md` (images, bases, native
  replacements, settings).
