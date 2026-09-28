---
tags: [mvgal, hardware, compatibility, reference]
aliases: [Hardware Compatibility, Hardware]
mvgal_version: "0.7.14"
mvgal_verified: 2026-09-28
mvgal_role: reference
mvgal_order: 12
---

# MVGAL Hardware Compatibility

> Source metadata is **0.7.14**; the source changelog documents releases through **0.7.14**. This page describes discovery and probed interfaces, not certification of GPU workload execution.

## GPU discovery

The kernel and userspace components recognize PCI vendor IDs for AMD (`0x1002`), NVIDIA (`0x10de`), Intel (`0x8086`), and Moore Threads (`0x1ed5`). The kernel module discovers devices read-only; it does not bind them away from the native vendor driver. The repository also contains an Adreno adapter stub whose operations report unsupported.

| Vendor | Native driver examples | What to verify |
|--------|-------------------------|----------------|
| AMD | `amdgpu` | Device appears in MVGAL output; inspect reported capability mask |
| NVIDIA | `nvidia` | Device appears in MVGAL output; inspect reported capability mask |
| Intel | `i915`, `xe` | Device appears in MVGAL output; inspect reported capability mask |
| Moore Threads | vendor driver | Device appears in MVGAL output; inspect reported capability mask |
| Qualcomm Adreno | platform-specific | Adapter is a stub; do not assume operational support |

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

For reproducible compatibility reports, include the GPU model and PCI ID, native driver and version, kernel version, MVGAL source/package version, reported capability mask, and the test result for discovery, allocation, submission, synchronization, and transfer separately.

## Hardware validation status

The source repository contains test scaffolding and vendor adapters. A build or passing synthetic/unit test is not physical-hardware certification. No blanket “production supported” matrix is claimed here; consult the source changelog, runtime probe output, and hardware-specific validation results.
