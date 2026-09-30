---
tags: [mvgal, install, guide]
aliases: [Installation, Install]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: guide
mvgal_order: 2
---

# MVGAL Installation Guide

> **Implementation status:** Source metadata is 0.7.16. The source changelog documents through 0.7.16. Treat design/API descriptions as available only where the relevant code path and runtime capability are verified; unsupported kernel submission and VRAM allocation return `-EOPNOTSUPP`.

**Source version:** 0.7.16 | **Updated:** September 2026

---

## Package installation

The source tree provides packaging definitions and this documentation repository includes built artifacts. Remote COPR publication may vary; verify repository availability and package version before following distribution-specific installation steps.

```bash
dnf info mvgal
# If your configured repository provides the package:
# pkexec dnf install mvgal
```

Build configurations exist for multiple distributions. A packaging target does not by itself establish publication or runtime validation.

Package contents and installation paths depend on the selected recipe. Inspect the package manifest before relying on a particular binary, layer manifest, service, or DKMS module being installed. The source tree's CLI target definitions are in `tools/CMakeLists.txt`; module and service recipes are under `packaging/` and `systemd/`.
---

## Start the Daemon

```bash
pkexec systemctl start mvgald
pkexec systemctl enable mvgald   # auto-start on boot
```

Verify:

```bash
mvgal-info          # list detected GPUs
mvgal-status        # real-time utilization
mvgal-compat --system   # check readiness
```

---

## Secure Boot (UEFI systems)

If Secure Boot is enabled, enroll the MVGAL signing key once:

```bash
mvgal-enroll-mok
```

Then **reboot** and complete enrollment in the MOK Manager (blue screen). See [SECURE_BOOT.md](SECURE_BOOT.md) for details.

If the kernel module is not loaded, `mvgal-status` reports **degraded userspace-only mode** with a MOK hint.

---

## Prerequisites

### Hardware

- **Minimum**: 2 GPUs from any supported vendor
- **Recommended**: GPUs on same PCIe root complex for P2P support
- **Supported vendors**: AMD (RDNA 1/2/3, GCN, APU), NVIDIA (Turing/Ampere/Ada/Pascal), Intel (Gen 9–12, Xe/Arc), Moore Threads (S60/S80/S2000)

### Vendor Drivers

Install vendor drivers **before** installing MVGAL:

```bash
# AMD (open-source, included in kernel) — nothing to install
# NVIDIA (proprietary)
pkexec dnf install akmod-nvidia  # Fedora
# Intel (open-source, included in kernel) — nothing to install
# Moore Threads — install mtgpu-drv from vendor
```

---

## Configuration

The daemon reads `/etc/mvgal/mvgal.conf`:

```ini
[core]
enabled = true
debug_level = info
gpu_count = 0                 # 0 = auto-detect
default_strategy = single     # see "Strategy names" below
enable_memory_migration = true
enable_dmabuf = true
enable_kernel_names = true
stats_interval = 1
enable_stats = true

[gpu_0]
type = auto                   # amd, nvidia, intel, auto
priority = 50
memory_limit_mb = 0           # 0 = unlimited
enabled = true

[gpu_1]
priority = 1
enabled = false               # disabled by default on single-GPU systems

[afr]
enable_sync = true
sync_timeout_ms = 16

[sfr]
split_mode = horizontal
split_ratio = 0.5

[hybrid]
primary_gpu = 0
fallback_gpu = 1
threshold_percent = 80

[custom]
script_path = /etc/mvgal/custom_strategy.lua   # shipped as a no-op stub

[cuda]
enabled = true
intercept_driver = true
intercept_runtime = true
enable_launch_intercept = true
track_memory = true

[direct3d]
enabled = true                # via Wine/Proton

[metal]
enabled = false

[webgpu]
enabled = true

[opencl]
enabled = true

[dri]
device_pattern = /dev/dri/card*
enable_prime = true

[power]
idle_timeout_ms = 5000
sustained_timeout_ms = 10000
park_timeout_ms = 30000
thermal_threshold = 85
critical_threshold = 95
power_curve = 0:30,25:50,50:70,75:90,100:100
enable_dvfs = true

[debug]
cuda_debug = false
d3d_debug = false
dump_calls = false
dump_file = /tmp/mvgal_dump.log

[network]
enabled = false
discovery_port = 49500
listen_addr = 0.0.0.0
heartbeat_interval_s = 5
peer_timeout_s = 30

[ai_scheduler]
model_path = /etc/mvgal/models/scheduler.onnx
enabled = false
inference_timeout_ms = 10
confidence_threshold = 0.6
```

**Strategy names.** Three vocabularies exist, and they are not the same set:

- **The C enum** `mvgal_distribution_strategy_t` (`include/mvgal/mvgal_types.h`) has **13 members** — 12 auto-numbered `0..11` plus `CUSTOM = 100`: `ROUND_ROBIN`, `AFR`, `SFR`, `AUTO`, `COMPUTE_OFFLOAD`, `HYBRID`, `SINGLE_GPU`, `TASK`, `AI_DRIVEN`, `RLD`, `REP`, `PPL`, `CUSTOM`.
- **`config/mvgal.conf`** documents 9 valid values for `default_strategy`: `single`, `round_robin`, `afr`, `sfr`, `hybrid`, `task`, `compute_offload`, `auto`, `custom`.
- **The pkexec helper** (`/usr/lib/mvgal/mvgal-pkexec-helper.sh`) accepts 11: `single`, `single_gpu`, `hybrid`, `task`, `afr`, `sfr`, `compute`, `compute_offload`, `round_robin`, `auto`, `custom`.

Only `single` is a pass-through safe default. Use `afr`, `sfr`, or `hybrid` only after
`mvgal-compat` reports `COMPAT_SUPPORTED` for the application. See [STRATEGIES.md](STRATEGIES.md).

> **Note on `[ai_scheduler] model_path`:** no package creates `/etc/mvgal/models/`. Since v0.7.14 `mvgal_ai_model_load()` validates the path with `stat()` and returns `NULL` with a diagnostic naming what it found, instead of returning a valid handle for any non-empty string. The daemon reads `$MVGAL_AI_MODEL` if set, otherwise this value, once at startup, and logs plainly that its distribution logic is a built-in heuristic rather than ONNX Runtime inference.

Edit with:

```bash
pkexec nano /etc/mvgal/mvgal.conf
# or
mvgal-config   # CLI configuration tool
```

---

## Build from Source

See [BUILD.md](BUILD.md) for the full build guide (CMake, Meson, Zig, DKMS).

Quick CMake build:

```bash
git clone https://github.com/TheCreateGM/mvgal.git
cd mvgal
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
pkexec cmake --install build
```

---

## Post-Installation

### Verify Installation

```bash
lsmod | grep mvgal            # kernel modules loaded
ls -l /dev/mvgal*             # device node
systemctl status mvgald       # daemon status
mvgal-info                    # GPU info
mvgal-status                  # real-time utilization
```

### Enable Vulkan interception layer

The layer is registered system-wide at
`/usr/share/vulkan/implicit_layer.d/VK_LAYER_MVGAL.json` — no action needed. It is
registered implicitly because it only intercepts and never stands in for a
`VkPhysicalDevice`. Verify with:

```bash
vulkaninfo | grep -i mvgal
```

Toggle it with `MVGAL_VULKAN_ENABLE=1` / `MVGAL_VULKAN_DISABLE=1`, or read the
manifest at `/usr/share/vulkan/explicit_layer.d/` if you move it.

### Enable the Vulkan ICD (opt-in)

The **ICD** is a separate thing from the layer, and as of v0.7.14 it is **not registered
globally**. It used to be installed into `share/vulkan/icd.d/`, so every Vulkan application
on the system loaded it — and since v0.7.12 it reports *zero* physical devices by design.
With no device handle the loader cannot build a per-device dispatch table, so it printed a
conformancy error on every startup.

The manifest now lives at `/usr/share/vulkan/mvgal/mvgal_icd.json` and is applied only on
request:

```bash
source /usr/share/mvgal/scripts/mvgal-vulkan-env.sh
# or, equivalently, for a single run:
MVGAL_ICD_JSON=/usr/share/vulkan/mvgal/mvgal_icd.json vulkaninfo
```

The script is installed at `/usr/share/mvgal/scripts/mvgal-vulkan-env.sh` (v0.7.14 installs
it for the first time). The `library_path` in the manifest is absolute, so it no longer
depends on the loader's `dlopen` search order.

Upgrades remove a stale manifest from `icd.d` **only** when it is recognisably MVGAL's.

### Enable OpenCL ICD

`libmvgal_opencl.so` is a real aggregating ICD: it scans `/etc/OpenCL/vendors/`, skips
itself, and delegates to every peer it finds. The manifest is at
`/etc/OpenCL/vendors/mvgal.icd`.

Since v0.7.14, if **no peer** OpenCL runtime is installed at first install time, the manifest
is moved aside to `mvgal.icd.disabled` and the install message names the package that
provides a peer and the exact command to re-enable it. With nothing to aggregate, leaving it
registered only produced zero platforms and no explanation. Erasing the MVGAL package
re-enables it if a peer has since appeared.

Verify with:

```bash
clinfo | grep -i mvgal
```

### Steam / Proton

See [STEAM_INTEGRATION.md](STEAM_INTEGRATION.md). Add to Steam launch options:

```
ENABLE_MVGAL=1 %command%
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `mvgal-status` shows degraded mode | Kernel module not loaded — enroll MOK (see [SECURE_BOOT.md](SECURE_BOOT.md)) or `pkexec modprobe mvgal` |
| Daemon won't start | `journalctl -u mvgald -f` for logs |
| No GPUs detected | `lspci \| grep -i vga`; check `/etc/mvgal/mvgal.conf` `enabled` flags |
| Vulkan app crashes | Update to v0.7.7+ (device dispatch fix); check `vulkaninfo` |
| `vulkaninfo` reports the ICD is not conformant | The ICD is opt-in since v0.7.14. Do not register it globally — source `mvgal-vulkan-env.sh` per-run instead. |
| `clinfo` reports zero platforms | Expected when no peer OpenCL runtime is installed; the manifest is parked as `mvgal.icd.disabled`. Install a vendor OpenCL runtime. |
| Daemon socket exists but you cannot connect | v0.7.14 chowns it to group `mvgal` (falling back to `video`). Run `mvgal-compat` — it prints the socket's real owner, mode, and your uid. |

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for the full guide.

---

## Uninstall

```bash
# Stop daemon
pkexec systemctl stop mvgald
pkexec systemctl disable mvgald

# Remove packages
pkexec dnf remove mvgal

# Remove configuration
pkexec rm -rf /etc/mvgal/
```
