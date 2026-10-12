---
tags: [mvgal, moc, index]
aliases: [MOC, Documentation Index, Home]
cssclasses: [moc]
mvgal_version: "0.7.21"
mvgal_verified: 2026-10-04
mvgal_role: index
---

# MVGAL Documentation — Map of Content

> [!info] Source version
> **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.
> Source version **0.7.21**; the source changelog documents releases through **0.7.21**.
> Every page in this vault was re-verified against the source tree on **2026-10-04**.

Cross-vendor GPU discovery and integration components for Linux; operational support is capability-dependent.

## 🚀 Start Here

| Note | Purpose |
|------|---------|
| [[docs/QUICKSTART\|Quick Start]] | Get MVGAL running in 5 minutes |
| [[docs/INSTALL\|Installation]] | Full installation guide (COPR, Secure Boot, config) |
| [[docs/SECURE_BOOT\|Secure Boot & MOK]] | MOK enrollment for Secure Boot systems |
| [[docs/CHANGELOG\|Changelog]] | Release history through v0.7.21 |
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

## 🔍 What’s New in 0.7.21

> [!tip]
> The summary below is generated from the source changelog. For the full prose entry see [[docs/CHANGELOG|Changelog]].

```dataview
TABLE WITHOUT ID
  file.link AS "Note",
  file.mtime AS "Last reviewed"
FROM "docs"
WHERE file.mtime >= date(2026-10-04)
SORT file.mtime DESC
```

**v0.7.21 is the first release in this vault driven by a field report rather than
by reading the source.** The difference is visible in what it found. Every
earlier release below was caught by an author reading code; this one was caught
by someone installing the package and running the shipped tools on a real
machine, and the two most serious findings were both things a source-reading
pass had walked straight past.

**v0.7.20 — reproducible source artefacts.** Found by reading the source, then reproduced:

- **The source tarball was reproducible in name only.** `vendor/` is tracked rather than gitignored, so `git archive` already emitted all 1109 of its paths and the packaging script then copied a second full tree over the top — nesting `vendor/vendor/` and restamping the parent’s mtime with the wall clock. That mtime was the *only* byte that differed between rebuilds, which is what made the bug easy to miss.
- **BUILDTIME was the wall clock.** Setting `SOURCE_DATE_EPOCH` changes nothing on rpm 6.0.2 unless the opt-in macro `use_source_date_epoch_as_buildtime` is also defined, which it deliberately ships without. Tarball and SRPM are now byte-identical across rebuilds of one commit.
- **Binary RPMs still are not.** Two axes remain: rpmbuild injects a random ELF build-id, and the build directory is baked into DWARF. Both, and the reason they are not being papered over, are documented in [[docs/STATUS|Project Status]] § Reproducibility limits.

**v0.7.21 — a black-box test report against 0.7.20.** Found by running the shipped
tools on a single-GPU Intel host, then reproduced:

- **A capability problem that reads exactly like a permissions problem.** The daemon’s IPC socket was `root:root`, locking every `mvgal` group member out of all CLI IPC while `sudo` kept working. The `chown()` was correct; the unit’s `CapabilityBoundingSet` omitted `CAP_CHOWN`, and because a bounding set caps what a uid-0 process can ever hold — and root is not a member of `mvgal` — the call could only fail, quietly, since its result was discarded. This is the finding that justifies the whole exercise: a reviewer reading `IpcServer::init()` sees a correct `chown()` and moves on. See [[docs/TROUBLESHOOTING|Troubleshooting]] § Daemon socket permissions.
- **The OpenCL ICD advertised a version it did not implement.** It reported `OpenCL 1.2` while exporting 2 of the 7 core entry points 1.2 added, so an application using a 1.2 feature received `NULL` from ocl-icd rather than an error.
- **Two fixes replaced first attempts that would not have worked.** The configuration merge keyed on bare key names — `priority` and `enabled` repeat across sections, and `psu_capacity_watts` *exists* in the new file with a different value, so the user’s setting would still have been dropped, which is precisely the case reported. The shared-memory marker borrowed a bit in the kernel-owned UAPI `flags` word, where a kernel-set bit 31 would mislabel real VRAM as shared.
- **Two reported items were not MVGAL’s fault, and were closed as such.** The Vulkan loader warning about display entry points cannot originate from MVGAL: both entry points resolve through the shipped ICD’s negotiated interface version 5, and no ICD manifest has shipped in `vulkan/icd.d` since 0.7.14. The `card0` concern needed no code change; enumeration selects on PCI vendor ID and was confirmed on a host exposing only `card1` with both `i915` and `xe` loaded.

## ⚠️ Read Before Relying on a Feature

Three areas of this documentation describe capability that the current source does **not** deliver. Each page carries an explicit callout. All three were re-checked against the v0.7.21 tree on **2026-10-12** and all three still hold.

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
