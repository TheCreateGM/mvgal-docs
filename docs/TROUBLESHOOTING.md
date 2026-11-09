---
tags: [mvgal, troubleshooting, guide]
aliases: [Troubleshooting, FAQ]
mvgal_version: "0.7.44"
mvgal_verified: 2026-11-08
mvgal_role: guide
mvgal_order: 4
---

# MVGAL Troubleshooting Guide

> Source metadata is **0.7.44**; the source changelog documents releases through **0.7.44**. Unsupported kernel submission and VRAM allocation paths return `-EOPNOTSUPP`. Diagnose the installed build and the specific capability in question.

## Start with supported diagnostics

```bash
mvgal --help
mvgal-info --help
mvgal-status --help
mvgal-config --help
mvgal-info
mvgal-status --once
```

For service and kernel messages:

```bash
systemctl status mvgald
journalctl -u mvgald -b --no-pager
journalctl -k -b --no-pager | grep -i mvgal
```

`mvgal-status` returns a three-tier exit code: `0` = healthy (daemon up, module loaded), `1` = degraded (daemon running, module absent), `2` = daemon not running. A return of `1` is expected on a Secure Boot machine where the MOK has not been enrolled, and is not a daemon failure. `mvgal-info` can still discover GPUs through the system's DRM/sysfs interfaces. Discovery alone does not establish that submission, allocation, DMA-BUF export, or P2P works.

## Package or command not found

Check the artifact matches your distribution and architecture, then inspect its contents with the package manager (`rpm -ql <package>` or `dpkg -L <package>`). Package files in this documentation workspace do not establish that a remote COPR repository is currently published. The installed binaries' `--help` output is authoritative for their command syntax.

## Daemon does not start

```bash
systemctl status mvgald
journalctl -u mvgald -b --no-pager
```

Check that the unit and daemon were installed by the selected package. Do not create a socket or D-Bus policy manually using paths copied from an older release; compare against the packaged unit and configuration files.

## Daemon socket permissions

Symptom: the daemon is running, but every CLI-to-daemon operation fails for a
normal user while working under `sudo`. `mvgal show-stats` returns zeros,
`mvgal status` cannot read live state, and connecting to the socket directly
gives `Permission denied`:

```bash
systemctl is-active mvgald
ls -l /run/mvgal/mvgal.sock
id -nG "$USER"
nc -U /run/mvgal/mvgal.sock
```

A healthy socket is `srw-rw---- root:mvgal`. Two different failures look
identical from the CLI, so read the socket's actual owner first:

| Socket shows | Meaning | Fix |
|---|---|---|
| `root:mvgal` | Correct ownership; your session lacks the group | `pkexec usermod -aG mvgal "$USER"`, then **log out and back in** — a new login is required for the supplementary group to appear |
| `root:root` | The daemon failed to hand the socket to the group; this is a daemon-side defect, not a group membership problem | Report it with `ls -l /run/mvgal/mvgal.sock` and the daemon's journal |

Do not work around `root:root` by adding your user to group 0 or by making the
socket world-writable. Both grant privilege the group model is meant to keep
out of ordinary use; the group exists precisely so that access to the daemon is
granted without root.

On versions before 0.7.21 the packaged unit omitted `CAP_CHOWN` from its
`CapabilityBoundingSet`, so the uid-0 daemon could not change the socket's
group — root is not a member of `mvgal`, and the call failed with `EPERM`
regardless of group membership. Both daemons now log that failure instead of
discarding it, so a recurring occurrence should appear in
`journalctl -u mvgald -b`.

## Kernel module does not load

```bash
uname -r
modinfo mvgal
dkms status
journalctl -k -b --no-pager | grep -Ei 'mvgal|key was rejected|module verification'
```

If Secure Boot rejects a signed module, use the package's `mvgal-enroll-mok` helper when available, complete enrollment in the firmware MOK screen after reboot, and verify with:

```bash
mokutil --sb-state
mokutil --test-key /var/lib/mvgal/keys/mvgal-signing.der   # exit 0 = this key is trusted
```

> Verify with `--test-key`, **not** `mokutil --list-enrolled | grep MVGAL`. Every
> MVGAL keypair shares one subject, so after the key is regenerated the old
> certificate is still listed, the grep passes, and modules signed by the new key
> are still rejected. `mvgald` had that bug and stayed silent about it; v0.7.22+
> uses `--test-key`.

### "Invalid parameters" or "decompression failed with status 6"

The module could not be **decompressed**, which happens before the Secure
Boot signature is ever checked. On v0.7.21 and v0.7.22 the modules were
compressed with `xz -9e`, producing a CRC64 stream that the kernel's
decoder rejects (it accepts CRC32 and below). Enrolling the MOK does not
help here — the failure is upstream of the signature check.

```bash
xz --list --verbose /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/mvgal/mvgal.ko.xz | grep Check
```

`Check: CRC32` is what the kernel accepts. Anything else fails to
decompress. Fix:

```bash
pkexec /usr/lib/mvgal/mvgal-sign-modules.sh
```

Fixed in v0.7.25, which uses the kernel's own compression settings
(`xz --check=crc32 --lzma2=dict=1MiB`).

### "Key was rejected by service" but the key *is* enrolled

Check that every module carries the same signature. On v0.7.21 and earlier,
`mvgal_ntsync.ko` — a hard dependency of `mvgal.ko` — was signed with DKMS's own
key while `mvgal-enroll-mok` enrolled only the MVGAL key, so enrollment could
never fix it:

```bash
for ko in $(find /lib/modules/$(uname -r) -name 'mvgal*.ko*'); do
  printf '%-60s ' "$ko"; modinfo -F signer "$ko" 2>/dev/null || echo "(unsigned)"
done
```

Anything reporting `DKMS module signing key` is the defect. Fix:

```bash
pkexec /usr/lib/mvgal/mvgal-sign-modules.sh
```

This handles the `.ko.xz` modules DKMS installs on a compression-enabled distro
(a compressed module cannot be signed in place), covers every directory a module
can land in, and is safe to re-run. Fixed in v0.7.22.

### `mvgal unload-module` fails with "Module mvgal is in use"

The core `mvgal` module has hard dependents — the vendor shims
(`mvgal_intel`, `mvgal_amd`, `mvgal_nvidia`, `mvgal_mtt`, `mvgal_adreno`)
and `mvgal_ntsync`. Running `modprobe -r mvgal` directly cannot remove a
module with dependents, so it fails with "Module mvgal is in use". Use the
provided unloader, which removes the dependents first:

```bash
pkexec mvgal unload-module
```

Fixed in v0.7.32; the CLI now routes through the pkexec helper, which
unloads in reverse dependency order and names the blocker if one holds a
reference. Since v0.7.33 the helper only names modules that are actually
loaded — it reads `/proc/modules` instead of reciting a fixed list — and it no
longer leaks shell job-control notices such as `Killed`.

### The module is stuck in `Unloading` and nothing can load it again

```bash
grep '^mvgal ' /proc/modules
# mvgal 327680 -1 - Unloading 0x0000000000000000 (OE-)
dd if=/dev/mvgal0 of=/dev/null bs=1 count=1
# dd: failed to open '/dev/mvgal0': No such device or address
```

A refcount of `-1` with state `Unloading` means `module_exit` never finished.
The root cause fixed in v0.7.34 was the idle-gate sweep re-queuing itself
unconditionally, so `cancel_delayed_work_sync()` never returned during teardown
and the module stayed in `MODULE_STATE_GOING` while `/dev/mvgal0` returned
ENXIO. `mvgal unload-module` and `mvgal status` now detect this state and say a
reboot is required; on a build older than 0.7.34, or if it still happens, a
reboot is the only recovery — `rmmod`, `modprobe` and a daemon restart all
fail against a module in that state.

### `/dev/mvgal0` exists but every open fails

Presence of the device node is not proof that the module is usable. Since
v0.7.33 every tool shares `tools/mvgal_device_state.h`, which really opens
`/dev/mvgal0` and reports one of four states:

| State | Meaning |
|-------|---------|
| not loaded | `/sys/module/mvgal` is absent |
| wedged | loaded but stuck in `Unloading` (reboot required) |
| loaded but unusable | module present, `open()` fails with ENXIO/EPERM |
| OK | `open()` succeeded |

`mvgal status`, `mvgal-hw-validate`, `mvgal-probe`, `mvgal-info` and the daemon
all use it, so they can no longer report `Kernel Module: loaded` while every
open fails. `mvgal-probe` likewise distinguishes "module not loaded" from
"module loaded but the device is unusable" instead of claiming the module is
absent.

### Load with `mvgal-load`, not `modprobe mvgal`

```bash
pkexec mvgal-load
```

`mvgal.ko` depends on `mvgal_ntsync.ko`, so `modprobe mvgal` fails on the
dependency while naming only the outer module. `mvgal-load` loads the inventory
in order, reports which module was rejected, and prints the enrollment steps when
Secure Boot is the cause.

## GPU is missing from MVGAL output

```bash
lspci -nn | grep -Ei 'VGA|3D|Display'
ls -l /sys/class/drm/
lsmod | grep -E 'mvgal|amdgpu|nvidia|i915|xe|mtgpu'
mvgal-info
```

Confirm the operating system detects the device and its native vendor driver is installed. MVGAL 0.7.12 removed GPU PCI binding so that native drivers retain device ownership. GPU detection is read-only and does not make MVGAL the GPU's kernel driver.

### GPU appears in `lspci` but not in `mvgal-info`

Since v0.7.31, a display-class PCI device whose native driver is not bound is
**skipped** by both the kernel module and the userspace daemon — if
`pdev->driver` is `NULL` (blacklisted or no driver loaded), the GPU is invisible
to MVGAL enumeration to keep kernel and userspace GPU indices consistent.

`mvgal-enum` and `mvgal list-gpus` now emit a warning to stderr for any
display-class PCI device (class `0x03xx`) with a known GPU vendor ID (AMD
`0x1002`, NVIDIA `0x10de`, Intel `0x8086`, Moore Threads `0x1ed5`) that has no
DRM card node:

```
Warning: GPU 1ed5:0102 (Moore Threads) on PCI 0000:01:00.0 has no DRM device node —
driver may be blacklisted. MVGAL cannot use it for rendering.
```

Check `/etc/modprobe.d/` for blacklist entries (the test environment blacklists
`mtgpu_stub` and `sgpu_km`) and confirm the driver is installed and not
blocked.

## Operation reports unsupported

This can be expected. In 0.7.12, runtime capability probing deliberately leaves kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle unsupported. Vendor operations that previously returned success without doing work were changed to return `-EOPNOTSUPP`. Check the source changelog and probed capability information rather than assuming a strategy or API name is implemented for the device.

## Steam / Proton

Use `mvgal-steam-setup --help` to see setup options provided by the installed build. Check game logs and the Vulkan loader's layer discovery output when investigating a layer. Do not use `mvgal-sched`, `mvgal-powercurve`, or environment-variable examples unless those commands/variables are present in the installed version; they are not all provided by the current build definitions.

## Report a reproducible issue

Include the installed MVGAL version, distribution, kernel version, GPU model and native driver, exact command, full error output, and relevant service or kernel log lines. Separate successful discovery from successful allocation, submission, synchronization, and transfer tests.
