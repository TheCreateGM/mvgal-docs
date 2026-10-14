---
tags: [mvgal, status, reference]
aliases: [Project Status, Status]
mvgal_version: "0.7.22"
mvgal_verified: 2026-10-14
mvgal_role: reference
mvgal_order: 5
---

# MVGAL Project Status

> Source metadata is **0.7.22** (`CMakeLists.txt`, `Cargo.toml`, version headers, RPM spec, git tag `v0.7.22` = `3056cd5`). The source tree's `CHANGELOG.md` and the spec `%changelog` both document the release.

## Verified project state

MVGAL contains a Linux kernel module, userspace daemon and libraries, API interception components, command-line tools, Rust safety crates, tests, and packaging definitions. Components building successfully does not establish that every runtime feature works on physical hardware.

Two later releases changed correctness, verification and packaging, not runtime capability:

- **v0.7.15 fixed a memory-corruption bug in the userspace copy path.** `mvgal_memory_copy()` applied the region offsets twice, so any copy at a non-zero offset read and wrote past the end of the mapping. The untrusted part of the data path was corrupting memory; it now does not. See [[docs/MEMORY|Memory Management]] § Buffer copies.
- **v0.7.16 made two API paths real rather than present.** The custom splitter API now registers and releases descriptors, and the command DAG translate and emit paths now produce a deep copy and an actual replay instead of returning their arguments unchanged. Both were previously reachable but non-functional. Note that registering a splitter still does not make the `custom` strategy selectable; applying one needs a task tree contract that has not been defined. See [[docs/STRATEGIES|Scheduling Strategies]] § Custom splitters.

The three releases after that added verification reach and packaging determinacy rather than new device-facing behaviour:

- **v0.7.17 repaired the Rust quality gate, which had never run.** `clippy.toml` carried three keys that modern clippy rejects, and clippy aborts on an unreadable configuration file *before* it lints anything, so the Rust crates had never been linted at all. It also listed `unwrap` and `expect` under `disallowed-macros`, though they are methods rather than macros, so `-D warnings` turned a clippy reporting quirk into a hard failure. Four real defects surfaced once the gate ran: `CrossDeviceFence` was neither `Send` nor `Sync` (timestamp in a `Cell`, handle in a raw pointer) so it could never cross a thread boundary; `GpuTimeline::create_fence()` and `FenceManager::create_fence()` each returned a *second*, independent `Arc`, so signalling the returned handle had no effect on the fence they retained; `MvgalError` relied on the implicit C-like enum representation, which cannot hold `Unknown = 0xFFFFFFFF`, and is now `#[repr(u32)]`; and `align_up()` hand-rolled the ceiling division `div_ceil()` provides.
- **v0.7.18 added a synthetic GPU topology backend** (`include/mvgal/mvgal_mock.h`, 30th public header). Seven presets describe device populations from a single discrete GPU to a four-vendor, three-root-complex machine. The GPU manager's rescan substitutes it for the hardware scan, so the scheduler, the memory manager and the P2P cost model all see synthetic devices through the normal discovery path. Thermal inertia, throttling, VRAM occupancy and per-pair link bandwidth are modelled rather than canned. See [[docs/API|API Reference]] § Synthetic Topology Backend. This is a **test surface**: it shapes what discovery reports and creates no devices.
- **v0.7.20 made release artefacts reproducible.** The source tarball and SRPM are now byte-identical when rebuilt from the same commit. Two causes were fixed: `vendor/` is tracked rather than gitignored, so the packaging script copied it a second time into `vendor/vendor/` (~12 MB of duplicates) and restamped the parent's mtime with the wall clock; and rpm only rewrites `BUILDTIME` from `SOURCE_DATE_EPOCH` when the opt-in macro `use_source_date_epoch_as_buildtime` is defined, which it ships without. Binary RPMs are still **not** byte-identical — see § Reproducibility limits below.

**v0.7.22 fixed a defect that made Secure Boot unusable.** This is worth
reading before anything else on this page, because the symptom looked like a
user error and the documented remedy could not work.

On v0.7.21 and earlier, `mvgal_ntsync.ko` — a hard dependency of `mvgal.ko` —
was signed with **DKMS's** key, while `mvgal-enroll-mok` enrolled only the
per-machine **MVGAL** key. A user could follow the printed instructions exactly:
enroll, reboot, confirm in MOK Manager. ntsync would still be rejected, and
because `mvgal.ko` depends on it, `modprobe mvgal` would fail too. Three faults
combined: the signing loops globbed `"$dir/"*.ko`, which cannot match the
`.ko.xz` a compression-enabled distro installs; they searched only the kernel
tree and `.../updates/dkms` when DKMS's real destination is distro-dependent
(`.../extra` on Fedora); and they discarded every failure, so the install
reported success.

v0.7.22 replaces both loops with `/usr/lib/mvgal/mvgal-sign-modules.sh`, which
searches every destination, handles `.ko`/`.ko.xz`/`.ko.zst` by decompressing,
signing and recompressing (a compressed module cannot be signed in place), and
exits non-zero rather than signing nothing. Two related gaps closed with it:
`mvgal-dkms` now **requires** `mvgal` at the same version, because its `%post`
signs with a key the main package's `%post` creates and rpm may run them in
either order; and `dkms.conf` sets `POST_INSTALL`, because a kernel upgrade
rebuilds modules without running any RPM scriptlet and would otherwise restore
the original defect.

The daemon's enrollment check was also wrong in a way worth knowing about: it
tested `mokutil --list-enrolled | grep -qi MVGAL`, which matches on subject
name. Every MVGAL keypair shares one subject, so after a key rotation the old
certificate is still listed, the check **passes**, and the daemon stays silent
while modules signed by the new key are rejected. It now uses
`mokutil --test-key` against the specific certificate. See
[[docs/SECURE_BOOT|Secure Boot]] for how to check and re-sign by hand.

The rest of the release is about the tools telling the truth: `set-power-curve`
no longer takes a GPU index it silently discarded; the invalid `gaming` example
is gone; log output no longer reaches stdout on the pre-initializer path;
`| head` exits 0 instead of 141; the Vulkan layer and the opt-in aggregated ICD
are reported separately instead of as one ambiguous "registered"; `mvgal-compat`
suggests `mvgal-load` rather than a `modprobe` that cannot succeed; and
`mvgal-bench` labels every figure with the hardware path it actually measured,
which is host RAM and a single-threaded host CPU. See
[[docs/CHANGELOG|Changelog]] § v0.7.22.

**v0.7.21 closed a black-box test report raised against 0.7.20.** It is a correctness and packaging release; it adds no device-facing capability and removes no existing constraint. Two of its findings were genuine defects rather than reporting problems, and both are worth stating precisely because the obvious reading of either was wrong:

- **The daemon socket group was a capability problem, not a `chown()` problem.** The IPC socket was `root:root`, so every user in the `mvgal` group was locked out of all CLI-to-daemon IPC. The `chown()` call was correct; the unit's `CapabilityBoundingSet` omitted `CAP_CHOWN`, which caps what a uid-0 process can ever hold, and root is not a member of `mvgal`, so the call could only fail. Adding error handling would have documented the bug without fixing it. This is the class of defect a source-reading pass tends to miss and a black-box report surfaces immediately.
- **The OpenCL ICD advertised a version it did not implement.** It reported `OpenCL 1.2` while exporting 2 of the 7 entry points 1.2 added, so an application using a 1.2 feature received `NULL` from the loader. All seven are now exported. The 1.2 ceiling remains deliberate and is now documented in the source rather than left as an unexplained literal.

The remainder of the release concerns what the tools tell you and what packaging does to your files: consistent exit codes for degraded states, log output moved off stdout so JSON output stays parseable, unavailable values emitted as `null` instead of `-1`/`0`, shared system memory no longer labelled as dedicated VRAM, cross-tool metadata agreement, `--version` and long options present across the shipped tools, and a configuration merge so an RPM upgrade no longer discards user edits. See [[docs/CHANGELOG|Changelog]] § v0.7.21 for the item-by-item list.

Two reported items were investigated and closed as **not** MVGAL defects rather than deferred. The Vulkan loader warning about display entry points does not originate from MVGAL: both entry points resolve through the shipped ICD's negotiated interface version 5, and no ICD manifest has shipped in `vulkan/icd.d` since 0.7.14. And the `card0`/single-driver concern needs no code change — enumeration selects on PCI vendor ID and resolves the driver from the bound sysfs symlink, verified on a host exposing only `card1` with both `i915` and `xe` loaded.

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
| CMake project and Cargo workspace | 0.7.22 |
| Source changelog | Releases documented through 0.7.22 |
| Upstream COPR | 0.7.22 RPMs built on all 19 enabled chroots (build #11118333) |
| Docs package directory | Still **0.7.20** in every format — RPM, `.deb`, AppImage, tarball and Flatpak. These have not been rebuilt for 0.7.22; see [`package/README.md`](https://github.com/TheCreateGM/mvgal-docs/blob/main/package/README.md). Artifact presence is not a runtime validation result |

See [CHANGELOG.md](CHANGELOG.md) for the changes documented in the source changelog.

### Reproducibility limits

The **source** tarball and the **SRPM** are byte-identical when rebuilt from the
same commit. The **binary RPM is not**, and the reason is worth stating plainly
because it is easy to assume otherwise:

- Fedora's toolchain links with a bare `--build-id`, so every ELF carries a
  random `NT_GNU_BUILD_ID` note. Two builds of identical source produce
  different binaries.
- The build directory is baked into the artefacts: `DW_AT_comp_dir`,
  `DW_AT_name` and the generated `mvgalConfig.cmake` all record the absolute
  build path, so building in two different directories also diverges.

Both are addressable with `-Wl,--build-id=sha1` plus
`-fdebug-prefix-map`/`-ffile-prefix-map`, which preserves the content-derived
build-id that debuginfod and crash tooling correlate against. That is **not**
enabled, because the spec's `%build` section drives `cmake` through
`cmake-rpm-macros`, whose `%cmake` macro has repeatedly overridden spec-level
flag and cache workarounds in earlier releases. Treat binary-RPM
bit-reproducibility as open work, not as a property the project has.

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
| Tests and synthetic topology | `src/tests/`, `src/userspace/testing/` | Unit suite (15 test binaries) and the synthetic GPU topology backend |

## Validation guidance

For current supported commands, use `mvgal --help`, `mvgal-info --help`, `mvgal-status --help`, and `mvgal-config --help` from the installed build. `mvgal-status` returns a non-zero status when the kernel module is not loaded. Use `mvgal-info` to inspect discovered devices; discovery does not prove workload submission, memory allocation, or peer transfer support.

Hardware compatibility claims should include the GPU model, native driver, kernel version, reported capability bits, exact test, and result. The repository changelog and tests are the evidence source for code changes; the docs do not claim unrecorded production validation.
