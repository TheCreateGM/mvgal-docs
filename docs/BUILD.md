---
tags: [mvgal, build, guide]
aliases: [Build Guide, Building, Compile]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: guide
mvgal_order: 14
---

# MVGAL Build Guide

> Source metadata is **0.7.16**; the source changelog documents releases through **0.7.16**. This guide reflects the checked-in CMake, Meson, and Cargo manifests. A successful build does not mean all hardware operations are supported.

## Requirements

The top-level CMake configuration requires CMake 3.16+, a C and C++ compiler, pkg-config, libdrm, and pciaccess. Additional components are conditional on dependencies. Install the development packages matching your distribution; inspect CMake output for disabled optional targets.

Rust crates use the workspace manifest in `Cargo.toml` (edition 2021, Rust 1.75 minimum). Kernel module compilation additionally requires headers for the target kernel and the kernel build system.

## CMake build

From the source repository root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The top-level options include:

| Option | Default | Purpose |
|--------|---------|---------|
| `MVGAL_BUILD_KERNEL` | ON | Kernel module target |
| `MVGAL_BUILD_RUNTIME` | ON | Runtime daemon and libraries |
| `MVGAL_BUILD_API` | ON | API components |
| `MVGAL_BUILD_GAMING` | ON | Gaming integration components |
| `MVGAL_BUILD_TOOLS` | ON | Tools |
| `MVGAL_ENABLE_RUST` | ON | Rust safety components |
| `MVGAL_ENABLE_ZIG` | OFF | Zig components |
| `MVGAL_BUILD_TESTS` | ON | Test targets |
| `MVGAL_BUILD_UI` | OFF | UI dashboard |
| `MVGAL_ENABLE_SPIRV_OPT` | OFF | SPIR-V optimization dependencies |

Optional Vulkan, OpenCL, Qt, and other targets depend on development headers and libraries. Read configure output to confirm which targets were enabled. The top-level project also defines `MVGAL_ENABLE_FULL_STACK` and `MVGAL_BUILD_FULL_STACK`; these options do not certify the backends' hardware capabilities.

## Meson build

The checked-in `meson_options.txt` defines these options: `with_vulkan`, `with_opencl`, `with_cuda` (experimental, defaults off), `with_daemon`, `with_tests`, `with_benchmarks`, and `with_kernel_module` (defaults off).

```bash
meson setup builddir -Dwith_daemon=true -Dwith_tests=true -Dbuildtype=release
ninja -C builddir
```

## Rust crates

```bash
cargo test --workspace
```

The workspace includes `safe/fence_manager`, `safe/memory_safety`, `safe/capability_model`, `safe/ffi_tests`, and `runtime/safe`.

## Kernel module

The kernel module is built through the CMake/Kbuild integration and requires headers for the target kernel. DKMS packaging definitions are under `kernel/dkms/` and distribution package directories. Loading the module requires appropriate privileges and, when Secure Boot is enabled, a trusted signing key. See [Secure Boot](SECURE_BOOT.md).

## Install

Use the build's configured install prefix and inspect generated install rules before installing:

```bash
cmake --install build --prefix /usr/local
```

Distribution packaging definitions are under `packaging/`; artifact names and install paths depend on the selected package recipe. Do not rely on old hard-coded paths or version numbers in generated examples.

## Source references

- Top-level options and targets: source `CMakeLists.txt`
- Meson options and targets: source `meson_options.txt` and `meson.build`
- Rust workspace: source `Cargo.toml`
- Package recipes: source `packaging/`
