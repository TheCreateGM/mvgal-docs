---
tags: [mvgal, moc, index]
aliases: [MOC, Documentation Index, Home]
cssclasses: [moc]
mvgal_version: "0.7.27"
mvgal_verified: 2026-10-24
mvgal_role: index
---

# MVGAL Documentation — Map of Content

> [!info] Source version
> **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.
> Source version **0.7.27**; the source changelog documents releases through **0.7.27**.
> Core architecture and status pages were reconciled against the source tree on **2026-10-24**.

Cross-vendor GPU discovery and integration components for Linux; operational support is capability-dependent.

## 🚀 Start Here

| Note | Purpose |
|------|---------|
| [[docs/QUICKSTART\|Quick Start]] | Get MVGAL running in 5 minutes |
| [[docs/INSTALL\|Installation]] | Full installation guide (COPR, Secure Boot, config) |
| [[docs/SECURE_BOOT\|Secure Boot & MOK]] | MOK enrollment for Secure Boot systems |
| [[docs/CHANGELOG\|Changelog]] | Release history through v0.7.27 |
| [[docs/STATUS\|Project Status]] | What is verified, and what is not |

## 📖 Reference

| Note | Purpose |
|------|---------|
| [[docs/ARCHITECTURE\|Architecture]] | System architecture overview |
| [[docs/CODEBASE\|Codebase Map]] | Directory map and subsystem ownership |
| [[docs/DESIGN\|Design Document]] | Design decisions, and which ones shipped |
| [[docs/API\|API Reference]] | Public C API reference (32 headers) |
| [[docs/MEMORY\|Memory Management]] | Transfer paths, allocation, and what is not implemented |
| [[docs/STRATEGIES\|Scheduling Strategies]] | The 13 public strategy identifiers |
| [[docs/POWER_MANAGEMENT\|Power Management]] | Power, DVFS, thermal |
| [[docs/HARDWARE_COMPATIBILITY\|Hardware Compatibility]] | Supported GPUs and platforms |
| [[docs/BUILD\|Build Guide]] | Build from source (CMake, Meson, Cargo, DKMS) |
| [[docs/TROUBLESHOOTING\|Troubleshooting]] | Common issues and fixes |
| [[docs/STEAM_INTEGRATION\|Steam/Proton]] | Steam integration, and what is dormant |

## 🔍 What’s New in 0.7.27

> [!tip]
> The summary below follows the source changelog. For full details see [[docs/CHANGELOG|Changelog]].

**v0.7.27 fixes three hardware-detection and reporting defects that made
valid hardware look missing or report no stats.** The Vulkan ICD filename
check did not match Fedora's `radeon_icd.x86_64.json`, so AMD GPUs were
reported as having no Vulkan driver, and the AMD shader-backend probe
pointed at mesa's software rasterizer (`libvulkan_lvp.so`) instead of
RADV's `libvulkan_radeon.so`. The WoW64 layer check only looked in
`/usr/lib`, so a correctly installed multilib Fedora package reported
"not built". And `mvgal-info` left NVIDIA temperature and utilization at
their `-1` sentinel, because the proprietary driver exposes no hwmon
source — it now fills those fields from NVML, only where sysfs left them
empty, and never fabricates a value.

**v0.7.26 is a packaging release; runtime behaviour is unchanged.** The
RPM files list now always includes `mvgal-workload`, which the build
produces whenever CMake finds OpenCL — the previous conditional listing
made a Fedora build that found OpenCL fail in `%install` with an
"installed but unpackaged" error. The AppImage dependency self-check now
resolves `not found` entries and verifies against the staged `usr/lib`,
and the application icons are normalized to 256×256, which the Flatpak,
RPM and AppImage exports require.

**v0.7.25 fixed a defect that made the modules unloadable, and the
documented Secure Boot recovery could not have repaired them.** The
modules were compressed with `xz -9e`, producing a CRC64 xz stream that
the kernel's decoder rejects, so they failed at *decompression* — before
the signature was examined. Enrolling the MOK correctly still left the
system broken, and the journal pointed at a signature problem that was
not the cause. The release also closed the reload path (the daemon had
chowned systemd's `RuntimeDirectory`, and SIGHUP was handled by a branch
that did not exist), and fixed the tools' reporting: the Vulkan probe
called a staged manifest "ACTIVE", the D-Bus methods were registered
without `SD_BUS_VTABLE_UNPRIVILEGED` so sd-bus refused every non-root
call, and a multi-GPU strategy was accepted on a single-GPU host.

**v0.7.24 is an audit and validation-path release.** It fixes daemon device-node
access and D-Bus name conflict reporting, corrects PCIe/NUMA/class-code
discovery, repairs sysfs and kernel resource-lifetime issues, separates shared
system memory from dedicated VRAM, and fixes power caps that were silently
overwritten. It adds `mvgal-workload`, a host-staged OpenCL workload gate that
checks execution against a CPU reference and requires two distinct vendors.
The source changelog records a remaining clean-boot hardware check for a PCI
enumeration fix. See [[docs/STATUS|Status]] for implementation and validation
boundaries.

## ⚠️ Read Before Relying on a Feature

The following implementation limits were checked against the 0.7.27 source
tree on **2026-10-24**. Build presence and API declarations do not prove device
execution support.

| Area | Current boundary | Page |
|------|------------------|------|
| Vendor GPU submission and VRAM allocation | Native drivers own those paths; current vendor adapters report unsupported operations | [[docs/MEMORY\|Memory]] |
| Frame pacing | Frame-pacer code exists, but presence of the helper does not establish an active presentation hook | [[docs/STEAM_INTEGRATION\|Steam]] |
| Compatibility bridges | `compat/` contains integration sources; root CMake only adds them when a compat CMake definition exists | [[docs/STEAM_INTEGRATION\|Steam]] |

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
