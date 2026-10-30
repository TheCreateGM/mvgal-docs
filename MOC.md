---
tags: [mvgal, moc, index]
aliases: [MOC, Documentation Index, Home]
cssclasses: [moc]
mvgal_version: "0.7.31"
mvgal_verified: 2026-10-30
mvgal_role: index
---

# MVGAL Documentation — Map of Content

> [!info] Source version
> **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.
> Source version **0.7.31**; the source changelog documents releases through **0.7.31**.
> Core architecture and status pages were reconciled against the source tree on **2026-10-30**.

Cross-vendor GPU discovery and integration components for Linux; operational support is capability-dependent.

## 🚀 Start Here

| Note | Purpose |
|------|---------|
| [[docs/QUICKSTART\|Quick Start]] | Get MVGAL running in 5 minutes |
| [[docs/INSTALL\|Installation]] | Full installation guide (COPR, Secure Boot, config) |
| [[docs/SECURE_BOOT\|Secure Boot & MOK]] | MOK enrollment for Secure Boot systems |
| [[docs/CHANGELOG\|Changelog]] | Release history through v0.7.31 |
| [[docs/STATUS\|Project Status]] | What is verified, and what is not |

## 📖 Reference

| Note | Purpose |
|------|---------|
| [[docs/ARCHITECTURE\|Architecture]] | System architecture overview |
| [[docs/CODEBASE\|Codebase Map]] | Directory map and subsystem ownership |
| [[docs/DESIGN\|Design Document]] | Design decisions, and which ones shipped |
| [[docs/API\|API Reference]] | Public C API reference (31 headers) |
| [[docs/MEMORY\|Memory Management]] | Transfer paths, allocation, and what is not implemented |
| [[docs/STRATEGIES\|Scheduling Strategies]] | The 13 public strategy identifiers |
| [[docs/POWER_MANAGEMENT\|Power Management]] | Power, DVFS, thermal |
| [[docs/HARDWARE_COMPATIBILITY\|Hardware Compatibility]] | Supported GPUs and platforms |
| [[docs/BUILD\|Build Guide]] | Build from source (CMake, Meson, Cargo, DKMS) |
| [[docs/TROUBLESHOOTING\|Troubleshooting]] | Common issues and fixes |
| [[docs/STEAM_INTEGRATION\|Steam/Proton]] | Steam integration, and what is dormant |

## 🔍 What's New in 0.7.31

> [!tip]
> The summary below follows the source changelog. For full details see [[docs/CHANGELOG|Changelog]].

**v0.7.31 is a field-report-driven correctness release** addressing the 0.7.30 test report on a single-GPU Secure Boot host (Fedora 43, kernel 7.2.13-200.fc44.x86_64, Intel UHD Graphics 770, plus a blacklisted MTT S30). COPR build #11229933 succeeded on `fedora-43-x86_64`. Key fixes:

- **C1: GPU index mismatch corrected** — the kernel module now includes `PCI_CLASS_DISPLAY_OTHER` (0x0380) so Intel integrated GPUs are found alongside discrete cards, and skips display-class PCI devices whose native driver is not bound (blacklisted MTT S30), so kernel and userspace enumeration agree on which GPUs exist and their indices. The Intel PCI ID `0x4680` comment is corrected from "DG2" to "UHD Graphics 770 (Alder Lake)".
- **C2: MTT backend compile guard fixed** — `mvgal_mtt.c` now checks `MVGAL_FULL_STACK` (the real compile-time guard from `Kbuild` ccflags) instead of the non-existent `CONFIG_MVGal_MTT` typo, so MTT GPUs are probed when the vendor module is built. The `find_module()` calls — removed from the kernel symbol table in 7.x — are replaced by a `/proc/modules` read.
- **C3: udev permissions corrected** — udev rules and the pkexec helper now set `GROUP="mvgal"` and `MODE="0660"` (were `GROUP="video"` and `MODE="0666"`), so users in the `mvgal` group can access `/dev/mvgal0` and `/dev/mvgal_ntsync`.
- **H1: Blacklisted GPU visibility** — `mvgal-enum` and `mvgal list-gpus` now scan PCI for display-class GPUs with no DRM node and warn about present-but-unusable devices instead of silently omitting them.
- **H2: Start degraded mode check** — `mvgal start` now checks for `/sys/module/mvgal` after launching the daemon and prints a degraded-mode warning if the kernel module is absent or failed to load.

## 🔍 What's New in 0.7.30

> [!tip]
> The summary below follows the source changelog. For full details see [[docs/CHANGELOG|Changelog]].

**v0.7.30 is a field-report-driven correctness and packaging release** addressing the 0.7.30 test report on a single-GPU Secure Boot host (Fedora 44, kernel 7.2.12-200.fc44.x86_64, Intel UHD Graphics 770). Multi-GPU aggregation could not be exercised (single GPU), and the kernel module path stays unavailable under Secure Boot until the MOK is enrolled (see [SECURE_BOOT.md](docs/SECURE_BOOT.md)). COPR build #11217288 succeeded on all 18 enabled chroots. Key fixes:

- **Vulkan ICD opt-in no longer breaks all Vulkan** — `mvgal-vulkan-env.sh` no longer forces `VK_ICD_FILENAMES`/`VK_DRIVER_FILES` to *only* the MVGAL ICD (which reports zero devices when the kernel module is absent); `MVGAL_ICD_ONLY=0` by default preserves vendor ICDs, the duplicate `MVGAL_VULKAN_ENABLE` export and stale `VK_LAYER_PATH` are normalised, and `MVGAL_PREFIX` defaults to `/usr`.
- **OpenCL ICD steps aside when the kernel module is absent** — `libmvgal_opencl.so` reports 0 platforms instead of a half-working platform whose context creation fails.
- **GUI dashboard status cards refresh on startup** — `MainWindow` auto-refreshes via a single-shot `QTimer` so the cards no longer stay "Checking…".
- **Benchmark caveats everywhere** — `mvgal-bench compute` and other single-suite paths now print the "What is actually measured" caveat block in the same form as `all`, so host-proxy vs. GPU figures are unambiguous.
- **Standardised exit codes** — usage/error paths exit `2` across tools; the contract is documented in the man pages.
- **Config log lines are DEBUG-only** — gated behind `--verbose`, so unstripped CLI output no longer falls through to stderr before `mvgal_log_init`.
- **Install-time cleanup and metadata** — `%post` removes leftover `/etc/OpenCL/vendors/mvgal.icd.disabled`; man pages were added for `mvgal-gui`, `mvgal-dashboard`, `mvgal-load`, `mvgal-unload`, `mvgal-workload`, `mvgal-probe`; and `mvgal-daemon.preset` (disabled) documents that `%post` enables the unit on first install.

## 🔍 What's New in 0.7.29

> [!tip]
> The summary below follows the source changelog. For full details see [[docs/CHANGELOG|Changelog]].

**v0.7.29 is a test-report-driven correctness release** addressing 15 issues from the v0.7.28 field validation on a single-GPU Secure Boot host (Fedora 44, kernel 7.2.11, Intel UHD 770). Key fixes:

- **Vulkan layer env var corrected** — `mvgal --help` and all Steam/compat scripts now use `MVGAL_VULKAN_ENABLE=1` instead of the wrong `VK_LAYER_MVGAL=1` / `ENABLE_MVGAL=1` that the manifest never checked.
- **`/etc/mvgal` security hardened** — config dir is now explicitly `0755 root:root` in the RPM (was `0775 group:mvgal`), closing a privilege-escalation path via `custom_strategy.lua`.
- **Three-tier status exit codes** — `mvgal status` and `mvgal-status` now return `0` (healthy), `1` (degraded — module absent), or `2` (daemon down), replacing the always-`1` behaviour on Secure Boot machines.
- **Benchmark commands fixed** — `mvgal benchmark`/`bench-*` now forward `mvgal-bench` output instead of suppressing it and printing "No workload data".
- **set-strategy validation** — multi-GPU strategies are refused on single-GPU machines, matching `mvgal-config`.
- **Config path validation** — `-c/--config` rejects paths outside `/etc/mvgal/`, mirroring the pkexec helper's safety check.
- **OpenCL ICD park** — parked manifest moved to `/usr/lib/mvgal/mvgal.icd.parked`, out of the loader's scan directory.
- **Workload device de-duplication** — `mvgal-workload` skips the MVGAL aggregating ICD platform.
- **Probe error demotion** — `mvgal-probe` logs `/dev/mvgal0` open failure as a notice, not a scary error.
- **`listen_addr` default** — changed to `127.0.0.1` (loopback only).

**v0.7.28 is a correctness and packaging release, validated on the physical
three-vendor bench (AMD Navi 24 + NVIDIA RTX 3050 + Intel Arc A380).** The
CUDA shim now reports the native driver's device count instead of the MVGAL
GPU count, and maps CUDA ordinals to MVGAL GPUs by PCI BDF instead of
modulo — the old mapping attributed CUDA device 0 (RTX 3050) to MVGAL GPU 0
(Intel Arc). The `-1` sentinel is rejected before context creation,
allocation and launch (the old `mvgal_gpu < gpu_count` guard was true for
`-1`), kernel launches are restricted to eligible GPUs, and
`MVGAL_CUDA_DEBUG=1` now raises the log level so the attribution line is
visible. A new `test_cuda_multidevice` integration harness brings ctest to
27/27 (4.73 s). The release also adds a Windows cross-compilation packaging
pipeline (NSIS and WiX installers built from `Jenkinsfile.windows`), and the
RPM ships a `systemd-sysusers` fragment (`g mvgal - -`) so the `mvgal`
group is declared before dependency resolution — fixing `dnf install`
failing with `nothing provides group(mvgal)`. In the source documentation,
SPEC_COMPLIANCE findings 4 and 5 are resolved and finding 6 has its first
physical evidence.

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

The following implementation limits were checked against the 0.7.31 source
tree on **2026-10-30**. Build presence and API declarations do not prove device
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
