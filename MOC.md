---
tags: [mvgal, moc, index]
aliases: [MOC, Documentation Index, Home]
cssclasses: [moc]
mvgal_version: "0.7.19"
mvgal_verified: 2026-10-04
mvgal_role: index
---

# MVGAL Documentation — Map of Content

> [!info] Source version
> **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.
> Source version **0.7.19**; the source changelog documents releases through **0.7.19**.
> Every page in this vault was re-verified against the source tree on **2026-10-04**.

Cross-vendor GPU discovery and integration components for Linux; operational support is capability-dependent.

## 🚀 Start Here

| Note | Purpose |
|------|---------|
| [[docs/QUICKSTART\|Quick Start]] | Get MVGAL running in 5 minutes |
| [[docs/INSTALL\|Installation]] | Full installation guide (COPR, Secure Boot, config) |
| [[docs/SECURE_BOOT\|Secure Boot & MOK]] | MOK enrollment for Secure Boot systems |
| [[docs/CHANGELOG\|Changelog]] | Release history through v0.7.19 |
| [[docs/STATUS\|Project Status]] | What is verified, and what is not |

## 📖 Reference

| Note | Purpose |
|------|---------|
| [[docs/ARCHITECTURE\|Architecture]] | System architecture overview |
| [[docs/DESIGN\|Design Document]] | Design decisions, and which ones shipped |
| [[docs/API\|API Reference]] | Public C API reference (30 headers) |
| [[docs/MEMORY\|Memory Management]] | Transfer paths, allocation, and what is not implemented |
| [[docs/STRATEGIES\|Scheduling Strategies]] | The 13 public strategy identifiers |
| [[docs/POWER_MANAGEMENT\|Power Management]] | Power, DVFS, thermal |
| [[docs/HARDWARE_COMPATIBILITY\|Hardware Compatibility]] | Supported GPUs and platforms |
| [[docs/BUILD\|Build Guide]] | Build from source (CMake, Meson, Zig, DKMS) |
| [[docs/TROUBLESHOOTING\|Troubleshooting]] | Common issues and fixes |
| [[docs/STEAM_INTEGRATION\|Steam/Proton]] | Steam integration, and what is dormant |

## 🔍 What's New in 0.7.19

> [!tip]
> The summary below is generated from the source changelog. For the full prose entry see [[docs/CHANGELOG\|Changelog]].

```dataview
TABLE WITHOUT ID
  file.link AS "Note",
  file.mtime AS "Last reviewed"
FROM "docs"
WHERE file.mtime >= date(2026-10-04)
SORT file.mtime DESC
```

Five releases landed between the two audits of this vault. Every one was found
by reading the source rather than from a field report, and each was reproduced
before it was changed.

**v0.7.15 — a memory-corruption fix.** All headline items, verified in this revision:

- **Copies applied their offsets twice.** `mvgal_memory_copy()` passed `src_offset` and `dst_offset` to `mvgal_memory_map()`, which already returns a pointer advanced by that offset, then added the same offsets again at the `memcpy`. A copy from source 1024 to destination 2048 landed at `base + 2 * 2048`, overrunning the mapping. Every existing test copied at offset 0, the one case where a double-applied offset is a no-op. See [[docs/MEMORY\|Memory Management]] § Buffer copies.
- **The same function unmapped buffers it did not own.** The cleanup was dead code, guarded by a `MAPPED` test `mvgal_memory_map()` had already satisfied, and the destination-map failure path tore down a source mapping it never created. Host-valid buffers carry an allocator-owned `host_ptr`, so unmapping would have freed memory the buffer still pointed at.

**v0.7.16 — the scheduler and command-DAG paths made real.** All headline items, verified in this revision:

- **Custom splitters could never be released.** They were registered by value but unregistered by address, and the internal slot address is never exposed to a caller, so removal always reported the splitter as absent. Matching is now by value across `analyze`, `split`, `merge` and `user_data`, and the release function gained the public declaration it never had. See [[docs/API\|API Reference]] § Custom Splitters.
- **`mvgal_translate_dag()` returned its argument unchanged** while its header promised a translated copy, so any caller edit silently corrupted the source DAG. It now deep copies and rewires every dependency edge onto the copies.
- **`mvgal_emit_dag()` always returned `VK_ERROR_LAYER_NOT_PRESENT`.** It now resolves command entry points through the device dispatch table and replays in recording order. Node types with no captured arguments return a specific error instead of being skipped, because a silent skip renders the wrong frame.
- **The command buffer to DAG map leaked on collision.** It was open-addressed with no collision handling, so two buffers hashing alike overwrote a live DAG. Lookups now probe, and beginning a second recording for the same buffer destroys the old DAG rather than dropping it.
- **A packaging bug meant the CI rpm stage could never pass.** The pipeline wrote its output directory *inside* the git checkout, and `scripts/mksrpm.sh` refuses a dirty tree. Both scratch directories are now ignored. The dirty-tree guard itself was deliberately left intact, because it exists to catch builds depending on uncommitted source.

**v0.7.17 — a Rust quality gate that had never run.** Found by reading the source, then reproduced:

- **The gate was vacuous.** `clippy.toml` carried three keys that modern clippy rejects, and clippy aborts on an unreadable configuration file *before* it lints anything, so the Rust crates had never been linted. The file also listed `unwrap` and `expect` under `disallowed-macros`, though they are methods rather than macros, which turned a reporting quirk into a hard failure under `-D warnings`.
- **Four real defects surfaced the moment it ran.** `CrossDeviceFence` was neither `Send` nor `Sync` — a timestamp in a `Cell` and a handle in a raw pointer — so it could never cross a thread boundary. `GpuTimeline::create_fence()` and `FenceManager::create_fence()` each returned a *second*, independent `Arc`, so signalling the returned handle had no effect on the fence they retained. `MvgalError` relied on the implicit C-like enum representation, which cannot hold `Unknown = 0xFFFFFFFF`, and is now `#[repr(u32)]`. `align_up()` hand-rolled the ceiling division `div_ceil()` provides.

**v0.7.18 — a synthetic GPU topology backend.** Found by reading the source, then reproduced:

- **A 30th public header**, `mvgal_mock.h`, lets a test describe a machine that does not exist: seven presets from a single discrete GPU to a four-vendor, three-root-complex box. The GPU manager's rescan substitutes it for the hardware scan, so the scheduler, memory manager and P2P cost model all reach synthetic devices through the ordinary discovery path rather than a test-only shortcut.
- **Thermal inertia, throttling, VRAM occupancy and per-pair link bandwidth are modelled, not canned.** Load is set, time is advanced, and the sensors follow — including the feedback where a hot device throttles and stops heating. See [[docs/API|API Reference]] § Synthetic Topology Backend.
- **It is a test surface and is documented as one.** It shapes what discovery reports; it creates no devices. Four defects were fixed during the work itself, including a fabricated 16 GB/s peer link that let the cost model recommend replication across a link that did not exist.

**v0.7.19 — reproducible source artefacts.** Found by reading the source, then reproduced:

- **The source tarball was reproducible in name only.** `vendor/` is tracked rather than gitignored, so `git archive` already emitted all 1109 of its paths and the packaging script then copied a second full tree over the top — nesting `vendor/vendor/` and restamping the parent's mtime with the wall clock. That mtime was the *only* byte that differed between rebuilds, which is what made the bug easy to miss.
- **BUILDTIME was the wall clock.** Setting `SOURCE_DATE_EPOCH` changes nothing on rpm 6.0.2 unless the opt-in macro `use_source_date_epoch_as_buildtime` is also defined, which it deliberately ships without. Tarball and SRPM are now byte-identical across rebuilds of one commit.
- **Binary RPMs still are not.** Two axes remain: rpmbuild injects a random ELF build-id, and the build directory is baked into DWARF. Both, and the reason they are not being papered over, are documented in [[docs/STATUS|Project Status]] § Reproducibility limits.

## ⚠️ Read Before Relying on a Feature

Three areas of this documentation describe capability that the current source does **not** deliver. Each page carries an explicit callout. All three were re-checked against the v0.7.19 tree on **2026-10-04** and all three still hold.

| Area | Reality | Page |
|------|---------|------|
| Vendor VRAM allocation, compute submission | Return `-EOPNOTSUPP` for all four vendor adapters | [[docs/MEMORY\|Memory]] |
| Frame pacing | `mvgal_fp_submit_frame()` has no call site anywhere in the tree | [[docs/STEAM_INTEGRATION\|Steam]] |
| Proton plugin, WoW64 thunk | `compat/` and `steam/` have no `CMakeLists.txt`, so they are not built | [[docs/STEAM_INTEGRATION\|Steam]] |

## 🗂️ All Notes

```dataview
TABLE WITHOUT ID
  file.link AS "Note",
  mvgal_role AS "Role",
  mvgal_verified AS "Verified"
FROM "docs"
WHERE file.name != "CHANGELOG"
SORT file.name ASC
```

## 🏷️ Tags

```dataview
LIST
FROM #mvgal
SORT file.name ASC
```

---
*Obsidian vault — plugins in use: Dataview (queries above), Tag Wrangler (tag discipline), Obsidian Git (sync), Templater, Linter. Published site is generated by `tools/generate_site.py`, which resolves wikilinks, renders callouts, and precomputes these Dataview queries at build time.*
