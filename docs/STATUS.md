---
tags: [mvgal, status, reference]
aliases: [Project Status, Status]
mvgal_version: "0.7.46"
mvgal_verified: 2026-11-14
mvgal_role: reference
mvgal_order: 5
---

# MVGAL Project Status

## Source version

The source repository reports **0.7.46** in CMake and the generated public version header. The source changelog has entries through **0.7.46**. This documentation snapshot was reconciled against that source on 2026-11-14. Package publication and physical hardware validation are separate questions; a successful build or installed artifact does not establish runtime support.

## v0.7.46 power and diagnostics updates

v0.7.46 wires the `[power]` section of `mvgal.conf` to the daemon end to end. `applyPowerConfig()` in `daemon.cpp` now parses `power_curve_profile` (`silent|balanced|performance|custom`) via `profileToPowerCurve()` — previously the pkexec helper persisted the key but nothing read it, so `set-power-curve` reported success while the daemon kept compiled defaults. An explicit `power_curve` list takes precedence over a named profile, and an unknown profile name is warned about rather than applied. The release also adds `mvgal` CLI subcommands `set-power-curve`, `set-power-limit`, `psu-config` and `psu-headroom`, which persist `[power]` keys through the pkexec helper's new generic `set-config` action (restricted to keys the daemon actually parses) and reload the daemon, plus diagnostics `mvgal doctor [--json]` (delegates to `mvgal-doctor`), `mvgal verify` (end-to-end self-check with an optional Vulkan dispatch smoke test) and `mvgal test` (delegates to `mvgal-hw-validate`).

The same release removes phantom power telemetry: `PowerManager::readTemperature()`, `readPowerDraw()`, `readFanSpeed()`, `writePowerLimit()` and `writeFrequency()` no longer return fabricated values (50 °C, 100 W, 0 RPM, unconditional success) when no vendor interface is present — callers keep their last known readings — and the fixed per-state NVML wattage writes (250/150/50/20 W) that ignored the card's actual rating are gone. See [Changelog](CHANGELOG.md) § v0.7.46.

## v0.7.45 execution updates

v0.7.45 replaces the Vulkan backend stub with a real compute path: `runtime/daemon/vulkan_backend.cpp` creates a `VkDevice` per PCI-BDF-matched `VkPhysicalDevice`, compiles an embedded SPIR-V reference kernel (`vulkan_ref_kernel_spv.h`), stages inputs through host-visible `VkDeviceMemory`, submits to a compute queue, waits on a `VkFence`, and CPU-validates the mapped output — the same contract as the OpenCL/CUDA backends. It was validated on AMD RADV (RX 6400), NVIDIA proprietary (RTX 3050) and Intel Mesa (Arc A380), including element-range partitioning across GPUs. The backend previously hand-declared Vulkan structs whose undersized declarations let drivers overflow caller storage; structs now come from the system `vulkan/vulkan.h` at compile time while entry points are still resolved via dlopen, and systems without Vulkan headers get an honest "unavailable" stub. PCI matching uses `vkGetPhysicalDeviceProperties2` and filters all-zero BDFs reported by software rasterizers. A new `daemon_dispatch` ctest (`src/tests/tests/test_daemon_dispatch.sh`) starts `mvgald` on an isolated socket and submits the reference workload through OpenCL, CUDA and Vulkan via `mvgal-exec` (`--api vulkan` added). See [Changelog](CHANGELOG.md) § v0.7.45.

## v0.7.44 execution updates

v0.7.44 adds CUDA, Vulkan, and SYCL daemon backend implementations/slots plus heterogeneous workload partition planning. The CUDA backend dynamically loads the CUDA driver and submits a reference PTX kernel. Vulkan command submission remains an explicit stub pending per-ICD integration; SYCL availability depends on a compatible oneAPI/DPC++ environment. The partition planner has a unit test, which validates planning logic rather than physical multi-vendor execution. See [Changelog](CHANGELOG.md) § v0.7.44.

## What the code provides

The source includes a Linux DRM-facing kernel module, GPU discovery and capability reporting, a userspace library/API, the `mvgald` runtime daemon, several API integration targets, management/diagnostic tools, Rust safety crates, language bindings, UI sources, tests and distribution packaging definitions. Exact components depend on build options, dependency discovery and package selection.

v0.7.43 makes the Vulkan ICD build on systems whose headers predate Vulkan
1.3. `src/userspace/vulkan_icd/CMakeLists.txt` only ran its compile check
when a Vulkan include directory had been discovered; otherwise it treated
"Vulkan was found" as "headers are 1.3 or newer", so pkg-config reporting a
1.2 SDK on openEuler 22.03 led to the ICD being compiled against 1.2 headers
and failing with `unknown type name 'VkPhysicalDeviceToolProperties'`. The
check now always runs, letting the compiler search its default include path
when no directory is reported, and the ICD target is skipped with a warning
when 1.3 headers are absent so the rest of MVGAL still builds there. See
[Changelog](CHANGELOG.md) § v0.7.43.

v0.7.38 makes the Vulkan command-buffer DAG compile against Vulkan 1.2
headers. openEuler 22.03 ships headers without `VkDependencyInfo` or
`PFN_vkCmdPipelineBarrier2`, so the recorded barrier payload is now an
opaque handle, the synchronization2 lowering helpers and the
`vkCmdPipelineBarrier2` slot are compiled only when the headers provide
them, and a recorded sync2 barrier on such a build reports
`VK_ERROR_FEATURE_NOT_PRESENT` instead of being silently dropped. Vulkan
1.3 behaviour, including runtime lowering to `vkCmdPipelineBarrier`, is
unchanged. See [Changelog](CHANGELOG.md) § v0.7.38.

v0.7.37 fixes the two remaining openEuler 22.03 build failures.
`vk_layer.c` uses `VK_API_VERSION_1_3` to advertise its spec and instance
API version, and that constant only exists in Vulkan headers from
1.2.170; a local `VK_MAKE_API_VERSION(0,1,3,0)` fallback keeps the layer
compiling on older headers. The spec now builds whichever directory
actually received the CMake cache: openEuler configures in-source while
its `cmake_build` macro expects an out-of-tree `x86_64-openEuler-linux-gnu`
directory that was never created.

v0.7.36 defines `cmake_build`/`cmake_install` fallbacks for chroots that
ship no `cmake-rpm-macros`. On openEuler the macro was left undefined, so
the literal token reached the build script and bash read it as a job
specification, aborting with `fg: no job control` after a successful
configure. Fedora, RHEL and SUSE are unaffected and keep the standard
out-of-tree macro path.

v0.7.35 removes the hard requirement on `drm/drm.h` in
`runtime/daemon/kernel_ioctl_types.hpp`, using `__has_include()` plus
equivalent `_IOC` definitions for `DRM_IOWR` and `DRM_COMMAND_BASE`. This
unblocks openSUSE Leap 16 on both architectures and Mageia Cauldron
aarch64, and generates identical ioctl numbers. `mvgal-config` also
reloads a running daemon after saving a strategy and says whether the
change is live, matching `mvgal set-strategy`.

v0.7.34 fixes the root cause of the module-unload wedge. The idle-gate
sweep re-queued itself unconditionally, so `cancel_delayed_work_sync()`
never returned during teardown and `mvgal` stayed in `MODULE_STATE_GOING`
(`Unloading`, refcount `-1`) with `/dev/mvgal0` unopenable (`ENXIO`) until
reboot; the sweep now honours a stopping flag set before cancellation.
The spec also stops putting section macros in comments (rpm parsed one as
a real marker and reported a second install section) and drops the
build-time `dkms` dependency.

v0.7.33 is the release that closes the 0.7.32 test report. **C1/C2/H1/M6**
— every tool now shares `tools/mvgal_device_state.h`, which actually opens
`/dev/mvgal0` and reports not-loaded, wedged, loaded-but-unusable or OK
instead of trusting `stat()`. **H4** — unload-module detects the wedged
state up front, uses a non-blocking rmmod, names the modules that really
hold the reference, never suggests rmmod for unloaded modules, and the
helper no longer leaks shell `Killed` notices. **M5** — `mvgal restart` on
a stopped daemon says it started it. **L2** — bash, zsh and fish
completions ship. **L3** — only user-facing documentation is installed.
**L6** — no blank line before the JSON closing brace. Shader
intermediate-format detection and routing was added for SPIR-V, PTX,
cubin, fatbin, hsaco, LLVM IR/bitcode, assembly and Intel GEN. The 0.7.33-2
rebuild fixed aarch64 (`__builtin_ia32_pause()` was used unconditionally),
made the `.modinfo` dma-buf record identical across kernel releases via
`MODULE_IMPORT_NS()`, and guarded `Recommends` for RPM older than 4.12.

v0.7.32 fixes seven issues from the 0.7.31 test report: unload-module always
failed because the core module has hard dependents; bench --json produced
invalid JSON; set-strategy suggested --force but did not implement it;
the shipped config used round_robin on single-GPU installs; -c with an
unreadable file exited 0; mvgal-probe reported zeros for PCIe/BAR/subsystem;
and mvgal-gui hung with no display. See [Changelog](CHANGELOG.md) § v0.7.32.

v0.7.31 is a field-report-driven correctness release addressing the 0.7.30 test report on a single-GPU Secure Boot host (Fedora 43, kernel 7.2.13-200.fc44.x86_64, Intel UHD Graphics 770, plus a blacklisted MTT S30). COPR build #11229933 succeeded on `fedora-43-x86_64`. Key fixes: **C1** — the kernel module now includes `PCI_CLASS_DISPLAY_OTHER` (0x0380) so Intel integrated GPUs are found alongside discrete cards, and skips display-class PCI devices whose native driver is not bound (blacklisted MTT S30), so kernel and userspace enumeration agree on GPU indices; **C2** — `mvgal_mtt.c` now checks `MVGAL_FULL_STACK` (the real compile-time guard) instead of the non-existent `CONFIG_MVGal_MTT` typo, and the `find_module()` calls removed from kernel 7.x are replaced by a `/proc/modules` read; **C3** — udev rules and the pkexec helper now set `GROUP="mvgal"` and `MODE="0660"` (were `GROUP="video"` and `MODE="0666"`); **H1** — `mvgal-enum` and `mvgal list-gpus` now scan PCI for display-class GPUs with no DRM node and warn about present-but-unusable devices; **H2** — `mvgal start` now checks for `/sys/module/mvgal` after launching the daemon and prints a degraded-mode warning if the kernel module is absent.

v0.7.30 is a field-report-driven correctness and packaging release from the 0.7.30 test campaign on a single-GPU Secure Boot host (Fedora 44, kernel 7.2.12-200.fc44.x86_64, Intel UHD Graphics 770). Multi-GPU aggregation could not be exercised (single GPU), and the kernel module path remains unavailable under Secure Boot until the MOK is enrolled (see [SECURE_BOOT.md](SECURE_BOOT.md)). The headline fixes: `mvgal-vulkan-env.sh` no longer forces `VK_ICD_FILENAMES`/`VK_DRIVER_FILES` to *only* the MVGAL aggregating ICD (which reports zero devices when the kernel module is absent), defaulting to `MVGAL_ICD_ONLY=0` so vendor ICDs are preserved; the OpenCL ICD reports zero platforms when the kernel module is absent instead of exposing a half-working platform whose context creation fails; the GUI dashboard status cards auto-refresh on startup via a single-shot `QTimer` instead of staying "Checking…"; `mvgal-bench compute` and other single-suite paths now print the "What is actually measured" caveat like `all`; usage/error paths are standardized to exit `2` across tools (documented in man pages); the two configuration log lines are `DEBUG`-only and gated behind `--verbose`; `%post` removes leftover `/etc/OpenCL/vendors/mvgal.icd.disabled`; man pages were added for `mvgal-gui`, `mvgal-dashboard`, `mvgal-load`, `mvgal-unload`, `mvgal-workload`, `mvgal-probe`; and `mvgal-daemon.preset` (disabled) documents that `%post` enables the unit on first install. COPR build #11217288 succeeded on all 18 enabled chroots.

v0.7.29 is a test-report-driven correctness release addressing 15 issues from the v0.7.28 field validation on a single-GPU Secure Boot host. The headline fixes: the Vulkan layer activation variable was documented as `VK_LAYER_MVGAL=1`/`ENABLE_MVGAL=1` but the manifest only enables on `MVGAL_VULKAN_ENABLE=1`; `/etc/mvgal` is now explicitly `0755 root:root` in the package (was `0775 group:mvgal`, a privilege-escalation path); `mvgal status` and `mvgal-status` now use a three-tier exit code (`0` healthy, `1` degraded, `2` daemon down) instead of always returning `1`; benchmark subcommands forward `mvgal-bench` output instead of suppressing it; `mvgal set-strategy` now refuses multi-GPU strategies on single-GPU machines; `mvgal-config show-config` handles `ENUM`-typed entries and shows only the effective view by default; `-c/--config` now rejects paths outside `/etc/mvgal/`; start/stop are idempotent (exit 0 when already in the target state); the OpenCL ICD park location moved to `/usr/lib/mvgal/`; `mvgal-workload` skips the MVGAL aggregating ICD platform to avoid double-counting; `mvgal-probe` demotes its `/dev/mvgal0` open failure to a notice; and `listen_addr` defaults to `127.0.0.1`.

v0.7.28 is a correctness and packaging release. The CUDA shim reported
the MVGAL GPU count from `cuDeviceGetCount`/`cudaGetDeviceCount` instead
of the native driver's, and mapped CUDA ordinals to MVGAL GPUs by modulo,
so CUDA device 0 (RTX 3050) was attributed to MVGAL GPU 0 (Intel Arc).
The shim now probes each ordinal's PCI BDF once and matches it against
the NVIDIA MVGAL GPUs, passes native counts through, rejects the `-1`
sentinel before context creation, allocation and launch (the old
`mvgal_gpu < gpu_count` guard was true for `-1`), restricts kernel
launches to eligible GPUs, and lets `MVGAL_CUDA_DEBUG=1` raise the log
level. A new `test_cuda_multidevice` harness brings ctest to 27/27
(4.73 s). The release also adds a Windows cross-compilation packaging
pipeline (NSIS and WiX installers from `Jenkinsfile.windows`), and the
RPM ships a `systemd-sysusers` fragment so the `mvgal` group is declared
before dependency resolution — `dnf install` no longer fails with
`nothing provides group(mvgal)`. See [Changelog](CHANGELOG.md) § v0.7.28.

v0.7.27 fixes three hardware-detection and reporting defects. The Vulkan
ICD filename check did not match Fedora's `radeon_icd.x86_64.json`, so
AMD GPUs were reported as having no Vulkan driver; the AMD shader-backend
probe pointed at mesa's software rasterizer instead of RADV; the WoW64
layer check only looked in `/usr/lib` and reported "not built" on a
correctly installed multilib Fedora package; and `mvgal-info` left
NVIDIA temperature and utilization at their `-1` sentinel — the
proprietary driver exposes no hwmon source for them — and now fills
only those empty fields via NVML, never fabricating a value. See
[Changelog](CHANGELOG.md) § v0.7.27.

v0.7.26 is a packaging release with no runtime behaviour changes. The RPM
files list now always includes `mvgal-workload`, which the build produces
whenever CMake finds OpenCL — the previous conditional listing made a
Fedora build that found OpenCL fail in `%install`. The AppImage
dependency self-check now resolves `not found` entries and verifies
against the staged `usr/lib`, and the application icons are normalized
to 256×256 for the Flatpak, RPM and AppImage exports. See
[Changelog](CHANGELOG.md) § v0.7.26.

v0.7.25 is a packaging and reporting release. Its headline defect made the
modules unloadable and the documented Secure Boot recovery unable to
repair them: the modules were compressed with `xz -9e`, producing a
CRC64 xz stream that the kernel's decoder rejects (it accepts CRC32 and
below), so the module failed at *decompression* — before the signature
was examined. A user who enrolled the MOK correctly still had a system
that would not load MVGAL, and the journal pointed at a signature problem
that was not the cause. CRC64 is xz's default check at every compression
level, so `xz -9` was equally broken. v0.7.25 uses the kernel's own
settings from `scripts/Makefile.modinst`
(`xz --check=crc32 --lzma2=dict=1MiB`), which is also byte-identical to
what DKMS builds.

Two related gaps were closed with it: the daemon had chowned systemd's
`RuntimeDirectory`, which made every `systemctl reload mvgald` fail with
`status=233` while `restart` kept working; and SIGHUP was installed but
the handler had no case for it, so a reload did nothing and reported
success. The remainder of the release is reporting: the Vulkan probe
called a staged manifest "ACTIVE", the D-Bus methods were registered
without `SD_BUS_VTABLE_UNPRIVILEGED` (so sd-bus refused every non-root
call and left the GUI and dashboard dead for members of the `mvgal`
group), the OpenCL ICD registration was frozen at install time, and a
multi-GPU strategy was accepted on a single-GPU host. See
[Changelog](CHANGELOG.md) § v0.7.25.

The 0.7.23–0.7.24 releases mainly fixed correctness and observability issues found by packaging and exercising the installed system. The latest audit fixed daemon device access and D-Bus name ownership checks; PCIe generation, NUMA and class-code reporting; sysfs setup and kernel work/reference lifecycle defects; GPU memory totals; and inert power-control paths. It added `mvgal-workload`, an end-to-end OpenCL workload gate requiring at least two distinct vendors. See [Changelog](CHANGELOG.md) for the full source-derived details.

## Runtime boundaries

- The kernel module is above-driver discovery/control scaffolding. It does not take ownership of GPU PCI functions; native vendor drivers remain in charge of GPU submission and their memory managers.
- Capabilities are intended to come from runtime probes. Unsupported kernel submission and VRAM allocation are not made functional by ioctl declarations or adapter files; callers must honor explicit unsupported results and fallbacks.
- The Vulkan layer and Vulkan ICD are distinct components. The ICD does not provide a fabricated physical device representing multiple vendors.
- API interception, strategy identifiers and memory APIs do not prove safe work distribution. Correctness depends on workload/API semantics, available backend operations and probed capabilities.
- DMA-BUF/P2P paths depend on the device pair and driver support. Host staging is the fallback where supported by the particular userspace path.
- Moore Threads and Adreno adapters and Windows/Steam compatibility code are experimental integration surfaces. Treat each as unvalidated until the exact hardware, driver and workload path has been exercised.

## Build and validation

CMake is the primary broad build; Meson and Cargo cover separate portions. Optional dependencies and build switches determine which targets exist. Unit/integration tests, synthetic topology, successful package builds and physical multi-vendor validation provide different evidence and should be reported separately. The synthetic topology backend is a test fixture and does not create devices.

The source test table records 27/27 CTest tests (4.73 s, measured 2026-10-25) and 71/71 across the full suite, including the new `test_cuda_multidevice` and `uapi_probe` on the three-vendor bench host (AMD Navi 24, NVIDIA RTX 3050, Intel Arc A380). That is bench evidence for that host, not a universal hardware claim.

The 2026-11-14 validation pass on the same three-vendor host (kernel 7.3.3-300.fc45, Fedora 45, Mesa 26.2.6, NVIDIA driver 620.70.06) records `ctest` 32/32 passed (7.94 s) in `build_check` and 30/30 (7.85 s) in `build_output`, plus a per-GPU × per-API dispatch matrix: OpenCL, CUDA and Vulkan all `COMPLETE` on the NVIDIA GPU; Vulkan `COMPLETE` on the Intel Arc A380 and AMD RX 6400 with OpenCL also complete there; CUDA pinned to non-NVIDIA GPUs returns an honest `ERROR (error_code=6)` rather than faking success. The new `daemon_dispatch` test exercises real daemon IPC dispatch for all three backends including element-range partitioning across physical GPUs. The SYCL backend remains an honest stub — no oneAPI runtime exists on the host. This is dated bench evidence for that host, covering only the embedded reference kernel, not arbitrary workloads, graphics paths, DMA-BUF/P2P transfers, hotplug, or MTT hardware.

The source changelog's 0.7.24 known-issues entry records a PCI enumeration reference-lifetime fix that still needs a clean-boot hardware check on the host where it was found; the 0.7.28 entry does not restate it. The 2026-10-25 bench run (ctest 27/27, including `uapi_probe`, on the three-vendor bench host) does not substitute for that check on the affected machine. Do not turn this source-level fix into a claim of completed physical validation.

## Package state

This docs repository's `package/` directory contains **0.7.44** RPM, DEB, AppImage, tarball and Flatpak artifacts as of this update. The current source release, **0.7.46**, has had its SRPM built cleanly and submitted to COPR: build **11324792** succeeded on **all 60 enabled chroots** in the project on the first attempt, covering `fedora-43/44/45`, `fedora-eln`, `fedora-rawhide`, `rhel` and `epel` 8–10, `almalinux-9/10`, `almalinux-kitten-10`, `centos-stream-8/9/10`, `amazonlinux-2023/2027`, `opensuse-leap-16.0`, `opensuse-tumbleweed`, `mageia-9/10` and `openeuler-22.03/24.03` on x86_64 and aarch64. Chroots that cannot build for environmental reasons — `openeuler-20.03` (CMake 3.17), `mageia-8` (end of life), `mageia-cauldron` (mirror failures), `epel-7`/`rhel-7` (archive gone), `centos-stream+epel-next-8` (unreachable metadata) and `custom-1` (empty chroot) — were removed from the project instead of being left permanently red. Its package README and individual manifests should be consulted for exact contents. Presence here does not establish that a remote repository has published the same version or that the artifacts have passed hardware validation.

## Further reading

- [Architecture](ARCHITECTURE.md) and [Codebase Map](CODEBASE.md)
- [Hardware Compatibility](HARDWARE_COMPATIBILITY.md)
- [Build Guide](BUILD.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Source changelog mirror](CHANGELOG.md)
