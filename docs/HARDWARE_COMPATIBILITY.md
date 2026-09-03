# MVGAL Hardware Compatibility

> **Version**: 0.7.3  
> **Last Updated**: 2026-06-06

---

## Table of Contents

1. [Supported GPU Vendors](#supported-gpu-vendors)
2. [Feature Matrix](#feature-matrix)
3. [GPU Architecture Support](#gpu-architecture-support)
4. [Kernel Version Requirements](#kernel-version-requirements)
5. [VRAM & Bandwidth Recommendations](#vram--bandwidth-recommendations)
6. [Vulkan Version Requirements](#vulkan-version-requirements)
7. [Platform Support](#platform-support)

---

## Supported GPU Vendors

MVGAL supports four GPU vendors through the vendor ops interface defined in
`kernel/vendors/`. Each vendor provides a `mvgal_vendor_ops` struct that
implements device initialization, memory management, and submission
functions.

| Vendor | PCI VID | Kernel Module | Vendor Ops | Status |
|--------|---------|---------------|------------|--------|
| NVIDIA | `0x10DE` | `nvidia` + nouveau | `mvgal_nvidia_ops` | Production |
| AMD | `0x1002` | `amdgpu` | `mvgal_amd_ops` | Production |
| Intel | `0x8086` | `i915` | `mvgal_intel_ops` | Production |
| Moore Threads | `0x1ED5` | `mtgpu` | `mvgal_mtt_ops` | Beta |

### NVIDIA

- **Driver**: Proprietary `nvidia` (recommended), open `nvidia-open` (Turing+),
  `nouveau` (community, limited reclocking)
- **Vendor Ops File**: `kernel/vendors/mvgal_nvidia.c`
- **Capabilities**: Full VRAM management via NVML, NVLink peer detection,
  MIG partition discovery (A100/H100)
- **DMA-BUF**: Supported via `nvidia-drm` (≥ 515.48.07)

### AMD

- **Driver**: `amdgpu` (in-kernel, upstream)
- **Vendor Ops File**: `kernel/vendors/mvgal_amd.c`
- **Capabilities**: Full VRAM management, XGMI peer detection (RX 7000 series),
  ROCm compatibility layer
- **DMA-BUF**: Native via `amdgpu` DRM driver

### Intel

- **Driver**: `i915` (in-kernel, upstream)
- **Vendor Ops File**: `kernel/vendors/mvgal_intel.c`
- **Capabilities**: VRAM management for discrete (DG2/Alchemist+), integrated
  GPU sharing via i915
- **DMA-BUF**: Native via `i915` DRM driver

### Moore Threads (MTT)

- **Driver**: `mtgpu` (proprietary, vendor-provided)
- **Vendor Ops File**: `kernel/vendors/mvgal_mtt.c`
- **Device IDs**: MTT S2000 (`0x4000`), S3000
- **Capabilities**: VRAM management, limited peer-to-peer
- **Status**: Beta — P2P and MIG equivalents under development

---

## Feature Matrix

| Feature | NVIDIA | AMD | Intel (dGPU) | Intel (iGPU) | MTT |
|---------|:------:|:---:|:------------:|:------------:|:---:|
| VRAM Discovery | ✓ | ✓ | ✓ | N/A | ✓ |
| P2P DMA-BUF | ✓ | ✓ | ✓ | ✓* | partial |
| NVLink/XGMI | ✓ | ✓ | — | — | — |
| MIG/SRU Partition | ✓ | — | — | — | planned |
| Power Management | ✓ (NVML) | ✓ (hwmon) | ✓ (hwmon) | ✓ | ✓ |
| GPU Metrics | ✓ (NVML) | ✓ (fdinfo) | ✓ (fdinfo) | ✓ | manual |
| Reclocking | ✓ | ✓ | ✓ | N/A | partial |
| Resizable BAR | ✓ | ✓ | ✓ | ✓ | ✓ |
| PCIe Atomics | ✓ | ✓ | ✓ | ✓ | ✓ |

> \* Intel integrated GPU P2P works via shared system memory (no physical P2P
>   over PCIe needed).

---

## GPU Architecture Support

### NVIDIA

| Architecture | Generation | Compute Cap. | Vulkan | ML Perf | Status |
|-------------|------------|:------------:|:------:|:-------:|:------:|
| Tesla | V100 | 7.0 | 1.1 | High | Supported |
| Turing | T4/RTX 20xx | 7.5 | 1.2 | High | Supported |
| Ampere | A100/RTX 30xx | 8.0 | 1.3 | Very High | Supported |
| Hopper | H100 | 9.0 | 1.3 | Very High | Supported |
| Ada Lovelace | RTX 40xx | 8.9 | 1.3 | High | Supported |
| Blackwell | B100/B200 | 10.0 | 1.4 | Very High | Supported |
| Pre-Tesla | GTX 9xx/10xx | ≤5.x | 1.0–1.1 | Low | Limited |

### AMD

| Architecture | GPUs | ROCm | Vulkan | Status |
|-------------|------|:----:|:------:|:------:|
| GCN 4/5 (Polaris/Vega) | RX 4xx–5xx, Vega | 5.x | 1.1–1.2 | Supported |
| RDNA 1 | RX 5000 | N/A | 1.2 | Supported |
| RDNA 2 | RX 6000 | N/A | 1.3 | Supported |
| RDNA 3 | RX 7000 | 6.x | 1.3 | Supported |
| CDNA 2 | MI200 | 5.x | — | Supported |
| CDNA 3 | MI300 | 6.x | — | Supported |
| Pre-GCN | HD 7000–8000 | — | 1.0 | Limited |

### Intel

| Architecture | GPUs | Vulkan | Status |
|-------------|------|:------:|:------:|
| Xe-LP (Tiger Lake) | Integrated | 1.2 | Supported |
| Xe-HPG (DG2/Alchemist) | Arc A3/A5/A7 | 1.3 | Supported |
| Xe-HPG (Battlemage) | Arc B-series | 1.3 | Supported |
| Xe² (Celestial) | Next-gen | 1.4 (planned) | Planned |
| Pre-Xe | UHD 6xx | 1.0–1.1 | Limited |

### Moore Threads

| GPU | Vulkan | VRAM | Status |
|-----|:------:|:----:|:------:|
| MTT S2000 | 1.2 | 32 GB | Beta |
| MTT S3000 | 1.3 | 48 GB | Beta |

---

## Kernel Version Requirements

| Requirement | Minimum | Recommended |
|-------------|:-------:|:-----------:|
| LTS Branch | 5.15 LTS | 6.6 LTS |
| Stable Branch | 6.1 | 6.8+ |
| DRM/KMS | 5.10+ | 6.6+ |
| DMA-BUF | 5.6+ | 6.0+ |
| NVLink support | 5.8+ | 6.0+ |
| MIG discovery | 5.16+ | 6.4+ |
| amdgpu P2P | 5.18+ | 6.6+ |
| i915 DG2/Alchemist | 6.0+ | 6.6+ |

**Note**: MVGAL kernel module is verified on Fedora kernel 7.0.10.
DKMS builds are supported for custom kernels.

---

## VRAM & Bandwidth Recommendations

### Per Use Case

| Use Case | Min VRAM | Recommended VRAM | Min Bandwidth | Recommended |
|----------|:--------:|:----------------:|:-------------:|:-----------:|
| 1080p Gaming | 4 GB | 8 GB | 200 GB/s | 400 GB/s |
| 1440p Gaming | 6 GB | 12 GB | 300 GB/s | 600 GB/s |
| 4K Gaming | 8 GB | 16 GB | 500 GB/s | 800 GB/s |
| VR (per eye) | 4 GB | 8 GB ea. | 400 GB/s | 800 GB/s |
| ML Inference | 8 GB | 24 GB | 500 GB/s | 900 GB/s |
| ML Training | 16 GB | 80 GB | 900 GB/s | 2 TB/s |
| Video Transcoding | 2 GB | 4 GB | 100 GB/s | 200 GB/s |
| Multi-GPU Compositing | 4 GB ea. | 8 GB ea. | 200 GB/s | 400 GB/s |

### Multi-GPU Topology

| Topology | Aggregate Bandwidth | Latency | Recommended Strategies |
|----------|:------------------:|:-------:|----------------------|
| NVLink (NVIDIA) | 600 GB/s (A100) | ~200 ns | GA, RLD, PPL |
| XGMI (AMD) | 448 GB/s (MI300) | ~300 ns | GA, RLD, PPL |
| PCIe 5.0 x16 | 64 GB/s | ~1 µs | RR, LL, RLD |
| PCIe 4.0 x16 | 32 GB/s | ~1.5 µs | RR, LL, BP |
| PCIe 3.0 x16 | 16 GB/s | ~3 µs | AFF, BP |

---

## Vulkan Version Requirements

### Per GPU Family

| Family | Vulkan Min | Vulkan Recommended | Extensions Required |
|--------|:----------:|:------------------:|---------------------|
| NVIDIA Ampere+ | 1.2 | 1.3 | `VK_KHR_timeline_semaphore`, `VK_KHR_buffer_device_address` |
| NVIDIA Turing | 1.1 | 1.2 | `VK_KHR_external_memory_fd` |
| AMD RDNA 2+ | 1.2 | 1.3 | `VK_KHR_synchronization2` |
| AMD GCN | 1.0 | 1.1 | `VK_KHR_external_memory_fd` |
| Intel Xe-HPG+ | 1.2 | 1.3 | `VK_KHR_timeline_semaphore` |
| Intel Xe-LP | 1.1 | 1.2 | `VK_EXT_external_memory_dma_buf` |
| MTT S2000 | 1.1 | 1.2 | `VK_KHR_external_memory_fd` |

### MVGAL Vulkan Extensions

MVGAL exposes vendor extensions through `VkPhysicalDeviceMVGAL` properties.
See `docs/ARCHITECTURE.md §7—Intercept Layer` for extension details.

---

## Platform Support

| Platform | Status | Notes |
|----------|:------:|-------|
| Fedora 40+ | Tier 1 | Primary development target |
| RHEL 9 / Rocky 9 | Tier 1 | Kernel 5.14+ with DKMS |
| Ubuntu 22.04 LTS | Tier 2 | Requires DKMS or PPA |
| Ubuntu 24.04 LTS | Tier 2 | Kernel 6.8+, native DKMS |
| openSUSE Tumbleweed | Tier 3 | Rolling kernel, DKMS |
| SteamOS 3.x | Tier 3 | Deck-specific tuning (WIP) |

**Tier definitions**:
- **Tier 1**: CI-tested, official packages in COPR, full support
- **Tier 2**: Community packages, automated build tests
- **Tier 3**: Manual build, best-effort support

---

*For installation instructions, see `docs/TROUBLESHOOTING.md`.  
For kernel module build, see `docs/KERNEL_MODULE.md`.*
