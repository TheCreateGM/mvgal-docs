---
tags: [mvgal, moc, index]
aliases: [MOC, Documentation Index, Home]
cssclasses: [moc]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: index
---

# MVGAL Documentation — Map of Content

> [!info] Source version
> **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.
> Source version **0.7.16**; the source changelog documents releases through **0.7.16**.
> Every page in this vault was re-verified against the source tree on **2026-09-30**.

Cross-vendor GPU discovery and integration components for Linux; operational support is capability-dependent.

## 🚀 Start Here

| Note | Purpose |
|------|---------|
| [[docs/QUICKSTART\|Quick Start]] | Get MVGAL running in 5 minutes |
| [[docs/INSTALL\|Installation]] | Full installation guide (COPR, Secure Boot, config) |
| [[docs/SECURE_BOOT\|Secure Boot & MOK]] | MOK enrollment for Secure Boot systems |
| [[docs/CHANGELOG\|Changelog]] | Release history through v0.7.16 |
| [[docs/STATUS\|Project Status]] | What is verified, and what is not |

## 📖 Reference

| Note | Purpose |
|------|---------|
| [[docs/ARCHITECTURE\|Architecture]] | System architecture overview |
| [[docs/DESIGN\|Design Document]] | Design decisions, and which ones shipped |
| [[docs/API\|API Reference]] | Public C API reference (29 headers) |
| [[docs/MEMORY\|Memory Management]] | Transfer paths, allocation, and what is not implemented |
| [[docs/STRATEGIES\|Scheduling Strategies]] | The 13 public strategy identifiers |
| [[docs/POWER_MANAGEMENT\|Power Management]] | Power, DVFS, thermal |
| [[docs/HARDWARE_COMPATIBILITY\|Hardware Compatibility]] | Supported GPUs and platforms |
| [[docs/BUILD\|Build Guide]] | Build from source (CMake, Meson, Zig, DKMS) |
| [[docs/TROUBLESHOOTING\|Troubleshooting]] | Common issues and fixes |
| [[docs/STEAM_INTEGRATION\|Steam/Proton]] | Steam integration, and what is dormant |

## 🔍 What's New in 0.7.16

> [!tip]
> The summary below is generated from the source changelog. For the full prose entry see [[docs/CHANGELOG\|Changelog]].

```dataview
TABLE WITHOUT ID
  file.link AS "Note",
  file.mtime AS "Last reviewed"
FROM "docs"
WHERE file.mtime >= date(2026-09-30)
SORT file.mtime DESC
```

Two releases landed together on 2026-09-30. Both were found by reading the
source rather than from a field report, and each was reproduced before it was
changed.

**v0.7.15 — a memory-corruption fix.** All headline items, verified in this revision:

- **Copies applied their offsets twice.** `mvgal_memory_copy()` passed `src_offset` and `dst_offset` to `mvgal_memory_map()`, which already returns a pointer advanced by that offset, then added the same offsets again at the `memcpy`. A copy from source 1024 to destination 2048 landed at `base + 2 * 2048`, overrunning the mapping. Every existing test copied at offset 0, the one case where a double-applied offset is a no-op. See [[docs/MEMORY\|Memory Management]] § Buffer copies.
- **The same function unmapped buffers it did not own.** The cleanup was dead code, guarded by a `MAPPED` test `mvgal_memory_map()` had already satisfied, and the destination-map failure path tore down a source mapping it never created. Host-valid buffers carry an allocator-owned `host_ptr`, so unmapping would have freed memory the buffer still pointed at.

**v0.7.16 — the scheduler and command-DAG paths made real.** All headline items, verified in this revision:

- **Custom splitters could never be released.** They were registered by value but unregistered by address, and the internal slot address is never exposed to a caller, so removal always reported the splitter as absent. Matching is now by value across `analyze`, `split`, `merge` and `user_data`, and the release function gained the public declaration it never had. See [[docs/API\|API Reference]] § Custom Splitters.
- **`mvgal_translate_dag()` returned its argument unchanged** while its header promised a translated copy, so any caller edit silently corrupted the source DAG. It now deep copies and rewires every dependency edge onto the copies.
- **`mvgal_emit_dag()` always returned `VK_ERROR_LAYER_NOT_PRESENT`.** It now resolves command entry points through the device dispatch table and replays in recording order. Node types with no captured arguments return a specific error instead of being skipped, because a silent skip renders the wrong frame.
- **The command buffer to DAG map leaked on collision.** It was open-addressed with no collision handling, so two buffers hashing alike overwrote a live DAG. Lookups now probe, and beginning a second recording for the same buffer destroys the old DAG rather than dropping it.
- **A packaging bug meant the CI rpm stage could never pass.** The pipeline wrote its output directory *inside* the git checkout, and `scripts/mksrpm.sh` refuses a dirty tree. Both scratch directories are now ignored. The dirty-tree guard itself was deliberately left intact, because it exists to catch builds depending on uncommitted source.

## ⚠️ Read Before Relying on a Feature

Three areas of this documentation describe capability that the current source does **not** deliver. Each page carries an explicit callout. All three were re-checked against the v0.7.16 tree on **2026-09-30** and all three still hold.

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
