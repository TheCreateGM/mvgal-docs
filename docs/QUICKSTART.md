---
tags: [mvgal, quickstart, guide]
aliases: [Quick Start, Quickstart]
mvgal_version: "0.7.31"
mvgal_verified: 2026-10-30
mvgal_role: guide
mvgal_order: 1
---

# MVGAL Quick Start

> Source metadata is **0.7.31***; the source changelog documents releases through **0.7.31**. GPU discovery and API availability do not imply cross-vendor workload execution. Unsupported kernel submission and VRAM allocation paths return `-EOPNOTSUPP`.

## 1. Inspect the package or build

The documentation workspace contains 0.7.28 package artifacts in RPM, DEB, AppImage and tarball formats. Inspect package metadata and signatures before installation; see [`package/README.md`](https://github.com/TheCreateGM/mvgal-docs/blob/main/package/README.md) for the current inventory. Package availability through remote repositories varies. For source builds, follow the [Build Guide](BUILD.md).

> [!note]
> On RPM distributions, check the module package metadata and kernel version before choosing prebuilt modules or DKMS. Secure Boot and kernel-header requirements are covered in [Secure Boot](SECURE_BOOT.md).

## 2. Inspect GPUs

```bash
lspci -nn | grep -Ei 'VGA|3D|Display'
ls /sys/class/drm/
```

If MVGAL is installed, enumerate devices:

```bash
mvgal-info
mvgal-enum --help
```

GPU discovery reports devices and telemetry available from the installed drivers. It does not mean MVGAL owns those GPUs or can submit workloads to them.

## 3. Check installed commands

Use command help from the installed version rather than relying on examples from older docs:

```bash
mvgal --help
mvgal-info --help
mvgal-status --help
mvgal-config --help
mvgal-steam-setup --help
```

## 4. Start and inspect the daemon

If the package installed the systemd unit:

```bash
pkexec systemctl start mvgald
# or, equivalently:
mvgal start
systemctl status mvgald
journalctl -u mvgald -b --no-pager
```

Since v0.7.31, `mvgal start` checks for `/sys/module/mvgal` after launching the
daemon and prints a degraded-mode warning if the kernel module is absent (e.g.
on a Secure Boot machine where the MOK has not been enrolled).

Then inspect current device status:

```bash
mvgal-info
mvgal-status --once
```

`mvgal-status` uses a three-tier exit code:

| Exit code | Meaning |
|----------|---------|
| `0` | Healthy — daemon running and kernel module loaded |
| `1` | Degraded — daemon running, kernel module not loaded (userspace-only mode) |
| `2` | Down — daemon not running |

A non-zero status from `mvgal-status` is a degraded-mode signal, not proof that the userspace daemon failed. On a Secure Boot machine where the MOK is not yet enrolled, the exit code is `1`, not `0`.

## 5. Check capability support

Inspect the device capability information exposed by the installed kernel/runtime. In source version 0.7.12, the changelog states that kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle are not advertised as supported. Do not interpret a listed strategy, API function, or detected GPU as evidence those operations work.

## Secure Boot

For packages that install signed DKMS modules, follow [Secure Boot](SECURE_BOOT.md). Confirm enrollment with `mokutil --test-key /var/lib/mvgal/keys/mvgal-signing.der` — not by grepping the enrolled list for `MVGAL`, which matches any MVGAL keypair including a stale one (see [SECURE_BOOT.md](SECURE_BOOT.md) § Verifying Enrollment).

## Troubleshooting

See [Troubleshooting](TROUBLESHOOTING.md) for supported diagnostic commands. See [Status](STATUS.md) for implementation boundaries and release provenance.
