---
tags: [mvgal, changelog, reference]
aliases: [Changelog, Release Notes]
mvgal_version: "0.7.31"
mvgal_verified: 2026-10-30
mvgal_role: reference
mvgal_order: 13
---

# Changelog

All notable changes to MVGAL (Multi-Vendor GPU Aggregation Layer) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.7.31] - 2026-10-30

Field-report-driven correctness release addressing the 0.7.30 test report on a
single-GPU Secure Boot host (Fedora 43, kernel 7.2.13-200.fc44.x86_64, Intel
UHD Graphics 770, plus a blacklisted MTT S30). COPR build #11229933 succeeded
on `fedora-43-x86_64`.

### Fixed

- **C1 — Kernel module and userspace disagreed on GPU identity/index.** The
  kernel module enumerated the MTT S30 via PCI and assigned it GPU index 0, but
  userspace (DRM/sysfs) could not see it (driver blacklisted) and assigned index
  0 to the Intel GPU instead. `mvgal_enumerate_gpus()` now includes
  `PCI_CLASS_DISPLAY_OTHER` (0x0380) so Intel integrated GPUs are found
  alongside discrete cards, and skips display-class PCI devices whose native
  driver is not bound — `mvgal_native_driver()` checks `pdev->driver`, which is
  `NULL` when no driver owns the function. The userspace device registry
  (`enumeratePciDevices`) applies the same class filter and warns when a PCI
  GPU has no DRM node. Both sides now agree on which GPUs exist and their
  indices. The Intel PCI ID `0x4680` comment is corrected from "DG2" to
  "UHD Graphics 770 (Alder Lake)".
- **C2 — Contradictory MTT backend messages.** `kernel/vendors/mvgal_mtt.c`
  checked the non-existent `CONFIG_MVGal_MTT` (a typo for `CONFIG_MVGAL_MTT`
  that never appeared in any Kconfig), so `MVGAL_MTT_ENABLED` was always 0 and
  `mvgal_mtt_init()` returned `-ENOTSUPP`, producing the contradictory messages
  "Registered Moore Threads GPU backend" (from `mtt_main.c`) followed by
  "Moore Threads support not compiled in" (from `mtt.c`). The guard is now
  `MVGAL_FULL_STACK`, the real compile-time symbol from `Kbuild` ccflags. The
  `find_module("mtgpu")` / `find_module("mtgpu_drv")` calls — removed from the
  kernel symbol table in 7.x and causing a `modpost` build failure — are
  replaced by a `/proc/modules` read via `filp_open` + `kernel_read`.
- **C3 — Group/permission mismatch locked users out of `/dev/mvgal0`.** The
  udev rules `config/99-mvgal.rules` and `packaging/99-mvgal.rules` set
  `GROUP="video"` and `MODE="0666"`, but the daemon and CLI tools use the
  `mvgal` group. Users in `video` but not `mvgal` were locked out of
  `/dev/mvgal0` despite being members of the video group. Both rules now set
  `GROUP="mvgal"` and `MODE="0660"`. The privileged helper
  (`mvgal-pkexec-helper.sh`) now `chown root:mvgal` (was `root:video`) on
  device nodes after module load.
- **C4 — `listen_addr` already correct.** The `[network]` section default was
  confirmed as `127.0.0.1` from v0.7.30; no code change needed.
- **H1 — Blacklisted GPUs were silently omitted.** The MTT S30 was present on
  PCI but invisible to MVGAL because its driver was blacklisted, with no warning.
  `mvgal-enum` and `mvgal list-gpus` now scan `/sys/bus/pci/devices/` for
  display-class PCI devices (classes 0x0300, 0x0302, 0x0380) with known GPU
  vendor IDs (AMD 0x1002, NVIDIA 0x10de, Intel 0x8086, MTT 0x1ed5), check
  whether each has a DRM card node, and print a warning to stderr when a GPU has
  no DRM node — naming the PCI BDF, vendor, and the likely cause (blacklisted or
  missing driver). The daemon's `DeviceRegistry::enumeratePciDevices()` emits
  the same warning with the bound driver name (or "no driver bound").
- **H2 — `mvgal start` did not report degraded mode.** After launching the
  daemon successfully (both systemd and fork paths), `mvgal start` now checks
  for `/sys/module/mvgal` and prints a degraded-mode warning to stderr if the
  kernel module is absent or failed to load, with remediation steps (enroll
  the MOK, then `pkexec mvgal-load`).

### Added

- **MTT S30 PCI ID in the kernel table.** `{ PCI_DEVICE(0x1ED5, 0x0102) }` is
  now in the `mvgal_gpu_pci_ids[]` table (`kernel/mvgal_core.c`), so the MTT S30
  is recognized when its driver is bound.

### Packaging

- COPR build #11229933 succeeded on `fedora-43-x86_64`.

## [0.7.30] - 2026-10-28

Field-report-driven correctness and packaging release from the 0.7.30 test
campaign on a single-GPU Secure Boot host (Fedora 44, kernel
7.2.12-200.fc44.x86_64, Intel UHD Graphics 770). Multi-GPU aggregation could
not be exercised (single GPU); the kernel module path remains unavailable
under Secure Boot until the MOK is enrolled (see [SECURE_BOOT.md](SECURE_BOOT.md)).
COPR build #11217288 succeeded on all 18 enabled chroots.

### Fixed

- **The Vulkan aggregated ICD opt-in broke every Vulkan app** ([2], [13]) — `mvgal-vulkan-env.sh` set `VK_ICD_FILENAMES`/`VK_DRIVER_FILES` to *only* `/usr/share/vulkan/mvgal/mvgal_icd.json` (with `MVGAL_ICD_ONLY=1`). That ICD deliberately reports zero physical devices when the kernel module is absent, so sourcing the script made `vulkaninfo` and every Vulkan app see no GPU at all. The script now defaults to `MVGAL_ICD_ONLY=0`, preserving the loaded vendor ICDs as fallback; the duplicate `MVGAL_VULKAN_ENABLE` export and the stale `VK_LAYER_PATH` are normalised, and `MVGAL_PREFIX` defaults to `/usr`. Sourcing the script no longer disables the vendor renderer.
- **OpenCL ICD exposed a half-working platform when the kernel module was absent** ([5]) — `libmvgal_opencl.so` now reports 0 platforms (stepping aside) when the kernel module is not loaded/degraded, instead of exposing a platform whose context creation fails.
- **GUI dashboard status cards stayed "Checking…" forever** ([6]) — `MainWindow` now auto-refreshes the status cards on startup via a single-shot `QTimer`, so they resolve to real values instead of never firing.
- **Benchmark caveats were missing from single-suite paths** ([8]) — `mvgal-bench compute` (synthetic) and other single-suite invocations now print the "What is actually measured" caveat block in the same form as `all`, so the host-proxy vs. GPU distinction is unambiguous.
- **Tools disagreed on the usage/error exit code** ([9], [17]) — usage/error paths are standardised to exit `2` across the CLI tools; `mvgal --help`/`--version` exit `0`. The contract is documented in the man pages.
- **Configuration log lines spammed stderr before logging was initialised** ([10]) — the two configuration log lines are now `DEBUG`-only and gated behind `--verbose`, so unstripped CLI output no longer falls through to stderr before `mvgal_log_init`.
- **A stale parked OpenCL ICD could be picked up after upgrade** ([11]) — the RPM `%post` now removes any leftover `/etc/OpenCL/vendors/mvgal.icd.disabled` at install time (the park now lives at `/usr/lib/mvgal/mvgal.icd.parked`).
- **`mvgal-dmabuf-matrix` leaked build-instruction text into its cdoc header** output ([12]) — the stray lines are removed.

### Added

- **Man pages** ([16]) — added `mvgal-gui`, `mvgal-dashboard`, `mvgal-load`, `mvgal-unload`, `mvgal-workload` and `mvgal-probe`.
- **`mvgal-daemon.preset`** ([19]) — a disabled preset documenting that `%post` enables the unit on first install.

### Packaging

- COPR build `#11217288` succeeded on all 18 enabled chroots. The Qt GUI is not built on `amazonlinux-2023` (the spec skips its Qt build-requires there via `%if ! 0%{?amzn}`), but that build still succeeds.

## [0.7.29] - 2026-10-27

Test-report-driven correctness release addressing 15 issues from the v0.7.28
field validation on a single-GPU Secure Boot host (Fedora 44, kernel
7.2.11-200.fc44.x86_64, Intel UHD 770). COPR build #11212845 succeeded on all
enabled chroots.

### Fixed

- **Vulkan layer activation env var was wrong in `--help` and all Steam/compat scripts.** Every user-facing path told users to set `VK_LAYER_MVGAL=1` or `ENABLE_MVGAL=1`, but the layer manifest only enables on `MVGAL_VULKAN_ENABLE=1`. Users following the docs got no Vulkan interception. All references corrected across `mvgal --help`, `mvgal-config`, `mvgal-steam-setup`, `mvgal-vulkan-env.sh`, `mvgal_steam_compat.sh`, and `README.md`.
- **`/etc/mvgal` was group-writable (0775 root:mvgal) with no sticky bit.** Any user in the `mvgal` group could unlink and replace root-owned files there; combined with `strategy = custom` being settable by unprivileged users and reloaded by the root daemon, this was a local privilege-escalation path. The RPM `%post` now explicitly `chmod 0755` + `chown root:root` the directory and forces `custom_strategy.lua` to `0644 root:root`; `%files` declares `%dir %attr(755,root,root)` for `/etc/mvgal`.
- **`mvgal status` always exited 1, even when the daemon was running.** Both `mvgal status` and `mvgal-status` now use a three-tier exit code: `0` = healthy (daemon running + module loaded), `1` = degraded (daemon running, module absent), `2` = daemon down. On a Secure Boot machine with an unenrolled key, the code is `1`, not `0`.
- **Benchmark subcommands printed "No workload data" and exited 0.** `mvgal benchmark`, `bench-synthetic`, `bench-realworld`, and `bench-stress` invoked `mvgal-bench` with `>/dev/null 2>&1`, suppressing all output, and then read zero in-process counters. They now forward `mvgal-bench`'s stdout/stderr directly and propagate its exit code.
- **`mvgal set-strategy` did not validate multi-GPU requirements.** It accepted `afr`, `sfr`, `round_robin`, `hybrid`, `task`, and `compute_offload` on a single-GPU machine, while `mvgal-config set-strategy` already refused them. The CLI now calls `strategy_requires_multiple_gpus()` and `mvgal_gpu_get_count()` before proceeding; `--force` overrides.
- **`mvgal-config show-config` rendered `ENUM`-typed entries as "(unsupported type)".** `log_level` and `scheduler.strategy` (both `MVGAL_CONFIG_ENUM`) now print their integer value. The default view also returns early after showing the effective configuration — `--raw` is required to see the literal file.
- **`-c/--config` path constraint was not enforced.** The CLI accepted any path; only the pkexec helper validated it. The CLI now rejects paths that are not a `*.conf` inside `/etc/mvgal` (after symlink resolution), matching the helper's check.
- **`mvgal start` returned exit 1 when already running** (via both systemd and `pidof`). Now exits 0 with an informational message.
- **`mvgal stop` returned exit 1 when not running** (via both systemd and `pidof`). Now exits 0 with an informational message.
- **OpenCL ICD park file was at `/etc/OpenCL/vendors/mvgal.icd.disabled`.** Because it sat in the loader's scan directory, some distributions picked it up during rescan. The parked manifest now lives at `/usr/lib/mvgal/mvgal.icd.parked`, outside the scan path entirely; the force-unregister action creates `/usr/lib/mvgal/` if missing.
- **`mvgal-workload` counted the MVGAL aggregating ICD platform as a second device.** On a single GPU it reported 2 devices and refused to run. It now skips the platform whose `CL_PLATFORM_VENDOR` is `"Multi-Vendor GPU Aggregation Layer"`, counting each physical GPU once.
- **`mvgal-probe` printed a scary "Failed to open /dev/mvgal0" error on systems without the kernel module.** The message is demoted to a notice: "kernel module not loaded; falling back to DRM".
- **`listen_addr` defaulted to `0.0.0.0`** in `[network]`. Changed to `127.0.0.1` so the listener (when enabled) only accepts local connections.
- **Steam profiles directory (`steam/steam_profiles/`) shipped 3 profile files but no directory listing.** The RPM `%files` now includes the directory as `%{_sysconfdir}/mvgal/steam_profiles/`.
- **`mvgal-steam-setup --help` exited non-zero with no arguments.** Fixed to exit 0.

### Packaging

- COPR build #11212845 succeeded.
- `/etc/mvgal` and `custom_strategy.lua` permissions hardened as described above.
- OpenCL ICD park path updated in `%files` and `mvgal-opencl-icd.sh`.

## [0.7.28] - 2026-10-25

Phase C (documentation gap closure) and Phase D (CUDA shim multi-device
correctness) of the 2026-10-25 full campaign, validated on the physical
three-vendor bench (AMD Navi 24 + NVIDIA RTX 3050 + Intel Arc A380).

### Fixed

- **CUDA device counts pass through natively.** `cuDeviceGetCount` /
  `cudaGetDeviceCount` no longer return the MVGAL GPU count; the fabricated
  override is gone.
- **CUDA ordinal → MVGAL GPU attribution is BDF-based.** A one-time PCI
  BDF probe replaces the modulo mapping that sent CUDA device 0 (RTX 3050)
  to MVGAL GPU 0 (Intel Arc).
- **No more out-of-bounds GPU indexing.** The `-1` sentinel is rejected by
  `>= 0` checks in `cuCtxCreate`, `cuMemAlloc`, `cuLaunchKernel`, and the
  runtime launch path; the old `mvgal_gpu < gpu_count` guard was true for
  `-1`.
- **Kernel launches are restricted to eligible GPUs.**
- **`MVGAL_CUDA_DEBUG=1` actually raises the log level**, so the
  `cuCtxCreate: CUDA device=N -> MVGAL GPU=M` attribution line is visible.

### Added

- **`test_cuda_multidevice`** — LD_PRELOAD integration harness asserting
  ordinal resolution, BDF set equality, and `cuCtxCreate` attribution.
  ctest is now 27/27 (4.73 s) on the bench.
- **Documentation:** Phase D addendum in `HARDWARE_VALIDATION_2026-10-25.md`;
  `POWER_MANAGEMENT.md`, `WINDOWS_COMPAT.md`, `STATUS.md`, and
  `SPEC_COMPLIANCE.md` gap closures (findings 4/5 resolved, 6 partially
  addressed).

## [0.7.27] - 2026-10-24

Fixes three hardware-detection and reporting defects that made valid
hardware look missing or report no stats.

### Fixed

- **AMD ICD detection now matches Fedora's `radeon_icd` manifest.** The
  Vulkan ICD filename check only matched `amd`/`radv`/`intel`/`mtt`
  substrings, but Fedora ships mesa's manifest as `radeon_icd.x86_64.json`,
  which contains none of them, so AMD GPUs were reported as having no
  Vulkan driver. The matcher now also accepts `radeon`/`radv` for AMD.
- **AMD shader-backend library list no longer probes lavapipe.** The list
  pointed at mesa's software rasterizer (`libvulkan_lvp.so`), not an AMD
  driver. It now probes the real RADV paths (`libvulkan_radeon.so` in the
  Fedora/RHEL/Arch and Debian layouts).
- **WoW64 layer detection accepts the `/usr/lib64` install path.** Multilib
  Fedora installs `libmvgal-wow64.so` under `/usr/lib64`, not `/usr/lib`, so
  the WoW64 check reported "not built" on a correctly installed package.
  Both paths are now checked.
- **`mvgal-info` reports NVIDIA temperature and utilization.** The
  proprietary NVIDIA driver exposes no hwmon `temp1_input` and no
  `gpu_busy_percent`, so those fields were left at their `-1` "unavailable"
  sentinel. `mvgal-info` now queries NVML (already linked in) for
  temperature and utilization by PCI bus id, filling only the fields sysfs
  left empty and leaving the sentinel when NVML is unavailable — never
  fabricating a value.

## [0.7.26] - 2026-10-24

Packaging release. No runtime behaviour changes.

### Fixed

- **`mvgal-workload` could be built but not packaged.** The tool is built
  whenever CMake finds OpenCL, while the RPM files list made its
  inclusion conditional, so a Fedora build that found OpenCL failed in
  `%install` with `Installed (but unpackaged) file(s) found:
  /usr/bin/mvgal-workload`. The files list now always includes the
  binary that the build produces.
- **The AppImage dependency self-check failed on a library it had just
  staged.** The `ldd` walk now resolves `soname => not found` entries
  instead of skipping them, and the final check runs with
  `LD_LIBRARY_PATH` pointing at the staged `usr/lib`, so `mvgal-probe`
  and its `libmvgal.so.0` dependency are verified inside the image
  rather than against the host.
- **Icon dimensions broke the Flatpak build.** The application icons
  were 1056×1024; the exported hicolor icons are normalized to
  256×256, which is the size the manifest installs and the size the
  RPM and Flatpak packages ship.

## [0.7.25] - 2026-10-22

Packaging and reporting release. The headline defect made the modules
unloadable, and the documented Secure Boot recovery could not have
repaired it.

### Fixed

- **Signed modules could not be decompressed by the kernel.** The modules
  were compressed with `xz -9e`, producing a CRC64-checked xz stream. The
  kernel's xz decoder rejects any check type above CRC32
  (`lib/xz/xz_dec_stream.c`), and it carries only an internal CRC32
  implementation. The module failed at decompression with `Invalid
  parameters` and `decompression failed with status 6` — before the
  Secure Boot signature was examined, so **enrolling the MOK could not fix
  it**. CRC64 is xz's default check at every compression level, so `xz -9`
  was equally broken. v0.7.25 uses the kernel's own settings from
  `scripts/Makefile.modinst` (`xz --check=crc32 --lzma2=dict=1MiB -f`),
  which is byte-identical to what DKMS builds.
- **A module already signed with the MVGAL key was never repaired.** The
  "already signed" check compares the decompressed image, so a module
  signed by v0.7.21/v0.7.22 was left with its unloadable container intact
  and the upgrade silently fixed nothing.
- **Enrolling the MOK now also makes the modules loadable**:
  `mvgal-enroll-mok` re-signs the installed modules before queueing the
  certificate.
- **`systemctl reload mvgald` failed permanently** (`status=233`): the
  daemon chowned systemd's `RuntimeDirectory=/run/mvgal` to `root:mvgal`,
  and systemd requires `root:root`. The daemon no longer touches the
  directory's ownership.
- **A reload did nothing.** SIGHUP was installed but the handler had no
  case for it, so a reload signalled the daemon and reported success
  while nothing happened. The daemon now re-reads the configuration on
  SIGHUP.
- **"Vulkan aggregated ICD: ACTIVE" was a false positive** — the staging
  copy in the opt-in directory was treated as a registration. The ICD now
  reports registered / available / absent.
- **The OpenCL ICD registration was decided once, from a stale snapshot**,
  so on a host where the vendor runtime was installed after MVGAL it
  stayed parked and every OpenCL application ran without MVGAL in the
  path. The decision moved to `/usr/lib/mvgal/mvgal-opencl-icd.sh` and the
  manifest is registered by default.
- **Module load failures were always blamed on Secure Boot.** The loader
  used `insmod` on a path `modinfo` can legitimately return compressed
  (`.ko.xz`), which `insmod` cannot load, and then printed the MOK
  remedy for a failure enrollment could not fix. It now uses `modprobe`
  first and classifies the failure.
- **The D-Bus API refused every non-root call.** The methods were
  registered without `SD_BUS_VTABLE_UNPRIVILEGED`, so sd-bus applied its
  own default policy and rejected them with `AccessDenied` regardless of
  the bus policy that allows the `mvgal` group.
- **A multi-GPU strategy was accepted on a single-GPU machine.** It is now
  checked against the detected GPU count in three places.
- **`mvgal-config list-gpus` reported shared system RAM as dedicated
  VRAM**, without the caveat `mvgal-info` gave.
- **`mvgal-compat` exited 0 while reporting "Not operational"**, and
  `mvgal-dashboard --check` printed "daemon not running" and then "OK".
  Both now have meaningful exit codes.
- **`mvgal-steam-setup --check` reported two false results** — it checked
  for `libmvgal.so` on disk rather than the runtime, and looked for a
  Steam compatdata directory rather than the `mvgal-compat` binary.
- **Every vendor shader backend was skipped, even for a present GPU**,
  because the check only knew the Debian library layout.
- **The DKMS build and the packaged modules used two different layouts and
  compression conventions**, so `rpm -V` and `dkms status` both reported
  them as mismatched.
- **`mvgal-config show-config` dumped the raw file** rather than the
  effective configuration the daemon runs on. `--raw` now prints the file.
- **`/etc/OpenCL/layers` was missing**, so the loader warned on every run.
- **The pkexec log was world-readable** and recorded configuration
  values.
- **`/var/log/mvgal` was created and never written to.**
- **The key directory was 0700 root**, so the documented
  `mvgal-signing.der` path was unreadable by the group it exists for. It
  is now 0750 root:mvgal, with the public certificate at 0640 and the
  private key still 0600.
- **Stale DKMS build trees accumulated** for every kernel the machine had
  ever had.
- **`[ai_scheduler] enabled = false` was never read**, so a default
  install complained on every start about a feature that was switched off.
- **`mvgal-config --help` demonstrated destructive global mutations**; the
  examples are now read-only.
- **`journalctl -u mvgald` returned nothing** because `journalctl` does not
  resolve unit aliases. The canonical name is `mvgal-daemon.service`.

### Notes

- The kernel's own module compression is
  `xz --check=crc32 --lzma2=dict=1MiB`; matching it exactly is what makes
  the signed module byte-identical to the DKMS-built one.
- The marker terminator in an appended module signature is a NEWLINE, not
  a NUL, and the 4-byte big-endian DER length sits 32 bytes before the end
  of the file.
- `sign-file` has no verify mode and re-signing APPENDS rather than
  replaces, so the signer strips any existing signature first.
- The Mageia 9 COPR chroot was removed from the upstream project: Mageia 9
  is end-of-life and its repository content has been purged from the
  mirrors, so every build failed at bootstrap with a mirrorlist 404 for
  reasons unrelated to the package. Builds now cover 18 chroots.

## [0.7.24] - 2026-10-18

Audit release: eleven defects found by exercising the installed package on a
three-GPU AMD/NVIDIA/Intel host, most of which had been silently disabling
parts of the system rather than failing visibly.

### Fixed
- Daemon: the systemd unit's `DeviceAllow=` used glob paths. systemd does not
  expand them, and their presence flipped the implicit `DevicePolicy` from
  `auto` to `closed`, so mvgald could open neither `/dev/mvgal0` nor any
  `/dev/dri/*` node. It ran permanently in userspace-only fallback while
  reporting only that the kernel device was unavailable. The allowlist is
  removed: the GPU node set depends on topology and udev render-node
  numbering, and GPUs hot-plug at runtime, so no static list can be correct.
- Daemon: surface `KernelDevice::lastError` when the kernel device cannot be
  opened. The errno was discarded, which is why the above went unnoticed --
  ENOENT and EPERM call for completely different investigations.
- Daemon: request the D-Bus name with `DO_NOT_QUEUE` and check the reply code.
  With flags=0 a taken name was queued and returned a positive value, so a
  takeover would have looked like success while every method call went to the
  other instance. Conflicts now name the owning pid instead of advising a
  dbus reload that could not help.
- Kernel: `pcie_gen`/`pcie_lanes` stored raw `enum pci_bus_speed` values, which
  are bus-speed codes rather than generations (`PCIE_SPEED_2_5GT` is 0x14). A
  Gen4 x16 GPU reported as "Gen 23 x16". Both are now decoded from the PCI
  Express capability register; the legacy wrappers also signal failure with
  `PCI_SPEED_UNKNOWN`, so the `>= 0` guard never fired.
- Kernel: `numa_node` used `dev_to_node()` on a PCI device, whose `dev` is never
  NUMA-aware, so it always read unknown. Now uses `pcibus_to_node()`, with a
  single-node fallback for hosts that have no ACPI/SRAT topology.
- Kernel: the `numa_node >= 0` guard was tautological on an unsigned field, so
  two GPUs with unknown nodes compared as same-node and P2P was admitted on
  the strength of a value carrying no information.
- Kernel: `class_code` was declared in the UABI and printed by mvgal-info, but
  no code ever assigned it. Every GPU reported `0x0000` instead of `0x030000`.
- Kernel: `mvgal_sysfs_init()` called `class_create("mvgal")` a second time
  when `mvgal_core.c` had already created it. The -EEXIST was swallowed, so the
  module reported a clean load while the documented per-GPU `capabilities`
  attributes did not exist -- and the stale class made every load after the
  first fail. sysfs_init now parents its per-GPU kobjects to the device kobject
  the core already registered instead of creating a competing class.
- Kernel: `mvgal_device_free()` cancelled the same delayed work twice, via
  `*_stop()` and again via `*_fini()`, tripping `WARN_ON` in `__flush_work` on
  every rmmod -- once per GPU. Both cancels are now guarded, which also makes
  `fini()` safe standalone. The DVFS work item had the same defect.
- Kernel: fix a use-after-free in PCI enumeration. `pci_get_device()` takes a
  reference on what it returns but not on the cursor it is handed, and the skip
  path released a reference on a cursor it did not own, so the next iteration
  walked freed memory. The cursor now owns one reference for the whole scan.
- Kernel: `*_init()` passed NULL as the delayed-work handler, so anything
  queuing the work before `*_start()` would have faulted.
- Tools: mvgal-info pooled an integrated GPU's shared system memory into
  "Aggregate VRAM", claiming a 66 GiB pool on a machine with 10 GiB of real
  VRAM. Dedicated VRAM and shared system RAM are now accumulated and reported
  separately.
- Daemon: `writeFrequency()` returned success without writing a clock, so the
  DVFS controller recorded clocks the GPU was never running at. It now reports
  clock control as unavailable and leaves last-known state intact.
- Daemon: the PSU headroom and power curve controllers both wrote
  `targetClockMhz`, which the DVFS controller rewrites from utilisation every
  tick, making both silently inert. Each now holds its own cap that the DVFS
  controller clamps against.
- Steam: shipped game profiles pinned `primary_gpu_mask = 0x3`, freezing them to
  a two-GPU machine regardless of hardware. Now `0`, which the scheduler already
  defines as "all GPUs".

### Added
- D1-D5 design/docs: narrow end-to-end userspace workload path (OpenCL ICD loader, host-staged, CPU reference validation)
- Tool: mvgal-workload (end-to-end OpenCL workload gate; validates >=2 distinct vendors)

### Changed
- Build: link mvgal-info with nvml_query.c and ${CMAKE_DL_LIBS} (standalone tool needs NVML helper)
- Kernel: PCIe link attributes are read from the capability register (maximum
  supported) rather than the status register, so a powered-down GPU reports its
  real capability instead of a negotiated width of zero.

- packaging: ship `/usr/bin/mvgal-workload`. The tool and its CMake install
  rule arrived in 0.7.23 but were never added to the RPM `%files`, so every
  COPR build since then has failed with "Installed (but unpackaged) file(s)
  found". It is built only when `find_package(OpenCL)` succeeds, so it is
  now listed under the existing `%bcond_without opencl`.

### Known issues
- The PCI enumeration use-after-free is source-verified only. On the host where
  it was found, earlier load/unload cycles had already driven a device refcount
  to zero, and such refcounts are not recoverable without a reboot. It needs a
  clean-boot check; `test_uapi_probe` fails on an affected machine because
  enumeration reports zero GPUs.

## [0.7.23] - 2026-10-18

### Fixed
- DKMS: ensure KERNELDIR is correctly resolved in kernel/Makefile and dkms.conf (fixes module build on kernel 7.2.11-200.fc44.x86_64)
- Userspace: fix NVIDIA VRAM reporting (0 GB) via NVML fallback by PCI BDF; aggregate VRAM correctly labels/excludes shared system memory
- Daemon: eliminate AMD frequency-set log spam by initializing C logger at INFO level (mvgal_log_init) so DEBUG messages are filtered
- Tools: mvgal-info shows full driver names (amdgpu/nvidia/i915); mvgal status displays VRAM with "(shared system memory)" for shared RAM

## [v0.7.22] - 2026-10-14

Fixes a Secure Boot packaging defect that made the documented remediation
impossible to complete, plus five reporting defects found by a black-box audit
of 0.7.21 on a Secure Boot host.

### Fixed

- **Modules were signed with two different keys, so Secure Boot could never be made to work.** `mvgal_ntsync.ko` — a hard dependency of `mvgal.ko` — was signed with DKMS's own key while every other module carried the per-machine MVGAL key, and `mvgal-enroll-mok` enrolled only the MVGAL key. A user could follow the printed instructions exactly and still get `Key was rejected by service`. Three faults combined: the signing loops globbed `"$dir/"*.ko`, which cannot match the `.ko.xz` a compression-enabled distro installs; they looked only in the kernel tree and `.../updates/dkms` when DKMS's real destination is distro-dependent (on Fedora, `.../extra`); and they discarded every failure, so the install reported success. Both loops are replaced by `/usr/lib/mvgal/mvgal-sign-modules.sh`, which searches every location a module can land in, handles `.ko`, `.ko.xz` and `.ko.zst`, decompresses to sign and recompresses, and exits non-zero when a module could not be signed.
- **A scriptlet-ordering bug could leave every module unsigned.** `mvgal-dkms` did not depend on `mvgal`, so on a first install its `%post` could run before the main package's `%post` generated the signing key. It now requires `mvgal` at the same version.
- **Kernel updates re-signed themselves again.** DKMS rebuilds automatically on a new kernel, and that runs no RPM scriptlet, so the rebuilt modules returned with DKMS's key. `dkms.conf` now sets `POST_INSTALL` to re-run the signer, and the signer with no argument covers every installed kernel release rather than only the running one.
- **The Secure Boot check could pass while the key was unusable.** The daemon tested enrollment with `mokutil --list-enrolled | grep -qi MVGAL`, which matches on subject name. Every MVGAL keypair shares one subject, so after a key rotation the old certificate is still listed, the check passes, and the daemon stays silent while modules signed by the new key are rejected. It now uses `mokutil --test-key`.
- **`set-power-curve` accepted a GPU index it discarded.** The helper persists a single global `power.power_curve_profile`, so every index wrote the same key. Its documented example, `set-power-curve 0 gaming`, also failed, because `gaming` is not a valid profile. The argument is removed and the example corrected; the old two-argument form still works with a warning. The help now states that the profile is persisted but not yet consumed, because nothing reads the key.
- **Informational log output still reached stdout.** v0.7.21 redirected `get_default_output()`, but `log_internal()` has a separate fallback for when `mvgal_log_init()` was never called, and that fallback still sent INFO and above to stdout — which is exactly the path the affected tools take. Both paths now write to stderr.
- **`tool | head` killed the producer with SIGPIPE.** The CLI tools now ignore it, so a closed downstream pipe yields exit 0 instead of status 141.
- **"Vulkan registered: yes" implied aggregation was active.** The implicit interception layer ships globally and only intercepts calls; the aggregated ICD, which would expose an MVGAL `VkPhysicalDevice`, is a separate opt-in. `mvgal-info` and `mvgal-compat` now report the two separately and name the opt-in script.
- **`mvgal-compat` advised a command that cannot succeed.** `pkexec modprobe mvgal` fails on a Secure Boot machine whose key is not enrolled, and `mvgal.ko` depends on `mvgal_ntsync.ko`, so modprobe reports only the outermost failure. The hint now points at `mvgal-load`.
- **`mvgal-bench` presented host measurements as GPU figures.** Memory bandwidth is an `mmap`'d host RAM copy and compute is a single-threaded host CPU DAXPY; both were printed under headings that read as GPU performance. Every measurement is now labelled with its hardware path, the run header states when no GPU path is exercised, and `--metadata` gains `hardware_path`, `mvgal_device_present`, `measures_gpu` and `measurement_note`.

### Notes

- Re-signing a module that already carries a signature **appends** a second one rather than replacing it; the signer strips the existing signature first.
- A signed module ends with the DER blob, an 8-byte `struct module_signature`, a 4-byte big-endian DER length, and the marker `"~Module signature appended~\n"` — the terminator is a newline, not a NUL.
- The per-machine key is preserved across upgrades: `%post` regenerates it only when missing and no `%postun` removes it.
- Verified by extracting the built RPMs and executing the shipped binaries, not by reading the source. Upstream COPR build #11118333 is green on all 19 enabled chroots.

## [v0.7.21] - 2026-10-12

Correctness and packaging release driven by a black-box test report against
0.7.20 on a single-GPU Intel host. Most of the report concerned reporting and
packaging rather than device paths, but two findings were genuine defects and
two of the fixes below replaced a first attempt that would not have worked.

### Fixed

- **The daemon's IPC socket was created `root:root`, locking out every user in the `mvgal` group.** All CLI-to-daemon IPC failed: `mvgal show-stats` returned stub zeros, `mvgal status` could not read live state, and `nc -U /run/mvgal/mvgal.sock` returned `Permission denied`, even though the package adds the installing user to `mvgal` and the shipped unit comments say the socket must be `0660 root:mvgal`. The cause was **not** the `chown()` call itself. The unit's `CapabilityBoundingSet` listed `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO CAP_SYS_MODULE` and omitted `CAP_CHOWN`, and a bounding set caps the permitted set a uid-0 process can ever hold. `chown()` only avoids needing `CAP_CHOWN` when the target group is one the caller is already a member of, and root's supplementary groups do not include `mvgal` — so the call failed with `EPERM`, the return value was discarded, and the daemon reported a listener it had in fact left root-only. `CAP_CHOWN` is now in both `CapabilityBoundingSet` and `AmbientCapabilities`; it is needed exactly once, at startup. The unit's comment claiming the daemon "drops capabilities itself after init" was also false and has been corrected — there is no `prctl`/`capset`/`setuid` in `runtime/`. Both daemons now log the failure rather than swallowing it. See [[docs/TROUBLESHOOTING|Troubleshooting]] § Daemon socket permissions.
- **The OpenCL ICD advertised a version it did not implement.** `clGetPlatformInfo` reported `"OpenCL 1.2 MVGAL"` while the library exported only 2 of the 7 entry points that OpenCL 1.2 added to the core API. Because the library is registered as an ICD, ocl-icd and the CUDA loader `dlsym()` them from the shared object, so an application using any 1.2 feature received `NULL` and would fault rather than fail gracefully. Added `clCreateCommandQueueWithProperties`, `clCreateSubDevices`, `clCreateSamplerWithProperties`, `clSetUserEventStatus` and `clGetEventProfilingInfo` as pass-throughs, returning `CL_INVALID_OPERATION` where no vendor implements them — deliberately *not* falling back to the deprecated `clCreateCommandQueue`, which would silently drop queue properties that 1.2 requires to be honoured. The 1.2 ceiling itself is deliberate and is now documented in the source: the layer enumerates and delegates vendor devices rather than virtualising the device API, and 3.0's pipe/sparse/dma-buf behaviours are not emulated, so claiming 3.0 would overstate the aggregation path.
- **Configuration was silently reset on RPM upgrade.** `mvgal.conf` is `%config(noreplace)`, so an upgrade that changes the schema activates the new default file and leaves the user's edits in `.rpmsave` — the only record. A merge now runs in `%post` (`/usr/lib/mvgal/mvgal-merge-config.sh`), restoring the user's values per **section and key**, re-adding keys the new release dropped, and appending sections it dropped entirely. It also preserves the new release's default alongside as `mvgal.conf.mvgal-default`, so nothing is lost either way.
- **`mvgal load-module` hung indefinitely.** The CLI spawned the polkit helper through `system()` with no bound, so a cancelled or ignored authentication dialog left it waiting forever and the user never saw the result. It now runs under a 60-second timeout, distinguishes that case explicitly, and prints the Secure Boot remediation on failure.
- **Two fixes corrected first attempts that would not have worked.** The configuration merge originally keyed on bare key names; `priority` appears in both `[gpu_0]` and `[gpu_1]`, `enabled` in five sections, and `psu_capacity_watts` exists in the new file with a different value — so a user's `psu_capacity_watts = 750` would still have been dropped, which is the exact case reported. The shared-memory flag originally occupied a bit in the kernel-owned UAPI `flags` word; a kernel-set bit 31 would have mislabelled a real GPU's dedicated VRAM as shared system memory. Both were replaced with unambiguous mechanisms.
- **`mvgal-compat` advised adding the user to group 0.** When the socket was inaccessible it printed that `'id -nG'` must list the socket's gid, "gid 0 means the daemon did not chown its socket" — self-contradictory, and it framed a privilege escalation as a fix. It now distinguishes the two cases: gid 0 names the daemon-side chown bug, anything else points at group membership.
- **Exit codes disagreed about the same degraded state.** `mvgal status` exited 0 with the module unloaded while `mvgal-status --once` exited 1; `mvgal reload` printed "configuration not reloaded" and exited 0. Degraded/not-applied now returns non-zero consistently, and `mvgal reload` reports failure when there was no daemon to reload.
- **Informational log output polluted stdout.** `get_default_output()` returned `stdout` for INFO and above, so `Configuration system initialized` and friends interleaved into command output and would break a JSON consumer. All levels now go to stderr.
- **Placeholder values were presented as measurements.** `mvgal-info --json` emitted `"driver": ""`, `"class_code": "0x0000"`, `"pcie_link_gen": 0` and `vram_used_bytes: -1`. Unavailable values now emit `null`, and a new `vram_type` field distinguishes `dedicated`, `shared_system` and `unavailable`. Two sentinels had a genuine ambiguity: `utilization_pct` and `temperature_c` started at 0, so a real 0% busy was indistinguishable from "no such node"; these now use -1, and NUMA node uses `UINT32_MAX` because 0 is a real node.
- **Integrated GPUs reported system RAM as VRAM.** An Intel UHD 770 was shown as `VRAM: 7.43 GB` and `Aggregate VRAM: 7.43 GiB`, the latter being the headline figure of an aggregation layer. Shared memory is now labelled as such in both the per-GPU listing and the aggregate total.
- **Cross-tool disagreement about the same GPU.** `mvgal-info` reported an empty driver while `mvgal-enum` reported `i915`; `mvgal-enum`'s `timestamp_ns` field held epoch *seconds*. The driver is now resolved from the device's bound sysfs symlink, and the field is `timestamp_s`.
- **`-c/--config` accepted only `/etc/mvgal/*.conf`, undocumented.** The restriction exists because the privileged helper edits the path, so an unconstrained value would be a privilege-escalation primitive; it is now stated in the help text. The raw wait-status `256` that masked the real error is now decoded.
- **`--version` was missing on three shipped tools** and `mvgal-info` silently ignored unknown options while also ignoring `--version`. All shipped tools now answer `--version`, and `mvgal-info` rejects unknown arguments.
- **`mvgal-probe` rejected long options**, printing `invalid option -- '-'`. It accepts `--help`, `--rescan`, `--caps`, `--stats`, `--json` and others.
- **The AI scheduler logged a per-boot warning.** No model ships, so `AI scheduler: model ... not found` appeared at info level on every start. Demoted to debug.

### Packaging
- **COPR build #11110014** succeeded on all 19 enabled chroots (Fedora 43/44/45/ELN/Rawhide, RHEL 8/9/10 and +epel, AlmaLinux 9/10, AlmaLinux Kitten 10, AlmaLinux +epel, CentOS Stream 9/10 and +epel-next, Amazon Linux 2023, Mageia 9).
- The Secure Boot banner is now printed by the daemon at startup as well as by `%post`, so an unenrolled key is visible on first run rather than only at install.
- Verified by extracting the published `mvgal-0.7.21-1.fc44.x86_64.rpm` and checking the artefacts in place: the OpenCL shared object exports all seven 1.2 entry points, the configuration-merge script is installed mode 755, and the shipped unit carries `CAP_CHOWN`.

### Notes
- **L7 is not an MVGAL defect.** The report attributed a Vulkan loader warning about missing display entry points to the MVGAL ICD. Both `vkGetPhysicalDeviceDisplayPropertiesKHR` and `...PlanePropertiesKHR` are implemented and resolve through the shipped ICD's negotiated interface version 5, which is the path the loader uses; the library exports only the five spec-mandated `vk_icd*` symbols, as an ICD must. Since 0.7.14 no ICD manifest ships in `vulkan/icd.d` at all (the manifest is opt-in), so the loader cannot be loading MVGAL as an ICD unless a user explicitly opts in. The reporter also noted a second ICD warned in the same run.
- **L8 required no change.** Enumeration selects on PCI vendor ID and resolves the driver from the bound sysfs symlink, never on card index or driver name. Confirmed on a host exposing only `card1` with both `i915` and `xe` loaded.

## [v0.7.20] - 2026-10-10

Build system fix and version consistency across all components. The 0.7.19 release had a version drift: the Cargo workspace and several source headers still reported 0.7.19 while the CMake project and spec file reported 0.7.20. This release aligns every version source and fixes the daemon compilation.

### Fixed
- **Daemon compilation failed** with `testing/mvgal_mock_internal.h: No such file or directory`. The daemon's `gpu_manager.c` includes the mock header, but `src/userspace/CMakeLists.txt` did not expose the `testing/` directory to the daemon target. Added the include path.
- **`build.sh` manual compilation test used the wrong include path.** The test now uses `-Isrc/userspace` so it finds `testing/mvgal_mock_internal.h` through the daemon's include path.

### Changed
- **Version alignment across all sources**: `CMakeLists.txt`, `packaging/rpm/mvgal.spec`, `Cargo.toml` (workspace), `bindings/rust/Cargo.toml`, `Cargo.lock` (via `cargo update --workspace`), `include/mvgal/mvgal_version.h`, `kernel/mvgal_version.h`, `kernel/dkms/dkms.conf`, `tools/libmvgal/CMakeLists.txt` all report 0.7.20.

### Packaging
- **COPR build #11104568** succeeded on Fedora 43/44/45, Rawhide, ELN, RHEL 8/9/10, AlmaLinux 9/10, CentOS Stream 9/10, Amazon Linux 2023, Mageia 9.
- **Jenkins build #18** produced all 13 artifact formats: RPM (SRPM, binary, DKMS, metapackage), DEB (main, daemon, dev, dkms, vulkan), AppImage, tar.zst, Flatpak.
- All 28 unit tests pass (`ctest --output-on-failure`).

## [v0.7.19] - 2026-10-04

Makes a release reproducible from its commit: rebuilding the source tarball and the SRPM from the same tree now yields byte-identical files. Two independent causes had to be removed.

### Fixed
- **The source tarball embedded a second, complete copy of `vendor/`.** `scripts/mksrpm.sh` assumed `vendor/` was gitignored and therefore absent from `git archive`, then copied it in — but `vendor/` is **tracked** (`.gitignore` says so explicitly: the vendored crates have to travel with the source, because `.cargo/config.toml` replaces crates.io with them). `git archive` already emitted all 1109 `vendor/` paths, so the copy nested a duplicate at `vendor/vendor/` and restamped the parent's mtime with the wall clock. That single mtime was the only difference between two builds of an identical tree. The copy is gone; the script now *fails* if `vendor/` is absent from the archive rather than silently duplicating it. The tarball shrank from 11 MB to 8.3 MB and is now reproducible.
- **`BUILDTIME` was the wall clock.** rpm only rewrites `BUILDTIME` from `SOURCE_DATE_EPOCH` when the macro `use_source_date_epoch_as_buildtime` is defined, and it ships undefined on purpose — exporting `SOURCE_DATE_EPOCH` alone changes nothing, which is exactly what the first attempt at this fix demonstrated. Both `scripts/mksrpm.sh` and `packaging/jenkins/build_rpm.sh` now default `SOURCE_DATE_EPOCH` to the commit date (`git log -1 --format=%ct`) and pass the opt-in macro. Verified: two consecutive runs produce the same tarball digest, the same SRPM digest, and the same `BUILDTIME`, equal to the commit date. The Jenkins path was confirmed against a real build — its SRPM is byte-identical to the one `mksrpm.sh` produced locally from the same commit, so the two independent code paths agree.

### Notes
- **Binary RPMs are still not bit-reproducible, and this release does not claim they are.** Two axes remain. Fedora's toolchain links with a bare `--build-id`, so each ELF gets a random `NT_GNU_BUILD_ID` note; and the absolute build path is baked into `DW_AT_comp_dir`, `DW_AT_name` and the generated `mvgalConfig.cmake`, so two different build directories also diverge. Both are addressable — `-Wl,--build-id=sha1` with `-fdebug-prefix-map`/`-ffile-prefix-map` was verified to collapse two builds from different directories to a single digest, and unlike stripping the note it keeps the content-derived build-id that debuginfod depends on. It is not enabled because the spec's `%build` drives `cmake` through `cmake-rpm-macros`, whose `%cmake` macro has already overridden spec-level flag and cache workarounds in five earlier releases. This is recorded as open work in [[docs/STATUS|Project Status]] § Reproducibility limits rather than papered over.

## [v0.7.18] - 2026-10-04

Adds a synthetic GPU topology backend, so the heterogeneous code paths can be exercised and asserted on a single machine instead of only being reachable on a box that happens to have two vendors installed.

### Added
- **`mvgal_mock` — the 30th public header.** `include/mvgal/mvgal_mock.h` publishes a backend that advertises a configurable set of fake GPUs: vendor, VRAM size, PCIe generation and lane count, feature bits and driver identity. The GPU manager's rescan substitutes it for the hardware scan, so the scheduler, the memory manager and the P2P cost model all see synthetic devices **through the normal discovery path** rather than a parallel test-only one. With the backend inactive, `mvgal_mock_is_active()` returns false and discovery is untouched. See [[docs/API|API Reference]] § Synthetic Topology Backend.
- **Seven topology presets** — `NONE`, `SINGLE`, `HETERO_DUAL`, `HETERO_TRI`, `HETERO_QUAD`, `AMD_DUAL` and `INTEGRATED_ONLY` — covering the single-GPU optimisation case, dual-vendor P2P, multi-root-complex host staging, homogeneous AMD peer-to-peer and the integrated-only case with no VRAM. `append_to_hardware` adds synthetic devices alongside the real scan instead of replacing it; it is off by default so a test gets the same device population on any machine.
- **Modelled physics rather than canned values.** Temperature approaches an asymptote between a 35 C ambient and a TDP-scaled peak with a ~15 s time constant; throttling begins 5 C above TDP and is capped at a 60 % utilisation reduction; VRAM carries a 256 MiB baseline before any test allocation; and per-pair link bandwidth is derived from the pair's negotiated PCIe generation and lane count, so two Gen4 x16 peers model about 15.7 GB/s while a pair with no P2P path reports 0. `mvgal_mock_advance()` integrates elapsed time and then refreshes telemetry. Tests assert on *transitions* — a device heating into throttling and cooling back out — rather than on fixed numbers.
- **Per-device control from the test:** `set_load`, `allocate_vram` (0 releases), `kill_device` and `resurrect_device`, and `set_link_bandwidth`.

### Fixed
- **`mvgal_p2p_query_caps()` fabricated a 16 GB/s peer link.** Any pair on the same root complex reported `supported` with `max_bandwidth_mb_s` defaulting to 16000 — including synthetic devices whose peer path was disabled. The cost model reads that number, so it would select `REPLICATE` for a small buffer or `MIGRATE` for a large one between two devices that cannot transfer at all. Synthetic pairs now report the bandwidth the topology actually models, and `supported` requires a path to exist. `same_root_complex` remains pure topology. The real-hardware path is unchanged.
- **`mvgal_p2p_cross_vendor_supported()` ignored device health.** It checked only that both descriptors could be read, so a failed device still advertised itself as shareable and the scheduler would plan work onto it. Both descriptors must now also be `available`.
- **Host state leaked into the simulation.** `finalize_gpu_descriptor()` fills an integrated GPU's zero `vram_total` from `sysinfo()`, which meant a synthetic integrated device reported the *build host's* RAM — so the same topology produced different descriptors on different machines, quietly defeating the point of a deterministic fixture. Synthetic integrated devices now use the new public `MVGAL_MOCK_SYSTEM_RAM_BYTES` (32 GiB). The real-hardware behaviour is deliberately unchanged.
- **`mvgal_mock_init()` rejected its own documented preset.** `MVGAL_MOCK_TOPOLOGY_NONE` — "no synthetic devices, hardware discovery behaves unchanged" — was refused with `MVGAL_ERROR_INVALID_ARGUMENT` by a `preset <= NONE` bounds check, while the header promised `MVGAL_ERROR_NO_GPUS` for an empty preset. The check now rejects only out-of-range values, and `NONE` falls through to the documented result.

### Tests
- `test_mock_gpu` — 193 assertions across the presets, device selection, failure isolation and resurrection, memory pressure, thermal throttling and cooling, configurable health thresholds, transfer-bottleneck topology, cross-vendor sharing, and determinism (two passes over the same topology must agree). Determinism is asserted by reading descriptors back through the public `mvgal_gpu_get_descriptor()` rather than through mock-internal accessors, so the assertion covers the discovery path the rest of the project uses.

## [v0.7.17] - 2026-10-04

Repairs the Rust quality gate. The crates had never been linted at all.

### Fixed
- **The crates were never linted.** `clippy.toml` carried three keys that modern clippy rejects: `panic-in-upgrade`, which is not a clippy configuration field; `large-digit-grouping`, a rust-analyzer setting rather than a clippy one; and `cyclomatic-complexity-threshold`, a deprecated alias that now collides with `cognitive-complexity-threshold`. Clippy aborts on an unreadable configuration file *before* it lints anything, so every one of these turned the entire gate off rather than producing a warning.
- **`disallowed-macros` listed two methods.** `unwrap` and `expect` are methods, not macros, so clippy reported them as unreachable macros on every invocation and `-D warnings` promoted that reporting quirk to a hard failure. The thresholds that are still meaningful are kept.
- **`CrossDeviceFence` could never cross a thread boundary.** It held its signal timestamp in a `Cell` and its external handle in a raw pointer, so `Arc<CrossDeviceFence>` was neither `Send` nor `Sync` — meaning any attempt to share a fence across threads did not compile. The timestamp moved behind a mutex and the handle is now documented as synchronised by the caller.
- **`create_fence()` returned a fence that was not the fence being tracked.** `GpuTimeline::create_fence()` and `FenceManager::create_fence()` each stored a clone in their map and returned a *second*, independent `Arc`, so signalling the returned handle had no effect on the fence the manager held. Both now hand out the same `Arc` they retain.
- **`MvgalError` could not represent its own error.** It relied on the implicit C-like enum representation, which cannot hold `Unknown = 0xFFFFFFFF`. It is now explicitly `#[repr(u32)]`; the `i32` conversion used across the FFI boundary still yields `-1` for `Unknown`.
- **`align_up()` hand-rolled `div_ceil()`.** The ceiling division is now the standard library's.

## [v0.7.16] - 2026-09-30

This release completes the custom splitter API and makes the command DAG translation and emission paths real instead of returning their arguments unchanged. Every item below was found by reading the source rather than from a field report, and each was reproduced before it was changed.

### Fixed
- **`mvgal_unregister_custom_splitter()` could never succeed.** Splitters were stored **by value** on registration but the removal loop compared the caller's pointer against the address of the internal slot, `&splitters[i]`, which is never exposed to any caller. Because the register path had already copied the struct, no caller could ever supply a pointer that matched, so the function reported the splitter as absent on every call. Removal now matches by value across `analyze`, `split`, `merge` and `user_data` together, which is what distinguishes two registrations that share callbacks but differ in their private state.
- **`mvgal_unregister_custom_splitter()` was not declared in any public header.** The definition was reachable inside the library but not from outside it, so a program could register a splitter and had no way to release it. The declaration is now in `include/mvgal/mvgal.h` beside its counterpart.
- **Both custom-splitter entry points discarded their arguments.** `mvgal_register_custom_splitter()` and `mvgal_unregister_custom_splitter()` in `src/userspace/api/mvgal_api.c` cast their context and splitter to `void`, logged that the feature was not yet implemented, and returned `MVGAL_ERROR_NOT_SUPPORTED`. They now validate the context is initialised and the descriptor is non-`NULL`, then forward to the scheduler.
- **`mvgal_translate_dag()` returned its argument unchanged.** The header promised a translated copy, so callers had every reason to mutate the result; instead they were handed a pointer aliasing the original, and any edit silently corrupted the source DAG. It now deep copies, carrying the queue family, command buffer index and primary flag, and rewires every `deps[]` edge onto the copies through an old-to-new pointer map. An edge whose target is not in the map fails the whole translation rather than dropping a synchronization edge. `vendor_data[]` is reset to `NULL` on the copy, because that array is owned per-vendor data whose lifetime the copy does not share; the recorded `args.barrier.info` stays a borrowed pointer and the caller must keep it alive.
- **`mvgal_emit_dag()` always failed.** It returned `VK_ERROR_LAYER_NOT_PRESENT` unconditionally, so a translated DAG could never be replayed. It now resolves `vkCmdDraw`, `vkCmdDrawIndirect`, `vkCmdDispatch`, `vkCmdPipelineBarrier2`, `vkCmdPipelineBarrier`, `vkCmdBlitImage`, `vkCmdClearAttachments` and `vkCmdBindPipeline` through the device dispatch table and replays the nodes in recording order. Node types with no captured arguments return a specific error instead of being skipped, because a silent skip renders the wrong frame. A new `mvgal_cmd_dag_begin_for_device()` records which device a command buffer belongs to; the existing `mvgal_cmd_dag_begin()` still works, and emission on a buffer with no known device reports that rather than pretending to succeed.
- **The command buffer to DAG map leaked on collision.** It was an open-addressed table with no collision handling, so `mvgal_cmd_dag_begin()` overwrote whatever DAG occupied the slot whenever two command buffers hashed alike — losing the live DAG and leaking it. Lookups now probe linearly, `mvgal_cmd_dag_end()` probes instead of hashing once, and beginning a recording for a buffer that already has one destroys the old DAG rather than dropping it.

### Notes
- **Barrier lowering refuses rather than approximates.** A sync2 dependency carrying a queue family transfer or an image layout transition is rejected with `VK_ERROR_FEATURE_NOT_PRESENT` and an explanation, instead of being flattened into a plain memory barrier. `mvgal_cmd_node_t` records no fields for either, so emitting them would silently under-synchronize. The same applies to mask widening: 64-bit sync2 stage and access masks are widened to their 32-bit equivalents, and any bit above 31 becomes `VK_PIPELINE_STAGE_ALL_COMMANDS` or a read-and-write access mask rather than being truncated away.
- **`MVGAL_STRATEGY_CUSTOM` still returns `MVGAL_ERROR_NOT_SUPPORTED`.** Registering a splitter works and the descriptor is validated, but applying one to a dequeued workload needs a task tree contract that is not yet defined: how a splitter's `split()` callback obtains sub-workload handles, who owns them, when `merge()` fires, and how a failed child is reported to the parent. That contract is a design decision, not a defect, so no speculative behaviour was added.

### Tests
- `test_custom_splitter_registration()` registers two splitters whose three callbacks are identical and which differ only in `user_data`, then unregisters them in the order that exposes a matcher ignoring that field: a matcher that compared only the callbacks would release `A` when asked for `B`, and the following release of `A` would then wrongly fail. It also checks that a third release reports `MVGAL_ERROR_NOT_FOUND` rather than success, that a `NULL` argument is rejected by both entry points, that a descriptor missing one callback is rejected outright, and that rejecting it left no stale entry behind — otherwise a stored descriptor with a `NULL` merge pointer would later be dispatched through it. Finally it asserts the three callbacks were never invoked, since no workload has been submitted.
- `test_translate_deep_copy()` asserts the translated DAG is a distinct object, that dependency edges point at the copies rather than the source nodes, and that mutating the copy leaves the original untouched.

## [v0.7.15] - 2026-09-30

A memory-corruption fix in the buffer copy path, found by reading the code rather than from a field report. Every case below was reproduced before it was changed.

### Fixed
- **`mvgal_memory_copy()` applied the region offsets twice.** It passed `region->src_offset` and `region->dst_offset` to `mvgal_memory_map()`, whose documented contract is that the returned pointer already points at the requested offset, and then added the same offsets again at the `memcpy`. A copy from source offset 1024 to destination offset 2048 therefore read and wrote at `base + 2 * 2048`, running past the end of the mapping and corrupting whatever followed it in the allocator. `mvgal_memory_copy_gpu()` builds a single region and delegates, so it inherited the fix. The pre-existing copies all used offset 0, which is exactly the case where a double-applied offset is a no-op, so the suite passed while the path was broken.
- **`mvgal_memory_copy()` unmapped buffers it did not own.** The cleanup was guarded by a test for the `MAPPED` state bit that `mvgal_memory_map()` had already set one line earlier, making it unreachable dead code, and the destination-map failure path tore down a source mapping it had never created. Host-valid buffers carry a `host_ptr` owned by the allocator, so unmapping would have freed memory the buffer still points at.

### Tests
- `test_memory` gained a case that copies 256 bytes from source offset 1024 to destination offset 2048, then checks both that the payload lands at the destination offset and that exactly 256 bytes anywhere in the destination buffer are non-zero, which is what proves nothing outside the destination window was written. It fails against the previous `mvgal_memory_copy()`.

## [v0.7.14] - 2026-09-28

This release is the response to a field report from a Fedora 44 machine with a single Intel UHD 770 and Secure Boot enabled. Every item below was reproduced before it was changed.

### Fixed
- **The MOK enrolment never completed.** `mokutil --import` prompts for the one-time password *twice*, but `mvgal-enroll-mok` fed it one line, so every enrolment ended in `could not read confirmation password`. It now writes the password twice. The script then verified success with `mokutil --list-new | grep -qi "mvgal-signing"`, a string mokutil never emits — it prints `Issuer/Subject: CN=MVGAL Kernel Module Signing Key, O=MVGAL` — so even a successful import was reported as failed. The check now matches the certificate's actual common name. Because the check could never pass, Secure Boot machines were told to reboot and still had no trusted key.
- **`mvgal-enroll-mok -p <password>` silently dropped the password.** The script parsed its options and only *then* re-executed itself through `pkexec` with `"$@"` — which the parse loop had already emptied. The password reached the elevated process as nothing. The script now elevates before parsing, with a non-consuming pre-scan that keeps `--help` working unprivileged, and hands `pkexec` a pristine argument vector (a password containing a space survives).
- **Secure Boot detection could not say "off".** The state was matched with two nested `case` globs that only tested for substrings, so `disabled` and `not enabled` were not both recognised. The state is now lower-cased once and matched against explicit patterns; an unreadable or empty state warns instead of silently proceeding.
- **`mvgald`'s `ExecStartPre` could never load a module.** The unit's `CapabilityBoundingSet` and `AmbientCapabilities` omitted `CAP_SYS_MODULE`, so both `modprobe` lines were guaranteed `EPERM`. The `-` prefix in front of each command discarded the exit status *and* the message, so the unit reported `active (running)` with no kernel module. `CAP_SYS_MODULE` is now granted, the failing status is no longer discarded, and the message names the real fix (`pkexec mvgal-enroll-mok`).
- **`/run/mvgal` did not survive a reboot.** No unit declared `RuntimeDirectory=`, and `/run` is tmpfs, so the daemon's own directory creation was the only thing keeping the socket's parent alive. The unit now declares `RuntimeDirectory=mvgal` with `RuntimeDirectoryPreserve=yes`.
- **The daemon IPC socket was unreachable by ordinary users.** The legacy C daemon created it `root:root` mode `0660` and never changed the group, so no unprivileged process could connect, while the error message (`tools/mvgal-compat.c`) told users to join the `mvgal` group they were already in. Both the legacy C daemon and the C++ runtime daemon now resolve the group (`mvgal`, falling back to `video`) and `chown` the socket before `chmod`. `mvgal-compat` now reports the socket's *actual* owner, mode and the caller's uid, and distinguishes "your supplementary groups have not picked up" from "the daemon did not chown".
- **The pkexec helper's `--config` accepted any path on the filesystem.** It filtered metacharacters but never constrained the target, so any user authorised for the helper could have root `sed`-edit arbitrary files such as `/etc/sudoers.d/x`. It now requires the path to resolve (symlinks followed) to a regular file inside `/etc/mvgal`.
- **GPU indices were interpolated into `sed` addresses unvalidated.** `enable_gpu`, `disable_gpu` and `set_power_state` built an address range from user input, so a crafted index could rewrite lines outside the intended section. A dedicated validator rejects non-digits, over-long input, non-canonical leading zeros and out-of-range values (bounded against the GPUs actually present under sysfs when the module is loaded).
- **GPUs were listed as `Intel GPU 4680`.** `4680` is a device id, not a model, and both GPU managers synthesised that name when no label was read. Both now read the DRM `label` attribute — the pattern the CLI tools already used — and fall back to `Intel [8086:4680]`, which cannot be misread as a model.
- **`mvgal-hw-validate` labelled the first GPU `GPU[1]`** and read a `device_name` attribute that does not exist, so its `Name:` line never printed. The counter is now zero-based and reset per run, the `readdir` loop respects the `MAX_GPUS` bound it declared but never used, and the name comes from `device/label`. Skipped virtual devices are labelled rather than numbered.
- **The four `mvgal benchmark` subcommands exited 1 with no data.** The counters are per-process and only move when a workload runs inside that same invocation, so a plain `mvgal benchmark` always found zero and always reported failure. It now says so plainly and exits 0, matching the documented contract in `mvgal(1)`; a genuine failure to *read* statistics still exits 1. Each branch had also left its `mvgal_stats_t` uninitialised and discarded `mvgal_get_stats()`'s return value, so a read failure produced an indeterminate stack read.
- **The polkit policy was invalid and authorised nothing.** `data/com.mvgal.policy` used `<_description>`/`<_message>` instead of `<description>`/`<message>`, so it failed DTD validation and no description ever rendered. It also declared ten action ids that no executable is annotated with, two of which (`com.mvgal.config.user`, `com.mvgal.monitor`) granted `allow_any=yes` — no authentication at all. It now declares exactly the two actions that exist and are annotated (`com.mvgal.privileged.helper` for the helper, `com.mvgal.daemon.start` for `/usr/sbin/mvgald`), both requiring `auth_admin`. The eight orphans are gone.

### Added
- **One module inventory, shared by all three loaders.** `config/mvgal-modules.sh` (`/usr/lib/mvgal/modules.sh`) is now the single source of truth for load order, and `mvgal-load`, `mvgal-unload` and the pkexec helper all source it; the helper derives its unload order by reversing it. The three had drifted: the helper loaded `mvgal` *before* its own dependency `mvgal_ntsync`, and the unload paths were missing `mvgal_mtt` and `mvgal_adreno` entirely, so a module could never be unloaded once loaded. Overridable with `$MVGAL_MODULE_LIST`; a missing file warns rather than falling back silently.
- **An honest diagnostic for the AI scheduler.** The daemon loaded its model from a hardcoded path that no package ever creates, and `mvgal_ai_model_load()` returned a valid handle for *any* non-empty string without touching the filesystem, so the daemon believed it had an AI model for its entire life and never said otherwise. The loader now validates the path and reports what it found; the daemon reads the configured path (or `$MVGAL_AI_MODEL`) once at startup and logs plainly that inference is a built-in heuristic, not ONNX Runtime.

### Changed
- **Every version surface now reads one place.** Six files carried the version as a literal of their own and every one of them had drifted: `mvgald --version`, the `modinfo` version of `mvgal.ko`, `mvgal-gui --version`, the `version` field of `mvgal-bench --json`, the DKMS registration version, and `Cargo.lock` (still two releases back). They now read `include/mvgal/mvgal_version.h`, so the daemon, the CLI, the module and the package cannot disagree. The generated `mvgal_version.h` also now includes `<stdint.h>` and `<stdbool.h>`, which it uses and never included — it only ever compiled when something else had included them first, so it could not be included early.
- **The generated version header is now safe for the kernel to include.** The kernel build reaches the same header path (`Kbuild` passes `-I$(src)/../include`, and `kernel/mvgal_core.c` includes `<mvgal/mvgal_version.h>` for the three numbers), and that header is macro-only in the source tree on purpose. It stayed macro-only only by accident of *out-of-source* builds: on RHEL 8 `cmake-rpm-macros`' `%cmake` is broken, so the spec invokes `cmake` with no `-B` and the build is in-source, where `configure_file` writes the generated copy straight over the source tree's. There the kernel compiled the user-space half, `<stdint.h>` resolved to GCC's, whose `#include_next` has no libc headers to find — and the resulting error cascade also broke `module_param()` for an unrelated module parameter. Only RHEL 8 was ever affected, which is exactly why a latent header-layout dependency survived every other distro. The user-space half is now fenced with `__KERNEL__`, which kbuild always defines and no user-space build does, so which copy of the header wins no longer decides whether the kernel compiles.
- **`scripts/mksrpm.sh` now checks every one of those.** It verified the six files that *derive* the version and ignored the ones that *copied* it, which is why the copy drifted while the check kept passing. It now also verifies `tools/libmvgal/CMakeLists.txt` and `kernel/dkms/dkms.conf`, checks that `Cargo.lock`'s workspace members are on the built version, and rejects any `MAJOR.MINOR.PATCH` literal appearing in the six source files that report a version — with C comments stripped first, so a version quoted in a comment explaining the check is not itself flagged.
- **The Vulkan ICD is no longer registered globally.** `mvgal_icd.json` was installed into `share/vulkan/icd.d`, so every Vulkan application on the system loaded it — and since v0.7.12 it reports *zero* physical devices by design. With no device handle the loader cannot build a per-device dispatch table, so it printed `Cannot query ICD interface function vkGetPhysicalDeviceDisplayPropertiesKHR, vkGetPhysicalDeviceDisplayPlanePropertiesKHR in ICD N. The ICD is not conformant.` on every startup. The manifest now lives in `share/vulkan/mvgal/` and is applied only on request, via `mvgal-vulkan-env.sh` (which is now installed, unlike before) or `MVGAL_ICD_JSON`. Its `library_path` is absolute rather than relying on the loader's `dlopen` search order. The implicit interception layer stays registered globally, because that is the layer that does the work. Upgrades remove a stale manifest from `icd.d` only when it is recognisably ours.
- **The OpenCL ICD is parked when it has nothing to aggregate.** `libmvgal_opencl.so` is a real aggregating ICD — it scans `/etc/OpenCL/vendors/`, skips itself and delegates to every peer — but with no vendor OpenCL runtime installed it produced zero platforms and no explanation. On first install with no peers present, the manifest is moved aside as `mvgal.icd.disabled` with a message naming the package that provides a peer and the exact command to re-enable it. Erasing the package re-enables it if a peer has since appeared.
- **`packaging/rpm/mvgal.conf` removed.** It was a dead duplicate of `config/mvgal.conf` with a completely different section layout, and the pkexec helper's `sed` edits only ever matched the latter. Leaving two files named `mvgal.conf` with different schemas is a trap; the installed file is now the only one.
- **`scripts/mksrpm.sh` refuses to build from a dirty tree.** It builds the source tarball with `git archive HEAD`, so the SRPM describes `HEAD` and nothing else — an uncommitted change, and in particular an untracked new file, is simply absent from the package. That is not hypothetical: the first 0.7.14 SRPM shipped the pre-fix source tree, because `config/mvgal-modules.sh` had not been added yet, and failed at the far end on four missing files in `%files`. The script now stops with the offending paths listed.
- **Documentation corrected** where it described the socket as `root:root`-only and the helper as living in `/usr/bin`.
- Version bumped 0.7.13 to 0.7.14.


## [v0.7.12] - 2026-09-27

This release removes the fabricated-success paths found by a full audit of the kernel and Vulkan subsystems. MVGAL reported hardware capabilities it could not deliver; where a capability is not obtainable on Linux, it now says so and the caller falls back.

### Removed
- **GPU PCI binding.** `mvgal_pci_driver` and its `MODULE_DEVICE_TABLE` alias table are gone. Registering a PCI driver whose probe calls `pci_enable_device()` and `pci_set_master()` competes with amdgpu, nvidia, i915/xe and mtgpu for a device MVGAL cannot drive. GPUs are still discovered read-only through `pci_get_device()` and the PCI bus notifier, and `mvgal.ko` now publishes no `alias:` at all, so udev cannot autoload it onto a GPU. This also removed a double registration: `mvgal_enumerate_gpus()` added every GPU, then `pci_register_driver()` re-probed the same devices and added them again.
- **Fabricated VRAM allocation, all four vendors.** `alloc_vram` was a bump allocator returning addresses with no backing buffer object: amd seeded `0x100000000`, mtt `0x40000000`, nvidia `0x10000000`, and intel returned the allocation's sequential id as the address, so the first allocation yielded address 0. All now return `-EOPNOTSUPP` and write `*gpu_addr = 0` so no stale address escapes.
- **`submit_cs` that dispatched nothing, all four vendors.** Each validated arguments, logged a debug line and returned 0. Two dispatcher branches in `mvgal_scheduler.c` went further and marked the workload COMPLETE with the comment "No vendor ops - mark complete immediately for testing". All now return `-EOPNOTSUPP`, and the scheduler restores the workload to PENDING instead of stranding it at RUNNING.
- **A synthetic Vulkan physical device.** The ICD reported one device whenever a GPU was present, carrying GPU 0's real `vendorID`/`deviceID`/`deviceType` and the name `"MVGAL Aggregated (<gpu0> + N more)"`. It now reports zero devices. The interception layer already enumerated the real devices truthfully; that is the honest multi-GPU surface.
- **Dead fabrication helpers in `physical_device.c`.** `mvgal_physical_device_create`, `mvgal_physical_device_destroy`, `mvgal_get_physical_device_group_properties` and `mvgal_get_real_gpu_count` had zero callers. The two live functions remain.

### Fixed
- **`pci_dev` reference leak.** Every enumerated GPU held a reference that was never released. `mvgal_gpu_free()` now releases it, and deliberately does not call `pci_disable_device()` or `pci_set_master()`, which belong to the native driver.
- **Double `pci_dev_put()`.** Both error paths of `mvgal_enumerate_gpus()` released a reference that the shared exit path released again.
- **Two crossed power-state enums.** `mvgal_set_power_state()` took `enum mvgal_power_state` (`OFF=0, SUSPEND=1, IDLE=2, ON=3, PERFORMANCE=4`) while every vendor op and the ops-table member take `enum mvgal_device_power_state` (`ACTIVE=0, SUSTAINED=1, IDLE=2, PARK=3, OFF=4`). Values were silently reinterpreted: requesting `ON` reached the driver as `PARK`, `PERFORMANCE` as `OFF`. The redundant enum is deleted and the power manager now speaks the vendor-op vocabulary.
- **`mvgal_set_power_state()` never updated the tracked state.** When a vendor op existed it returned immediately, so `gpu->power_state` diverged from what the driver was doing. With no vendor op it recorded the request and returned success; it now reports that the state was recorded but not applied.
- **`wait_idle` returned success without waiting**, in all four vendors, with no exported idle-wait entry point on any of them. Now `-EOPNOTSUPP`.
- **Unverified capability flags.** `can_export_dmabuf`, `can_import_dmabuf`, `ttm_available` and `dpm_supported` were set to `true` from the vendor family with no test. `dpm_supported` now requires the sysfs node to exist.
- **The memory KUnit suite asserted nothing.** `test_memory_alloc()` returned NULL because no fixture had called `test_memory_manager_init()`, so every `KUNIT_EXPECT_NOT_ERR_OR_NULL` was exercising the NULL path rather than the real one. The suite now registers proper init and exit fixtures.
- **Duplicate module detection in the NVIDIA driver.** `mvgal_nvidia_init` inlined the same `/sys/module` lookup twice; a single `mvgal_nvidia_module_present()` helper now serves both call sites.
- **A dead shader route call.** `vk_layer.c` ran a full SPIR-V optimise and decompile on every `vkCreateShaderModule`, against a hardcoded AMD vendor regardless of the actual GPU, then discarded the result.

### Added
- **Runtime capability probing.** Each GPU carries an `MVGAL_CAP_*` mask built by an actual test: opening the sysfs node, or checking which driver owns the PCI function. Nothing is inferred from the vendor family. `probe_capabilities` is a new vendor op, and a capability that cannot be verified is simply absent. `kernel-submit`, `kernel-vram`, `dmabuf-export` and `wait-idle` are deliberately never set for any vendor, for reasons recorded per vendor. `dma-buf-import` and `bo-query` are set where a driver owns the function, because those paths are real.
- **Callers consult capabilities, not ops pointers.** The scheduler, power manager and memory manager previously tested `ops->foo != NULL`, which an op that logs and returns 0 satisfies just as well as a working one. They now test the probed bit.
- **Per-GPU sysfs attributes** `capabilities` and `native_driver`, both printing `none` when there is nothing to report, so an unprobed device cannot be mistaken for a capable one.
- **Idle gating**, which requires a measurable busy signal and therefore `MVGAL_CAP_BUSY_PERCENT`. A device without one reports idle-gating as unavailable and refuses to arm rather than gating on a guess. Enabling it on such a device returns `-EOPNOTSUPP` to the writer. Exposed as `idle_gate`, `idle_gate_status` and `idle_gate_timeout`.
- **Corrected documentation.** `docs/SPEC_COMPLIANCE.md` findings 1, 2 and 3 are marked resolved with the evidence, and a new section records the probing contract. The README status table no longer claims the PCI binding and fake vendor operations are still present.

### Changed
- Version bumped 0.7.11 to 0.7.12.


## [v0.7.11] — 2026-09-26

### Fixed
- CRITICAL-1: The Vulkan shader compiler no longer overflows the heap when `ftell()` fails. `compile_nvidia_ptx()` and `compile_intel_igc()` (`src/userspace/intercept/vulkan/mvgal_shader_compiler.c`) sized their output buffer from `ftell()` and then read into it without validating the result. On failure the length is `-1`, so the allocation is `malloc(0)` — which glibc satisfies with a *non-NULL unique pointer*, meaning the existing `if (!*out_source)` guard did not catch it, and the following `fread(*out_source, 1, (size_t)-1, f)` then requested `SIZE_MAX` bytes into a zero-byte block. The trailing `(*out_source)[-1] = '\0'` was an out-of-bounds write in the same way. Both functions now reject a non-positive length and verify the short-read case, mirroring the checks the sibling `compile_amd_llc()` already had.
- HIGH-1: The daemon no longer writes out of bounds when the config file length cannot be determined. The `GET_CONFIG` handler (`runtime/daemon/ipc_server.cpp`) sized its response vector from `ftell()` and then wrote the terminator at that offset, but `ftell()` returns `-1` on failure — on the resulting zero-length vector, `configData[fsize]` is `configData[-1]`, a heap write one byte *before* the allocation, reachable by any client that can open the IPC socket. The `fread()` result was also unchecked. Both `fseek()` calls and the `fread()` are now verified, a negative length is rejected with `IpcErrorCode::GNU_ERROR`, and the payload length reported to the client is the number of bytes actually read — which additionally stops a stray NUL terminator from being shipped as payload.
- LOW-1: The discovery message header now documents that `DiscoveryMessageHeader::tcpPort` is a 32-bit wire slot carrying a 16-bit port, and the `htons()`/`ntohs()` call sites narrow explicitly. The field width is deliberately unchanged, so the on-wire layout of the packed struct is byte-for-byte identical; the previous implicit `uint32_t`→`uint16_t` narrowing was self-consistent only because the upper 16 bits happened to stay zero.
- MED-1: The version can no longer drift between the number and the string in `include/mvgal/mvgal_version.h`. The header carried `MVGAL_VERSION_MAJOR`/`_MINOR`/`_PATCH` and a hand-written `MVGAL_VERSION_STRING` independently, and the string is now built from the three numbers by a stringify macro, so a bump that edits only the numbers cannot leave the string behind. The previous in-tree copy had already drifted: `MVGAL_VERSION_STRING` read `0.7.10` while `MVGAL_VERSION_PATCH` read `10` after a bump that only touched the dotted form, and because `mvgal_get_version_numbers()` (`src/userspace/api/mvgal_api.c`) reports the numbers rather than the string, `mvgal --version` printed a patch number one release behind what `mvgald --version` and the generated header reported. Commit `95d0974` had generated an authoritative header from `project()` to prevent the two forms drifting apart, but that generated copy only shadows the in-tree one for some targets, so the in-tree copy remained live for the CLI.

### Added
- `scripts/mksrpm.sh` now verifies that the spec, `CMakeLists.txt`, both `Cargo.toml` manifests and both in-tree version headers agree on one version before it cuts the tarball, and reports every mismatch at once. Nothing previously forced those copies to agree, so a bump that missed one shipped a package whose daemon, CLI and library each reported a different version. This is the check that would have caught MED-1.

### Changed
- Version bumped 0.7.10 → 0.7.11 (bugfix release)

## [v0.7.10] — 2026-09-26

### Fixed
- HIGH-1: The daemon no longer invents a GPU that does not exist. `rescan_gpus_locked()` (`src/userspace/daemon/gpu_manager.c`) called `add_placeholder_gpu_locked()` whenever the DRM and NVIDIA scans both came back empty, registering a synthetic descriptor: `MVGAL_VENDOR_UNKNOWN`, `MVGAL_GPU_TYPE_VIRTUAL`, 4 GiB of VRAM, named "MVGAL Placeholder GPU", with `available = false`. Every consumer of the descriptor list then operated on that fiction — the scheduler would place work on it, VRAM accounting would report 4 GiB that is not there, and `mvgal list-gpus` would show a device no driver backs. On a host with no supported GPU, or with the `mvgal` kernel module not loaded, the daemon now logs the warning and reports zero GPUs.
- HIGH-2: The Vulkan ICD no longer advertises a fictitious physical device. `mvgal_vkEnumeratePhysicalDevices()` (`src/userspace/vulkan_icd/icd_entry.c`) returned a count of 1 and a `g_virtual_physical_device` handle named "MVGAL Virtual GPU (no physical GPUs detected)" whenever `g_daemon_gpu_count == 0`, and `mvgal_vkCreateInstance()` populated the properties struct to match. The loader would then select a device that has no backing, and the failure surfaced much later inside the application's own initialisation, far from the real cause. The ICD now reports 0 devices and leaves `*pPhysicalDeviceCount` at 0 — the contract the loader expects, which lets it fall through to the next real ICD on the system instead of dying here.

### Changed
- Version bumped 0.7.9 → 0.7.10 (bugfix release)
- `sudo` → `pkexec` across all shipped user-facing text (spec `%post` hints, `config/` scripts, docs, wiki, packaging helpers) to match the documented polkit-based privilege model.

## [v0.7.9] — 2026-09-26

### Fixed
- HIGH-1: Stale kernel header cache no longer breaks the build — `kernel/CMakeLists.txt` uses `find_path(KERNEL_HEADERS include/generated/utsrelease.h)`, and CMake never re-validates a cached `find_path` hit. A build directory reused across a kernel upgrade kept pointing at the removed header tree, so the `mvgal-kernel` target failed with `No such file or directory` even though the tree was present for the running kernel. The cache entry is now dropped when the generated headers are missing, so the build self-heals on any future kernel upgrade. This was the only failing target in a full build.
- HIGH-2: `libmvgal_cuda.so` could never be built — `src/userspace/CMakeLists.txt` gated the CUDA wrapper on `WITH_CUDA`, a variable that was never declared via `option()` or `set()` anywhere in the project. Undefined CMake variables are falsy, so the target was unreachable. Now built whenever `MVGAL_BUILD_API=ON`.
- HIGH-3: `libmvgal_cuda.so` is now packaged, and packaging no longer depends on the build host having a CUDA toolkit — `cuda_wrapper.c` is a pure `dlopen`/`dlsym` interposition shim: it includes no CUDA headers and links no CUDA libraries, resolving `libcuda` at load time. Gating the target on `CUDAToolkit_FOUND` therefore only served to make the library unbuildable, and so unshippable, in any environment without `nvcc`. The gate and the dead `${CUDAToolkit_INCLUDE_DIRS}` / `${CUDAToolkit_LIBRARIES}` are gone, and `%files` lists the library, fixing `Installed (but unpackaged) file(s) found: /usr/lib64/libmvgal_cuda.so` in every toolkit-less build root.
- MED-1: `memory.c` no longer fails a strict-warning build — `mvgal_migration_scheduler_dispatch()` declared a `struct timespec ts;` that was never used, left over from an untimed-wait rewrite of the migration condition variable. Removed.
- MED-2: `ai_data_collector.c` no longer fails a strict-warning build — the file used the POSIX timer API (`timer_create`, `struct sigevent`, `SIGEV_THREAD`, `union sigval`) without including `<signal.h>`, producing six cascading `-Werror` diagnostics. The sibling `ai_predictor.c` already included it.
- LOW-1: `cuda_wrapper.c` is clean under `-Wall -Wextra -Werror` — the two cross-GPU copy stubs left their `CUdeviceptr` parameters unused. Annotated with `(void)` casts; no behaviour change.

### Changed
- Version bumped 0.7.8 → 0.7.9 (bugfix release)
- `src/tests/tests/test_all.sh` rewritten against the real tree layout. It referenced roughly nineteen paths that do not exist (`dist/mvgal-0.2.2.tar.gz` from the 0.2.x era, `pkg/debian/`, `pkg/rpm/`, `pkg/arch/`, `pkg/flatpak/`, `pkg/snap/`, and three phantom `benchmarks/{synthetic,real_world,stress}/` binaries) and used `set -e` without `pipefail`. Now 10 sections and 72 checks, all resolving to real files.
- `src/tests/tests/test_cuda_wrapper.sh` rewritten. It was fully broken: a hardcoded stale absolute path (`/home/axogm/Documents/Driver/mvgal`) instead of deriving `BASE_DIR` from `$0`, two tests that printed a verdict without touching the exit status (so a real regression was invisible to CI), and an `nm -D` grep for `cuda_wrapper_init`, which is `static` and could never match. Now 7 real assertions including a `dlopen` harness and the eight interposed CUDA symbols, with real pass/fail counters and a real exit code.
- `test_all.sh`, `test_compile_all.sh` and `test_cuda_wrapper.sh` are clean under `shellcheck --severity=warning`.

## [v0.7.8] — 2026-09-22

### Fixed
- HIGH-1: `mvgal-enroll-mok` no longer reports false success — `mokutil --import` is now fed the password via stdin (the `-p` flag is rejected by mokutil 0.7.2) and the pending MOK list is verified with `mokutil --list-new` before claiming enrollment.
- HIGH-2: Daemon drops capabilities after init — `mvgald` now clears effective/permitted/inheritable sets and prunes the bounding set to `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO`; the systemd unit adds `CapabilityBoundingSet`/`AmbientCapabilities`/`NoNewPrivileges`.
- HIGH-3: `mvgal-status` reports degraded mode — when the `mvgal` kernel module is not loaded it prints `Kernel Module: NOT LOADED (degraded userspace-only mode)` with a MOK enrollment hint, and the hard-coded `Load Balance: 100.00%` is replaced by a real estimate (or `N/A` when fewer than 2 enabled GPUs / no workload data).
- HIGH-4: Vulkan ICD reports a real driver version — `apiVersion`/`driverVersion` are set from the MVGAL version macros in the daemon-GPU path and copied in `mvgal_vkGetPhysicalDeviceProperties` (previously `0.0.0`).
- MED-1: `mvgal-info` DRM fallback reads the `enabled` state from `/etc/mvgal/mvgal.conf` instead of hard-coding every GPU as enabled.
- MED-2: `mvgal-bench` multi-GPU scaling figures are labeled as theoretical estimates, not measured results.
- MED-3: `load-module.sh` resolves module paths via `modinfo -n` instead of a hard-coded `/lib/modules/.../updates/dkms` path.
- MED-4: D-Bus policy for `org.mvgal.MVGAL` is restricted to root and the `mvgal` group (previously open to all users).
- MED-5: `mvgal-hw-validate` attributes device-node failures to "kernel module not loaded" with a load hint instead of a bare FAIL.
- MED-6: `/etc/mvgal/custom_strategy.lua` is now shipped as a no-op stub so the `[custom] script_path` reference in `mvgal.conf` always resolves.

### Changed
- Version bumped 0.7.7 → 0.7.8 (bugfix release)

## [v0.7.7] — 2026-09-21

### Fixed
- CRITICAL-1: Vulkan ICD device dispatch — `vkCreateImage`, `vkGetImageMemoryRequirements` and `vkDestroyImage` were missing from `vk_icdGetDeviceProcAddr`, leaving NULL entries in the loader's device dispatch table. Any app calling `vkCreateImage` (e.g. `vulkaninfo`'s `FillImageTypeSupport`) crashed with SIGSEGV (exit 139). The three image functions are now implemented (tagged allocation records, plausible size/alignment/memoryTypeBits) and registered.
- CRITICAL-2: Vulkan ICD `vkGetPhysicalDeviceQueueFamilyProperties2` wrote past the caller's array — the 1.0 helper writes all queue families starting at element 0's inner struct, overflowing the `VkQueueFamilyProperties2` array and corrupting the pNext chain (heap corruption / SIGABRT under multi-ICD setups). Now fills a temp buffer and copies per element.
- MED-1: Version macros unified — `mvgal-gui --version` now reports 0.7.7 (CMakeLists.txt was stale at 0.7.5 while Cargo.toml and the spec said 0.7.6).

### Changed
- Version bumped 0.7.6 → 0.7.7 (bugfix release)

## [v0.7.6] — 2026-09-17

### Fixed
- CRITICAL-1: Vulkan layer no longer returns `VK_ERROR_LAYER_NOT_PRESENT` from `vkEnumerateDeviceExtensionProperties` for physical devices it did not wrap (e.g. the Mesa dzn ICD). The loader aborted with a `VUID-physicalDevice-parameter` error (SIGABRT, exit 134) in `mvgal_amd_external_mem --scan`; the layer now forwards the call through any registered instance dispatch chain.
- HIGH-1: `mvgal-status` now prints an explicit DEGRADED MODE warning and exits non-zero when the `mvgal` kernel module is not loaded (Secure Boot / MOK rejection previously left the daemon silently running on sysfs/stub data).
- HIGH-2: `mvgal-config -c/--config` now writes to the requested config file — the pkexec helper parsed `--config` but `set_config_value` ignored it and always wrote `/etc/mvgal/mvgal.conf`.
- HIGH-3: Config helper append check is now section-scoped, so a key that also appears in a later section no longer suppresses appending it to the target section.
- MED-1: Daemon `SET_CONFIG` IPC handler validates the payload (printable ASCII + at least one `[section]`) and writes atomically (temp file + rename) instead of truncating the live config with a raw write.
- MED-2: `mvgal-dashboard` with no arguments prints a banner + usage hint instead of exiting silently.
- MED-3: Version macros unified — `mvgal --version` now reports 0.7.6 everywhere (`MVGAL_VERSION_PATCH` was stale at 3 while the string said 0.7.5).

### Changed
- Version bumped 0.7.5 → 0.7.6 (bugfix release)

## [v0.7.5] — 2026-09-15

### Fixed
- CRITICAL-1: DKMS install — `BUILT_MODULE_LOCATION=/kernel` for all modules so DKMS finds the `.ko` files built into the `kernel/` subdirectory. The previous `MAKE[1]` copy approach never ran because DKMS executes only one make command.
- CRITICAL-2: Secure Boot — `%post -n mvgal-dkms` now signs the DKMS-installed modules in `/lib/modules/*/updates/dkms` with the per-machine MVGAL key (previously only the kernel-tree modules were signed, so DKMS modules were rejected under Secure Boot). `mvgal-enroll-mok` now generates a one-time password when `-p` is omitted and always passes it to `mokutil --import`, so enrollment works through pkexec without a TTY.
- CRITICAL-3: Vulkan ICD implements the WSI entry points the loader requires — `vkGetPhysicalDeviceSurfaceSupportKHR`, `SurfaceCapabilitiesKHR`, `SurfaceFormatsKHR`, `SurfacePresentModesKHR`, plus `FormatProperties2`, `ImageFormatProperties2`, `SparseImageFormatProperties2`, `ExternalBuffer/Fence/SemaphoreProperties`, `ToolProperties` — so apps no longer abort with "ICD does not export vkGetPhysicalDeviceSurfaceSupportKHR!".

## [v0.7.4] — 2026-09-07

### Fixed
- CRITICAL-1: DKMS build layout — `dkms.conf` now copies the built `.ko` files from the `kernel/` subdirectory up to the DKMS build root so `dkms install` actually finds and installs `mvgal.ko` / `mvgal_ntsync.ko`; spec `%post` no longer swallows `dkms build`/`dkms install` failures
- CRITICAL-2: Vulkan ICD now exposes a placeholder physical device (instead of 0 devices) when no physical GPU is available or the daemon is not running
- CRITICAL-3: OpenCL CMake propagation fixed — `OpenCL_LIBRARIES`/`OpenCL_INCLUDE_DIRS` are now populated from the pkg-config result so the ICD links the loader correctly
- HIGH-1: `mvgal_amd_external_mem --no-mvgal` now implies `--scan` instead of printing usage
- HIGH-2: `mvgal-dashboard` and `mvgal-gui` gained `--check`/`--self-test` for non-hanging headless verification
- HIGH-3: `mvgal-enroll-mok -p/--password` is now passed to `mokutil --import` so enrollment works without a TTY through pkexec
- MED-1: `mvgal-probe` exits 0 when the DRM sysfs fallback detects GPUs (was 2)
- MED-2: `mvgal-steam-setup` with no arguments prints usage and exits 0
- MED-3: `mvgal-config set-power-profile` help now marks the option AMD-only and the error suggests `mvgal list-gpus`
- MED-4: `mvgal-load`/`mvgal-unload` self-escalate via pkexec using the existing `mvgal-pkexec-helper.sh`

### Changed
- Version bumped 0.7.3 → 0.7.4 (bugfix release)

## [v0.7.3] — 2026-09-02

### Fixed
- CRITICAL-2: `mvgal`/`mvgal-config` config writes now route through the `-c`-specified config file instead of always writing the default path; `mvgal-pkexec-helper.sh` gained a `--config` option
- HIGH-1: D-Bus policy now takes effect immediately after install — spec `%post` reloads the D-Bus daemon
- HIGH-2: `mvgal_amd_external_mem --scan` prints progress before each blocking Vulkan call and gained `--no-mvgal` to enumerate real vendor ICDs only (bypasses the MVGAL ICD)
- HIGH-3: `mvgal-dashboard` prints a startup banner when launched from a terminal so it no longer looks like it hangs with no output
- HIGH-4: `mvgal --version` reported 0.7.1 because `MVGAL_VERSION_PATCH` was stale; version macros unified
- MED-1: `mvgal-bench` accepts `synthetic`/`realworld` suite aliases matching `mvgal --help`
- MED-2: `mvgal-probe` no longer passes a closed fd to UAPI ioctls when the module is absent, and honors `-j` in the DRM sysfs fallback
- MED-4: `mvgal stop` returns non-zero when the daemon is not running
- MED-5: `mvgal start`/`stop`/`restart` detect systemd via `/run/systemd/system` instead of `systemctl is-system-running`, so degraded systems still use the systemd unit
- MED-6: `mvgal-gui` disables xdg-desktop-portal registration in the Application constructor (defense in depth)
- MED-7: `mvgal-compat` no longer shows the "Unknown title" note for applications found in the compatibility database
- MED-8: `--version` added to `mvgal-config`, `mvgal-probe`, `mvgal-enum`, `mvgal-hw-validate`, `mvgal-status`, `mvgal-compat`, and `mvgal-bench`

### Changed
- Version bumped 0.7.2 → 0.7.3 (bugfix release)

## [v0.7.2] — 2026-09-01

### Fixed
- CRITICAL-2: `mvgal-enroll-mok` false positive — verify output contains 'is enrolled'
- CRITICAL-3: daemon reads `[core] default_strategy` from config and maps it to the scheduler mode
- CRITICAL-4: D-Bus policy adds `receive_sender` for signal reception
- HIGH-2/3: `QT_ENABLE_PORTAL=0` set before `QApplication` construction (GUI + dashboard) to prevent portal hangs
- HIGH-4: `mvgal-status` falls back to `pidof` when systemctl is unavailable
- HIGH-5: `mvgal-info` falls back to `pidof` on socket ENOENT
- MED-2/3: `mvgal-config` uses `strtol` with validation instead of `atoi`
- MED-5: `modeToString` handles the `AI_DRIVEN` enum

### Changed
- Version bumped 0.7.1 → 0.7.2 (bugfix release)

## [v0.7.1] — 2026-09-01

### Fixed
- DKMS build failure: `kernel/Makefile` was a CMake-generated file with hardcoded local paths; replaced with a Kbuild wrapper that delegates to the kernel build system
- `mvgal-load` used the wrong module path and was missing `mvgal_mtt` and `mvgal_adreno`; now points at `/updates/dkms` and loads all 7 modules
- Custom strategy was accepted without verifying the script exists; both `mvgal` and `mvgal-config` now require `/etc/mvgal/custom_strategy.lua`
- `mvgal status` always reported "single GPU" because the CLI did not load the default config; now loads `/etc/mvgal/mvgal.conf` by default
- `config/mvgal.conf` enabled `gpu_1` on single-GPU systems; now disabled

### Changed
- Version bumped 0.7.0 → 0.7.1 (bugfix release)

## [v0.7.0] — 2026-08-31

### Added
- Multi-vendor OpenCL ICD aggregation: platforms/devices from all vendor ICDs merged into one logical OpenCL platform
- `-Bsymbolic-functions` link flag to fix re-entrant deadlock in the OpenCL interceptor
- `mvgal` CLI OpenCL platform/device enumeration reporting

### Changed
- Version bumped 0.6.0 → 0.7.0 across spec, CMake, Rust workspace, kernel module, daemon, GUI, dashboard, mvgal-bench, libmvgal, docs, and README

## [v0.4.0] — 2026-06-07

### Added
- GPU power management: NVML-based frequency/thermal control, sysfs power limit fallback, AMD PPL interception wrappers
- Dynamic GPU scoring scheduler with real-time telemetry integration
- NTSYNC kernel module with cross-device synchronization ioctls
- Multi-vendor Vulkan barrier translation and shader backend dispatching
- PCIe P2P DMA support with connectivity matrix in UAPI
- AI-driven scheduler model inference and prediction
- Unified VRAM heap management with DMA-BUF zero-copy
- Real-time Intel GPU VRAM and utilization queries
- NVML loader for NVIDIA power/temperature monitoring
- Proton bridge for Steam/Proton integration
- Full-stack build support via DKMS
- Tool suite: mvgal-info (heap tracking), mvgal-bench, mvgal-compat documentation
- P2P and DMA-BUF telemetry in kernel UAPI
- Cross-platform multi-GPU abstraction layers
- RPM/COPR: vendored Rust deps for offline builds, multi-distro support (Fedora 40-44, Rawhide, RHEL/AlmaLinux/Rocky 9 & 10, CentOS Stream 9 & 10, openSUSE Tumbleweed, Amazon Linux 2023)
- Author metadata updated to 'AxoGM' project-wide

### Changed
- Kernel module: C89 compat fixes, MODULE_IMPORT_NS threshold lowered to 6.12.0
- CMake: improved kernel version detection, LTO gated behind GCC >= 9
- PID files migrated to /run, D-Bus event loop integrated
- Daemon status IPC handling refactored
- Rust crate versions synced to workspace 0.4.0 (fence_manager, memory_safety, capability_model)
- All version references (spec, README, CMake) synced to 0.4.0

### Fixed
- Kernel module struct redefinition and duplicated code in mvgal_device.c
- Missing linux/version.h include in mvgal_device.c
- GCC 15+ RHEL_RELEASE_VERSION preprocessor syntax error
- class_create compat for EL9, libelf for EL8, Tumbleweed build scripts
- SPEC: LTO guard for GCC version, EL8 cmake bypass, glob patterns, Source0 URL
- RHEL 8 LTO linker errors for static archives and tools
- Daemon init order, IPC parsing, socket EACCES cleanup
- Vulkan 1.3 API guard for legacy headers
- Mageia kernel header paths and empty kernel-module.list
- Prometheus and SYCL backend static libs in spec
- Build: all -Werror warnings resolved (26/26 compile tests)

### Removed
- Stale Module.symvers and modules.order generated kernel module files
- Stale GitHub Actions CI/CD workflows (ci.yml, copr.yml)

## [v0.2.2] — 2026-05-16

### Changed
- Bumped active project, runtime, API wrapper, Vulkan ICD, Steam compatibility,
  UI, binding, and packaging metadata from 0.2.1/older stale versions to 0.2.2.
- Added Nix and Gentoo package metadata to the supported distribution set.

### Fixed
- Runtime daemon scheduler queue consumption and wait predicate behavior.
- Runtime daemon memory replication deadlock when populating additional GPUs.

### Added
- Remote GPU network pooling: UDP/TCP peer discovery, heartbeat health tracking,
  RemoteGpu integration with DeviceRegistry, latency-weighted scheduler scoring
- AI-driven scheduler: `mvgal_ai.h` model inference C API (`load_model`, `predict`),
  `[ai_scheduler]` config section, runtime enable/disable toggle
- Cross-crate Rust FFI integration test suite (`safe/ffi_tests/`) — 9 tests
  validating fence, memory, and capability lifecycle across C FFI boundaries

### Changed
- Rust FFI audit: `panic::catch_unwind` wrappers on all 19 `extern "C"` functions
  across `capability_model`, `fence_manager`, `memory_safety`
- Metrics collector expansion with additional GPU telemetry fields

### Fixed
- SDL error handling in benchmarks
- `mvgal_resolve` type mismatch in stress benchmark
- Unused variable warnings in stress benchmark
- Missing CMake include paths for `mvgald` target

### Removed
- Stale GitHub Actions CI/CD workflows (ci.yml, copr.yml)

## [v0.2.1] — 2026-05-01

### Added
- RPM/COPR packaging: spec file fixes for Fedora, conditional OpenCL, debuginfo
- Vulkan ICD with device, memory, command buffer, and sync entry points
- Real GPU querying for Vulkan ICD, stress benchmark cleanup
- Vulkan API interception tests
- Fedora COPR package badge and install instructions
- Configurable GPU selection strategies: AFR, single, all-device modes
- Automatic frame rendering (AFR) support for aggregated Vulkan devices
- Dynamic load balancing with mutex lifecycle fix in Vulkan device group emulator
- GPU driver telemetry integration into load balancer
- Cross-vendor semaphore synchronization and tile assembly logic
- Kernel stub ABI, Vulkan layer updates, pkexec privilege helper
- Steam/Proton compatibility layer

### Changed
- CMake: use GNUInstallDirs for proper lib64 detection, compatibility aliases
- RPM spec: remove non-ASCII chars for RPM 6.x compatibility
- Project homepage URL updated
- Documentation rewritten based on full code analysis

### Fixed
- Vulkan 1.4 header incompatibilities and duplicate declarations
- CMake nesting error in Vulkan detection logic
- Manual Vulkan header search fallback, path syntax
- GCC 15+ implicit-declaration error in `mvgal_rewrite_update_gpu_utilization`
- Missing MVGAL_INCLUDE_DIRS on Vulkan layer target
- Dead `mvgal_rewrite_update_gpu_utilization` call removed
- Forward declaration for `mvgal_get_queue_family_properties` in device_group.c
- Function name mismatch (`mvgal_gpu_` → `mvgal_`) in device_group.c
- Build fixes for openSUSE, Mageia 8 compat

## [0.2.1-5..0.2.1-12] — 2026-04/05

### Added
- Moore Threads Driver Installer with Loginwall Support
- Multi-Vendor Vulkan Device Group Emulation
- Dynamic Workload Rebalancing Engine
- Security Policies (Polkit)
- Weighted dynamic load balancing for SFR
- Moore Threads vendor ID (0x1ED5)

### Fixed
- RPM debuginfo package conflict
- Spec file to match actual build outputs

## [0.2.0-1] — 2026-04-21

### Added
- GPU enumeration and capability discovery
- Device group creation and management
- Basic workload distribution across GPUs
- Initial Vulkan device group emulation
- Compute kernel dispatch infrastructure

## [0.1.0-1] — 2026-04-20

### Added
- Initial project structure and build system
- Multi-vendor GPU abstraction layer design
- Basic memory management for cross-device buffers
- Fence synchronization primitives
- Core API specification

[v0.2.2]: https://github.com/TheCreateGM/mvgal/releases/tag/v0.2.2
[v0.2.1]: https://github.com/TheCreateGM/mvgal/releases/tag/v0.2.1
