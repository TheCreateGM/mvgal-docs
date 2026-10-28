---
tags: [mvgal, install, guide]
aliases: [Installation, Install]
mvgal_version: "0.7.30"
mvgal_verified: 2026-10-28
mvgal_role: guide
mvgal_order: 2
---

# MVGAL Installation Guide

> **Implementation status:** Source metadata is 0.7.30. The source changelog documents through 0.7.30. Treat design/API descriptions as available only where the relevant code path and runtime capability are verified; unsupported kernel submission and VRAM allocation return `-EOPNOTSUPP`.

**Source version:** 0.7.30 | **Updated:** October 2026

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

**Check that the daemon is actually reachable by your user.** The package adds
you to the `mvgal` group, but group membership only reaches a new session:

Since v0.7.28 the RPM also ships a `systemd-sysusers` fragment
(`/usr/lib/sysusers.d/mvgal.conf`, containing `g mvgal - -`), so the group is
declared before dependency resolution. Earlier packages failed `dnf install`
with `nothing provides group(mvgal)`: rpmbuild auto-generates
`Requires: group(mvgal)` from the group-owned ghost key file, but the group
existed only in `%post`'s `groupadd`, which runs *after* dependency
resolution. The `%post` `groupadd` remains as the fallback for systems
without the sysusers trigger.

```bash
ls -l /run/mvgal/mvgal.sock      # expect: srw-rw---- root:mvgal
id -nG | tr ' ' '\n' | grep -x mvgal
```

The socket must be owned by `mvgal`, not `root`. If it shows `root:root` the
daemon could not hand it over — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) §
Daemon socket permissions. If the group is missing from your session but the
socket is correct, log out and back in.

---

## Secure Boot (UEFI systems)

If Secure Boot is enabled, enroll the MVGAL signing key once:

```bash
mvgal-enroll-mok
```

Then **reboot** and complete enrollment in the MOK Manager (blue screen). See [SECURE_BOOT.md](SECURE_BOOT.md) for details.

If the kernel module is not loaded, `mvgal-status` reports **degraded userspace-only mode** with a MOK hint.

As of v0.7.21 the daemon also checks this itself at startup and prints a banner
to the journal when Secure Boot is on but the key is not enrolled, so the cause
is visible without running a diagnostic:

```bash
journalctl -u mvgald -b | grep -A6 'Secure Boot is enabled'
```

`mvgal status` and `mvgal-status --once` both exit `1` in this state (degraded);
exit `2` means the daemon itself is not running (v0.7.29 three-tier scheme);
see [SECURE_BOOT.md](SECURE_BOOT.md) § Degraded Mode.

---

### The canonical systemd unit name

The unit is `mvgal-daemon.service`, with `mvgal.service` and
`mvgald.service` as aliases. `systemctl` accepts all three, but
`journalctl` does **not** resolve aliases:

```bash
journalctl -u mvgald              # no entries
journalctl -u mvgal-daemon.service # the full log
```

Use `mvgal-daemon.service` when reading the journal. The MVGAL tools
resolve the real name with `systemctl show -p Id`, so they work either way.

`systemctl reload mvgal-daemon.service` re-reads the configuration since
v0.7.25. Before that, SIGHUP was installed but the handler ignored it, so
a reload signalled the daemon and nothing happened while still reporting
success.

### The OpenCL ICD is registered by default

Since v0.7.25 `/etc/OpenCL/vendors/mvgal.icd` is installed **active**.
Earlier releases parked it as `mvgal.icd.disabled` when no other vendor
runtime happened to be installed at that moment — a snapshot that went
stale as soon as a vendor runtime was installed later, leaving MVGAL's
OpenCL interception out of every application's path while the tools still
reported OpenCL results.

The decision now lives in a script you can re-run at any time:

```bash
/usr/lib/mvgal/mvgal-opencl-icd.sh --status
sudo /usr/lib/mvgal/mvgal-opencl-icd.sh          # re-evaluate and register
sudo /usr/lib/mvgal/mvgal-opencl-icd.sh --force-unregister
```

Run the plain form after installing a vendor runtime (for example
`intel-compute-runtime`) and it registers the ICD if there is now
something to aggregate.

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
listen_addr = 127.0.0.1
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

### Upgrading: what happens to your configuration

`mvgal.conf` is marked `%config(noreplace)`, so rpm never overwrites your copy
silently. Historically that meant something worse: when a new release changed
the schema, rpm installed the new default file and moved yours to
`mvgal.conf.rpmsave`, leaving the *new defaults active* and your settings only in
that backup. Users read this as the upgrade resetting their configuration.

**Since v0.7.21 the package merges your file back** during `%post`:

- Values you had set are restored per **section and key**, so a setting in
  `[gpu_0]` is never confused with the same key name in `[gpu_1]` or `[core]`.
- Keys that only your version had — for example a `power_curve_profile` dropped
  by a later release — are re-added to their own section.
- Sections the new release removed entirely are appended rather than dropped.
- Keys the new release introduced are left at their new defaults.

The release's own default is preserved next to the result as
`/etc/mvgal/mvgal.conf.mvgal-default`, so you can diff the two at any time:

```bash
diff /etc/mvgal/mvgal.conf.mvgal-default /etc/mvgal/mvgal.conf
```

The merge is keyed on section **and** key name deliberately. A key name alone is
ambiguous — `priority` appears in both `[gpu_0]` and `[gpu_1]`, and `enabled`
appears in five sections — and a key that still exists but whose default
changed would be skipped entirely, which is the common case and exactly the one
that loses a setting like `psu_capacity_watts`.

The helper used for this is `/usr/lib/mvgal/mvgal-merge-config.sh`. It is also
runnable by hand if you want to merge an old file yourself:

```bash
sudo /usr/lib/mvgal/mvgal-merge-config.sh /etc/mvgal/mvgal.conf /path/to/old.conf
```

> **Note:** merging restores the values you had. It cannot know whether a
> behaviour you relied on changed meaning between releases; after a major schema
> change, read the changelog rather than assuming the file is authoritative.

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

> [!important] Sourcing this script no longer disables the vendor renderer (v0.7.30)
> Prior to v0.7.30 the script set `VK_ICD_FILENAMES` / `VK_DRIVER_FILES` to *only*
> `/usr/share/vulkan/mvgal/mvgal_icd.json` (with `MVGAL_ICD_ONLY=1`). That ICD reports
> zero physical devices when the kernel module is absent, so every Vulkan application
> broke after sourcing the script. The script now defaults to `MVGAL_ICD_ONLY=0`, which
> leaves the loaded vendor ICDs in place and only *adds* the MVGAL ICD on request. Set
> `MVGAL_ICD_ONLY=1` only when the kernel module is loaded and you want the MVGAL
> aggregating ICD to be the sole discoverable device. The script also normalises a
> duplicate `MVGAL_VULKAN_ENABLE` export, drops a stale `VK_LAYER_PATH`, and
> `MVGAL_PREFIX` defaults to `/usr`.

Upgrades remove a stale manifest from `icd.d` **only** when it is recognisably MVGAL's.

Check which of the two you actually have:

```bash
mvgal-info | grep -i vulkan
```

```
Vulkan layer registered  : yes (interception layer only; adds no GPU)
Vulkan aggregated ICD    : disabled by default (opt-in via /usr/share/mvgal/scripts/mvgal-vulkan-env.sh)
```

The layer and the ICD are different things and are now reported separately
(v0.7.22). The layer ships globally and only intercepts calls; it adds no device.
The aggregated ICD is the thing that would expose an MVGAL `VkPhysicalDevice`,
and it is off by default for the conformancy reason above. An earlier single
`Vulkan layer registered: yes` line was easy to read as "Vulkan aggregation is
active" when no aggregated device existed.

### Enable OpenCL ICD

`libmvgal_opencl.so` is a real aggregating ICD: it scans `/etc/OpenCL/vendors/`, skips
itself, and delegates to every peer it finds. The manifest is at
`/etc/OpenCL/vendors/mvgal.icd`.

Since v0.7.25, if **no peer** OpenCL runtime is installed at first install time, the manifest
is parked outside the loader's scan directory at `/usr/lib/mvgal/mvgal.icd.parked`
and the install message names the package that provides a peer and the exact command to
re-enable it. The decision can be re-evaluated at any time with
`/usr/lib/mvgal/mvgal-opencl-icd.sh`. With nothing to aggregate, leaving it registered only
produced zero platforms and no explanation. Erasing the MVGAL package re-registers it
automatically if a peer has since appeared.

Verify with:

```bash
clinfo | grep -i mvgal
```

### Steam / Proton

See [STEAM_INTEGRATION.md](STEAM_INTEGRATION.md). Add to Steam launch options:

```
MVGAL_VULKAN_ENABLE=1 %command%
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
| `clinfo` reports zero platforms | Expected when no peer OpenCL runtime is installed; the manifest is parked at `/usr/lib/mvgal/mvgal.icd.parked`. Install a vendor OpenCL runtime, then run `/usr/lib/mvgal/mvgal-opencl-icd.sh`. |
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
