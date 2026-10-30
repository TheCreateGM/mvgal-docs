---
tags: [mvgal, hardware, compatibility, reference]
aliases: [Hardware Compatibility, Hardware]
mvgal_version: "0.7.31"
mvgal_verified: 2026-10-30
mvgal_role: reference
mvgal_order: 12
---

# MVGAL Hardware Compatibility

> Source metadata is **0.7.31**; the source changelog documents releases through **0.7.31**. This page describes discovery and probed interfaces, not certification of GPU workload execution.

## GPU discovery

The kernel and userspace components recognize PCI vendor IDs for AMD (`0x1002`), NVIDIA (`0x10de`), Intel (`0x8086`), and Moore Threads (`0x1ed5`). The kernel module discovers devices read-only; it does not bind them away from the native vendor driver. The repository also contains an Adreno adapter stub whose operations report unsupported.

The kernel PCI ID table (`kernel/mvgal_core.c`) includes entries for the Moore Threads MTT S30 (`0x1ED5:0x0102`), Intel UHD Graphics 770 (`0x8086:0x4680`), and other supported devices. The kernel matches display-class PCI devices in three classes: VGA (`0x0300`), 3D controllers (`0x0302`), and **Generic Display Controllers** (`0x0380`, `PCI_CLASS_DISPLAY_OTHER`) — the latter being the class Intel integrated GPUs enumerate as. Since v0.7.31, the kernel also **skips** display-class PCI devices whose native driver is not bound (no `pdev->driver`), so a blacklisted GPU like the MTT S30 is invisible to both kernel and userspace enumeration. This fixes the GPU-index mismatch where the kernel assigned an index to a device userspace could never see.

| Vendor | Native driver examples | What to verify |
|--------|-------------------------|----------------|
| AMD | `amdgpu` | Device appears in MVGAL output; inspect reported capability mask |
| NVIDIA | `nvidia` | Device appears in MVGAL output; inspect reported capability mask |
| Intel | `i915`, `xe` | Device appears in MVGAL output; inspect reported capability mask |
| Moore Threads | `mtgpu`, `mtgpu_drv` | Device appears in MVGAL output; inspect reported capability mask |
| Qualcomm Adreno | platform-specific | Adapter is a stub; do not assume operational support |

> [!warning] A GPU with no bound driver is silently skipped
> Since v0.7.31, both the kernel module (`mvgal_enumerate_gpus()`) and the
> userspace daemon (`DeviceRegistry::enumeratePciDevices()`) skip
> display-class PCI devices whose native driver is not bound — `pdev->driver`
> is `NULL` when the device is blacklisted or no driver is loaded. The device
> is still physically present on the PCI bus but is invisible to MVGAL
> enumeration. If a GPU is expected but absent, check for a blacklist entry in
> `/etc/modprobe.d/` and verify the driver is installed and not blocked.
> `mvgal-enum` and `mvgal list-gpus` additionally scan PCI and emit a warning
> naming any display-class GPU with known vendor IDs that has no DRM card
> node, so the omission is no longer silent.

## Runtime capability boundaries

The 0.7.12 source changelog says capabilities are set from runtime probes rather than inferred from vendor family. It explicitly states that `kernel-submit`, `kernel-vram`, `dmabuf-export`, and `wait-idle` are not set for any vendor in the current implementation. DMA-BUF import and buffer-object query capability bits may be reported when the relevant driver owns the PCI function; that does not prove a complete cross-vendor transfer path.

Do not interpret a supported kernel version, recognized PCI ID, compiled vendor adapter, or API declaration as evidence that a GPU combination can run workloads through MVGAL. Record the reported capability bits and test the exact operation.

## Inspect the system

```bash
lspci -nn | grep -Ei 'VGA|3D|Display'
ls -l /sys/class/drm/
lsmod | grep -E 'amdgpu|nvidia|i915|xe|mtgpu'
mvgal-info
mvgal-status --once
```

If a GPU appears in `lspci` but not in `mvgal-info`, its kernel driver may be
blacklisted or not installed. Since v0.7.31, `mvgal-enum` and `mvgal list-gpus`
emit a warning to stderr naming any display-class PCI GPU with a known vendor
ID (AMD, NVIDIA, Intel, Moore Threads) that has no DRM card node — check
`/etc/modprobe.d/` for blacklist entries and confirm the native driver is
installed and loadable.

For reproducible compatibility reports, include the GPU model and PCI ID, native driver and version, kernel version, MVGAL source/package version, reported capability mask, and the test result for discovery, allocation, submission, synchronization, and transfer separately.

## Hardware validation status

The source repository contains test scaffolding and vendor adapters. A build or passing synthetic/unit test is not physical-hardware certification. No blanket “production supported” matrix is claimed here; consult the source changelog, runtime probe output, and hardware-specific validation results.

The source tree's `docs/HARDWARE_VALIDATION_2026-10-25.md` records a bench run on a three-vendor host — AMD Navi 24, NVIDIA RTX 3050 and Intel Arc A380 — with ctest 27/27 (4.73 s) including `uapi_probe`, and 71/71 across the full suite. That is dated evidence for that host, not a blanket support matrix; the same document keeps synthetic, single-vendor and multi-vendor results separate.
