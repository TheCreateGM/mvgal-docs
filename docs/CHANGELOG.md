---
tags: [mvgal, changelog, reference]
aliases: [Changelog, Release Notes]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: reference
mvgal_order: 13
---

# Changelog

All notable changes to MVGAL (Multi-Vendor GPU Aggregation Layer) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
