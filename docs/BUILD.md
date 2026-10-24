---
tags: [mvgal, build, guide]
aliases: [Build Guide, Building, Compile]
mvgal_version: "0.7.26"
mvgal_verified: 2026-10-24
mvgal_role: guide
mvgal_order: 14
---

# MVGAL Build Guide

> Source metadata is **0.7.26**; the source changelog documents releases through **0.7.26**. This guide reflects the checked-in CMake, Meson, and Cargo manifests. A successful build does not mean all hardware operations are supported.

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

## Packaging

> [!info]
> Historical build record: the earlier v0.7.20 source RPM and package pipeline were exercised in October 2026. That record does not describe the current 0.7.26 artifacts or establish their publication state. See [`package/README.md`](../package/README.md) for files present in this docs checkout.

### Source RPM

`scripts/mksrpm.sh` builds the SRPM. It is deliberately strict, and the strictness is the feature:

```bash
./scripts/mksrpm.sh            # uses packaging/rpm/mvgal.spec
./scripts/mksrpm.sh path/to/other.spec
```

- **Version cross-check.** The version in the spec is compared against eight other sources — `CMakeLists.txt`, `Cargo.toml`, `bindings/rust/Cargo.toml`, `kernel/mvgal_version.h`, `include/mvgal/mvgal_version.h`, `tools/libmvgal/CMakeLists.txt`, `kernel/dkms/dkms.conf` and `Cargo.lock` — and against any hard-coded `N.N.N` left in six C/C++ sources after comment stripping. A mismatch aborts the build. This is why a release bump touches eleven files.
- **Dirty-tree guard.** The script refuses to run against a working tree with uncommitted changes, because a tarball built from `git archive` would not correspond to the checkout you are looking at. Note that `vendor/` and `build*` are tracked/ignored asymmetrically; a stray `*.spec` in the repository root will block the script.
- **Output.** Both `v<version>.tar.gz` and `mvgal-<version>-1.<dist>.src.rpm` are written to the repository root. Both are gitignored.

### Fedora COPR

```bash
copr build axogm/mvgal mvgal-<version>-1.fc44.src.rpm
copr watch-build <build_id>
```

The SRPM embeds the source tarball, so no build chroot fetches anything from the forge. This matters: the spec's `Source0` points at a `github.com/.../archive/refs/tags/v<version>.tar.gz` URL, and if a build ever did resolve it, the tag must exist first. Bumping the version without pushing the tag yields a build that fails in every chroot with a 404.

> [!warning]
> `copr build` prints nothing while uploading, and an SRPM is several megabytes. A short command timeout can kill the client after the upload has already succeeded server-side — check `copr list-builds` before assuming it failed.

Build state is authoritative at `https://copr.fedorainfracloud.org/api_3/build/<build_id>`. Note that `api.copr.fedorainfracloud.org` does not resolve, and a bare `/api_3/` returns 404; only the per-build path works.

### Reproducibility

Rebuilding the tarball and SRPM from one commit is **byte-identical**. Rebuilding a binary RPM is not, for two independent reasons:

| Artefact | Reproducible | Why |
|----------|--------------|-----|
| `v<version>.tar.gz` | yes | `git archive` plus a guard that refuses a missing `vendor/` |
| `.src.rpm` | yes | `BUILDTIME` pinned to the commit date |
| binary `.rpm` | no | random ELF build-id; build path baked into DWARF |

The `BUILDTIME` pin is the non-obvious one. Exporting `SOURCE_DATE_EPOCH` alone changes nothing on rpm 6.0.2 — rpm only honours it when the opt-in macro `use_source_date_epoch_as_buildtime` is also defined, which it ships without on purpose. Both `scripts/mksrpm.sh` and `packaging/jenkins/build_rpm.sh` set both, which is why the SRPM the Jenkins RPM stage rebuilds is byte-identical to the one built locally.

The remaining binary-RPM variance is **left in place deliberately**. `-Wl,--build-id=sha1` combined with `-fdebug-prefix-map` would fix both axes and was verified to work, but stripping or replacing build-ids degrades debuginfo and debuginfod correlation for a shipped `-debuginfo` subpackage. See [[docs/STATUS|Project Status]] § Reproducibility limits.

### Jenkins

The `mvgal-packages` job builds every distributable format — deb, rpm, tar.zst, AppImage and Flatpak — and verifies a `SHA256SUMS` over the results. It has no webhook and is triggered manually. `BUILD_FLATPAK` is a boolean parameter and defaults to true; the Flatpak stage needs a ~2 GB SDK cache under `$JENKINS_HOME/.flatpak-user`, which is why the job preserves that directory between runs.

## Source references

- Top-level options and targets: source `CMakeLists.txt`
- Meson options and targets: source `meson_options.txt` and `meson.build`
- Rust workspace: source `Cargo.toml`
- Package recipes: source `packaging/`
- SRPM recipe and its version/dirty-tree guards: source `scripts/mksrpm.sh`
- Multi-format packaging used by CI: source `packaging/jenkins/`
