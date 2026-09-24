---
tags: [mvgal, changelog, reference]
aliases: [Changelog, Release Notes]
---

# MVGAL Changelog

**Version:** 0.7.8 | **Updated:** September 2026

All notable changes to MVGAL (Multi-Vendor GPU Aggregation Layer) are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [v0.7.8] — 2026-09-22

### Fixed
- **HIGH-1:** `mvgal-enroll-mok` no longer reports false success — `mokutil --import` is now fed the password via stdin (the `-p` flag is rejected by mokutil 0.7.2) and the pending MOK list is verified with `mokutil --list-new` before claiming enrollment.
- **HIGH-2:** Daemon drops capabilities after init — `mvgald` now clears effective/permitted/inheritable sets and prunes the bounding set to `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO`; the systemd unit adds `CapabilityBoundingSet`/`AmbientCapabilities`/`NoNewPrivileges`.
- **HIGH-3:** `mvgal-status` reports degraded mode — when the `mvgal` kernel module is not loaded it prints `Kernel Module: NOT LOADED (degraded userspace-only mode)` with a MOK enrollment hint, and the hard-coded `Load Balance: 100.00%` is replaced by a real estimate (or `N/A` when fewer than 2 enabled GPUs / no workload data).
- **HIGH-4:** Vulkan ICD reports a real driver version — `apiVersion`/`driverVersion` are set from the MVGAL version macros in the daemon-GPU path and copied in `mvgal_vkGetPhysicalDeviceProperties` (previously `0.0.0`).
- **MED-1:** `mvgal-info` DRM fallback reads the `enabled` state from `/etc/mvgal/mvgal.conf` instead of hard-coding every GPU as enabled.
- **MED-2:** `mvgal-bench` multi-GPU scaling figures are labeled as theoretical estimates, not measured results.
- **MED-3:** `load-module.sh` resolves module paths via `modinfo -n` instead of a hard-coded `/lib/modules/.../updates/dkms` path.
- **MED-4:** D-Bus policy for `org.mvgal.MVGAL` is restricted to root and the `mvgal` group (previously open to all users).
- **MED-5:** `mvgal-hw-validate` attributes device-node failures to "kernel module not loaded" with a load hint instead of a bare FAIL.
- **MED-6:** `/etc/mvgal/custom_strategy.lua` is now shipped as a no-op stub so the `[custom] script_path` reference in `mvgal.conf` always resolves.

### Changed
- Version bumped 0.7.7 → 0.7.8 (bugfix release)

## [v0.7.7] — 2026-09-21

### Fixed
- **CRITICAL-1:** Vulkan ICD device dispatch — `vkCreateImage`, `vkGetImageMemoryRequirements` and `vkDestroyImage` were missing from `vk_icdGetDeviceProcAddr`, leaving NULL entries in the loader's device dispatch table. Any app calling `vkCreateImage` (e.g. `vulkaninfo`'s `FillImageTypeSupport`) crashed with SIGSEGV (exit 139). The three image functions are now implemented (tagged allocation records, plausible size/alignment/memoryTypeBits) and registered.
- **CRITICAL-2:** Vulkan ICD `vkGetPhysicalDeviceQueueFamilyProperties2` wrote past the caller's array — the 1.0 helper writes all queue families starting at element 0's inner struct, overflowing the `VkQueueFamilyProperties2` array and corrupting the pNext chain (heap corruption / SIGABRT under multi-ICD setups). Now fills a temp buffer and copies per element.
- **MED-1:** Version macros unified — `mvgal-gui --version` now reports 0.7.7 (CMakeLists.txt was stale at 0.7.5 while Cargo.toml and the spec said 0.7.6).

### Changed
- Version bumped 0.7.6 → 0.7.7 (bugfix release)

## [v0.7.6] — 2026-09-17

### Fixed
- **CRITICAL-1:** Vulkan layer no longer returns `VK_ERROR_LAYER_NOT_PRESENT` from `vkEnumerateDeviceExtensionProperties` for physical devices it did not wrap (e.g. the Mesa dzn ICD). The loader aborted with a `VUID-physicalDevice-parameter` error (SIGABRT, exit 134) in `mvgal_amd_external_mem --scan`; the layer now forwards the call through any registered instance dispatch chain.
- **HIGH-1:** `mvgal-status` now prints an explicit DEGRADED MODE warning and exits non-zero when the `mvgal` kernel module is not loaded (Secure Boot / MOK rejection previously left the daemon silently running on sysfs/stub data).
- **HIGH-2:** `mvgal-config -c/--config` now writes to the requested config file — the pkexec helper parsed `--config` but `set_config_value` ignored it and always wrote `/etc/mvgal/mvgal.conf`.
- **HIGH-3:** Config helper append check is now section-scoped, so a key that also appears in a later section no longer suppresses appending it to the target section.
- **MED-1:** Daemon `SET_CONFIG` IPC handler validates the payload (printable ASCII + at least one `[section]`) and writes atomically (temp file + rename) instead of truncating the live config with a raw write.
- **MED-2:** `mvgal-dashboard` with no arguments prints a banner + usage hint instead of exiting silently.
- **MED-3:** Version macros unified — `mvgal --version` now reports 0.7.6 everywhere (`MVGAL_VERSION_PATCH` was stale at 3 while the string said 0.7.5).

### Changed
- Version bumped 0.7.5 → 0.7.6 (bugfix release)

## [v0.7.5] — 2026-09-15

### Fixed
- **CRITICAL-1:** DKMS install — `BUILT_MODULE_LOCATION=/kernel` for all modules so DKMS finds the `.ko` files built into the `kernel/` subdirectory. The previous `MAKE[1]` copy approach never ran because DKMS executes only one make command.
- **CRITICAL-2:** Secure Boot — `%post -n mvgal-dkms` now signs the DKMS-installed modules in `/lib/modules/*/updates/dkms` with the per-machine MVGAL key (previously only the kernel-tree modules were signed, so DKMS modules were rejected under Secure Boot). `mvgal-enroll-mok` now generates a one-time password when `-p` is omitted and always passes it to `mokutil --import`, so enrollment works through pkexec without a TTY.
- **CRITICAL-3:** Vulkan ICD implements the WSI entry points the loader requires — `vkGetPhysicalDeviceSurfaceSupportKHR`, `SurfaceCapabilitiesKHR`, `SurfaceFormatsKHR`, `SurfacePresentModesKHR`, plus `FormatProperties2`, `ImageFormatProperties2`, `SparseImageFormatProperties2`, `ExternalBuffer/Fence/SemaphoreProperties`, `ToolProperties` — so apps no longer abort with "ICD does not export vkGetPhysicalDeviceSurfaceSupportKHR!".

## [v0.7.4] — 2026-09-07

### Fixed
- **CRITICAL-1:** DKMS build layout — `dkms.conf` now copies the built `.ko` files from the `kernel/` subdirectory up to the DKMS build root so `dkms install` actually finds and installs `mvgal.ko` / `mvgal_ntsync.ko`; spec `%post` no longer swallows `dkms build`/`dkms install` failures
- **CRITICAL-2:** Vulkan ICD now exposes a placeholder physical device (instead of 0 devices) when no physical GPU is available or the daemon is not running
- **CRITICAL-3:** OpenCL CMake propagation fixed — `OpenCL_LIBRARIES`/`OpenCL_INCLUDE_DIRS` are now populated from the pkg-config result so the ICD links the loader correctly
- **HIGH-1:** `mvgal_amd_external_mem --no-mvgal` now implies `--scan` instead of printing usage
- **HIGH-2:** `mvgal-dashboard` and `mvgal-gui` gained `--check`/`--self-test` for non-hanging headless verification
- **HIGH-3:** `mvgal-enroll-mok -p/--password` is now passed to `mokutil --import` so enrollment works without a TTY through pkexec
- **MED-1:** `mvgal-probe` exits 0 when the DRM sysfs fallback detects GPUs (was 2)
- **MED-2:** `mvgal-steam-setup` with no arguments prints usage and exits 0
- **MED-3:** `mvgal-config set-power-profile` help now marks the option AMD-only and the error suggests `mvgal list-gpus`
- **MED-4:** `mvgal-load`/`mvgal-unload` self-escalate via pkexec using the existing `mvgal-pkexec-helper.sh`

### Changed
- Version bumped 0.7.3 → 0.7.4 (bugfix release)

---

## Earlier Versions

- **[v0.7.3]** (2026-09-02) — config writes route through `-c`-specified file; D-Bus policy reload on install; `--version` added to all CLI tools; version macros unified
- **[v0.7.2]** (2026-09-01) — `mvgal-enroll-mok` false-positive fix; daemon reads `[core] default_strategy`; D-Bus `receive_sender`; portal hang fixes; `pidof` fallbacks
- **[v0.7.1]** (2026-09-01) — DKMS Kbuild wrapper; `mvgal-load` loads all 7 modules; custom strategy existence check; config loaded by default
- **[v0.7.0]** (2026-08-31) — Multi-vendor OpenCL ICD aggregation; `-Bsymbolic-functions` deadlock fix; CLI OpenCL enumeration
- **[v0.4.0]** (2026-06-07) — GPU power management (NVML), dynamic scoring scheduler, NTSYNC kernel module, multi-vendor Vulkan barrier translation, PCIe P2P DMA, AI-driven scheduler, unified VRAM heap, Proton bridge, DKMS build support, RPM/COPR multi-distro packaging

For the complete history, see the [source repository CHANGELOG](https://github.com/TheCreateGM/mvgal/blob/main/CHANGELOG.md).