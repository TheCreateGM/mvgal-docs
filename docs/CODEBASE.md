---
tags: [mvgal, codebase, reference]
aliases: [Codebase Map, Source Map]
mvgal_version: "0.7.29"
mvgal_verified: 2026-10-27
mvgal_role: reference
mvgal_order: 7
---

# Codebase Map

This guide maps the checked-in source tree at MVGAL 0.7.29. Generated build directories, package outputs, vendored dependencies and research/session notes are excluded from the map.

## Repository root

| Path | Contents |
|---|---|
| `CMakeLists.txt` | Primary multi-component build; required DRM/PCI dependencies and optional component gates |
| `meson.build`, `meson_options.txt` | Independent Meson build for selected userspace components |
| `Cargo.toml`, `safe/` | Rust workspace: fence management, memory-safety helpers, capability model and FFI checks |
| `kernel/` | Linux kernel module sources, vendor adapters, UAPI implementation and KUnit-style tests |
| `include/mvgal/` | Public C headers, ioctl/UAPI types and API declarations |
| `src/userspace/` | C userspace core, API, scheduler, memory, interception and low-level daemon helpers |
| `runtime/` | C++20 daemon and Rust wrapper modules |
| `tools/` | Main CLI, inventory/status/configuration tools, probes, workload gate and benchmarks |
| `steam/`, `compat/`, `opengl/` | Steam helper/profile data and graphics/Windows compatibility pieces |
| `bindings/` | Language wrappers and client bindings |
| `ui/`, `dashboard/` | Optional Qt dashboard and Haxe dashboard source |
| `config/`, `data/`, `systemd/` | Runtime configuration, privileged helpers, D-Bus/polkit policy and service unit |
| `packaging/`, `scripts/`, `configs/` | Distribution recipes, release/build helpers and COPR target configurations |
| `Jenkinsfile`, `Jenkinsfile.windows` | CI pipelines: the Linux package build and the Windows cross-compilation packaging pipeline (added in v0.7.28) |
| `cmake/toolchains/` | Cross-compilation toolchain files for the Windows targets: `mingw-w64-x86_64.cmake`, `mingw-w64-override.cmake`, `zig-cc-windows.sh` (v0.7.28) |
| `packaging/windows/` | Windows installer definitions: `mvgal.nsi` (NSIS), `mvgal.wxs` (WiX) and packaging notes (v0.7.28) |
| `packaging/jenkins/` | CI build scripts for each artifact format, including `build_windows.sh` used by the Windows pipeline |
| `src/tests/`, `kernel/tests/`, `safe/ffi_tests/` | Userspace, kernel and Rust FFI test sources |
| `professional/`, `misc/`, `tests/` | Examples, integrations, benchmark assets and validation helpers |

## Userspace core (`src/userspace/`)

- `api/`, `core/` — public C API implementation and process/fork handling.
- `daemon/` — C GPU manager, configuration and IPC helpers used by the userspace library; distinct from the C++ `runtime/daemon` executable.
- `scheduler/` — policy selection, load balancing, work splitting, strategy implementations and AI-related helpers.
- `memory/` — allocation bookkeeping, mapping/copy helpers, coherency, DMA-BUF, P2P DMA and unified heap.
- `execution/` — execution coordination, dispatch and reproducible-build helpers.
- `intercept/` — API-specific wrappers/layers: Vulkan, OpenCL, CUDA, D3D, WebGPU, media, vendor helpers and shader translation.
- `power/`, `sycl/`, `win32/` — power curve and power-manager helpers, the SYCL entry point, and the WoW64 thunk.
- `vulkan_icd/` — separate Vulkan ICD implementation and IPC client; distinct from `intercept/vulkan/` layer.
- `transport/`, `network/`, `ccl/` — transport, remote/pool discovery and collective communication code.
- `testing/` — synthetic GPU topology used to exercise userspace discovery and policy paths; it creates no physical devices.

## Runtime daemon (`runtime/`)

`runtime/daemon/main.cpp` starts `mvgald`; the `Daemon` coordinates the daemon subsystems. The major modules are `device_registry` (inventory), `kernel_device` (ioctl client), `ipc_server` and `dbus_service` (control surfaces), `scheduler`, `memory_manager`, `power_manager`, `metrics_collector`, `nvml_loader`, `steam_profile_loader` and `ntsync_bridge`. Kernel-device availability and operation errors are reported as runtime state; callers must not infer successful kernel control merely because the daemon is running.

`runtime/safe/` contains Rust integration wrappers. The independently packaged crates under `safe/` provide the underlying memory, fence and capability-model functionality. `Cargo.toml` is the workspace manifest; `bindings/rust` is explicitly excluded and has its own manifest.

## Kernel (`kernel/`)

`mvgal_core.c` registers the DRM-facing device and ioctl table. `mvgal_device.c` manages discovered devices and capability probing; `mvgal_sysfs.c` exposes device data; `mvgal_memory.c`, `mvgal_sync.c`, `mvgal_power.c`, `mvgal_scheduler.c`, `mvgal_dmabuf.c`, `mvgal_p2p.c`, `mvgal_virt.c` and `mvgal_ntsync.c` hold subsystem code. `vendors/` contains AMD, NVIDIA, Intel, Moore Threads and Adreno adapters. Adapter presence does not itself establish a supported submit/allocation path. Build integration lives in `kernel/CMakeLists.txt`, `Kbuild`, `Makefile` and `dkms/`.

## APIs and integrations

`include/mvgal/` is the public header surface. `src/userspace/intercept/` contains loader-facing interposition components, while `src/userspace/vulkan_icd/` is a separate ICD target. `compat/` includes DXVK/VKD3D bridges, Vulkan compatibility code, preload and ntsync/WoW64 helpers. `steam/` contains profiles, compatibility metadata and frame-pacer code. Check `CMakeLists.txt`, subdirectory CMake files, and installed manifests before assuming an integration was built or registered.

## Build entry points and options

The root CMake build is the broadest build graph. Its main switches include `MVGAL_BUILD_KERNEL`, `MVGAL_BUILD_RUNTIME`, `MVGAL_BUILD_API`, `MVGAL_BUILD_GAMING`, `MVGAL_BUILD_TOOLS`, `MVGAL_ENABLE_RUST`, `MVGAL_BUILD_TESTS` and `MVGAL_BUILD_UI` (off by default). Feature-specific targets also depend on discovered libraries and nested CMake logic. Meson options are defined separately in `meson_options.txt`; do not assume CMake options map one-to-one. Rust components are built through Cargo. See [Build Guide](BUILD.md).

## How to trace a feature

1. Find its public contract under `include/mvgal/` or the relevant tool's `--help`/man page.
2. Follow the implementation in `src/userspace/` or `runtime/daemon/`.
3. For kernel control, follow the ioctl in `include/mvgal/mvgal_uapi.h` into `kernel/mvgal_core.c` and its handler.
4. Check capability probes and error returns in the backend before describing the operation as supported.
5. Check build/install rules and package manifests; source presence alone does not guarantee an installed feature.

See [Architecture](ARCHITECTURE.md) for runtime relationships and [Status](STATUS.md) for current limits.
