---
tags: [mvgal, status, reference]
aliases: [Project Status, Status]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: reference
mvgal_order: 5
---

# MVGAL Project Status

> Source metadata is **0.7.16** (`CMakeLists.txt`, `Cargo.toml`, and version headers). The project changelog documents releases through **0.7.16**.

## Verified project state

MVGAL contains a Linux kernel module, userspace daemon and libraries, API interception components, command-line tools, Rust safety crates, tests, and packaging definitions. Components building successfully does not establish that every runtime feature works on physical hardware.

Two later releases changed correctness, not capability:

- **v0.7.15 fixed a memory-corruption bug in the userspace copy path.** `mvgal_memory_copy()` applied the region offsets twice, so any copy at a non-zero offset read and wrote past the end of the mapping. The untrusted part of the data path was corrupting memory; it now does not. See [[docs/MEMORY|Memory Management]] § Buffer copies.
- **v0.7.16 made two API paths real rather than present.** The custom splitter API now registers and releases descriptors, and the command DAG translate and emit paths now produce a deep copy and an actual replay instead of returning their arguments unchanged. Both were previously reachable but non-functional. Note that registering a splitter still does not make the `custom` strategy selectable; applying one needs a task tree contract that has not been defined. See [[docs/STRATEGIES|Scheduling Strategies]] § Custom splitters.

The 0.7.12 source changelog records an audit that removed misleading success behavior:

- The MVGAL PCI driver no longer binds GPU devices; discovery remains read-only so native drivers retain ownership.
- Vendor VRAM allocation and kernel submission operations that lack a working implementation report `-EOPNOTSUPP`.
- The Vulkan ICD no longer advertises a synthetic aggregate physical device.
- Runtime capabilities are set from probes. Kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle are not advertised as supported.
- Scheduler, memory, and power paths use probed capability bits.

These constraints mean MVGAL does not currently provide general transparent cross-vendor GPU execution. Check the source capability matrix and the actual device's reported capabilities before relying on a path.

## Version and release notes

| Surface | State |
|---------|-------|
| CMake project and Cargo workspace | 0.7.16 |
| Source changelog | Releases documented through 0.7.16 |
| Docs package directory | 0.7.16 in every format — RPM, `.deb`, AppImage, tarball and Flatpak. See [`package/README.md`](https://github.com/TheCreateGM/mvgal-docs/blob/main/package/README.md). Artifact presence is not a runtime validation result |

See [CHANGELOG.md](CHANGELOG.md) for the changes documented in the source changelog.

## Project components

| Component | Location | Scope |
|-----------|----------|-------|
| Kernel module and vendor adapters | `kernel/` | Device discovery, UAPI, capability probes, synchronization and related interfaces |
| Daemon and runtime | `src/userspace/`, `runtime/` | Device registry, IPC, metrics, scheduling and configuration |
| API interception and ICDs | `src/userspace/intercept/`, `src/userspace/vulkan_icd/` | API-facing components; behavior depends on enabled build options and supported operations |
| Public headers | `include/mvgal/` | C API and kernel/userspace interfaces |
| Rust components | `safe/`, `runtime/safe/` | Fence, memory-safety and capability-model crates |
| CLI and GUI | `tools/`, `ui/` | Diagnostics, configuration, benchmarking, setup, and optional user interfaces |
| Build and packaging | `CMakeLists.txt`, `meson.build`, `packaging/` | Build configurations and distribution metadata |

## Validation guidance

For current supported commands, use `mvgal --help`, `mvgal-info --help`, `mvgal-status --help`, and `mvgal-config --help` from the installed build. `mvgal-status` returns a non-zero status when the kernel module is not loaded. Use `mvgal-info` to inspect discovered devices; discovery does not prove workload submission, memory allocation, or peer transfer support.

Hardware compatibility claims should include the GPU model, native driver, kernel version, reported capability bits, exact test, and result. The repository changelog and tests are the evidence source for code changes; the docs do not claim unrecorded production validation.
