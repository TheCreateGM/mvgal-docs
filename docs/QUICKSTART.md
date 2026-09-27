---
tags: [mvgal, quickstart, guide]
aliases: [Quick Start, Quickstart]
---

# MVGAL Quick Start

> Source metadata is **0.7.13**; the source changelog documents releases through **0.7.12**. GPU discovery and API availability do not imply cross-vendor workload execution. Unsupported kernel submission and VRAM allocation paths return `-EOPNOTSUPP`.

This guide covers package discovery, basic diagnostics, and service startup. Package publication and optional components depend on the distribution and build.

## 1. Inspect the package or build

The documentation workspace's `package/` directory contains 0.7.13 artifacts for several package formats. Select the artifact matching your distribution and architecture, or build from the [Build Guide](BUILD.md). The source repository includes package definitions, but availability from a remote COPR repository can change.

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
systemctl status mvgald
journalctl -u mvgald -b --no-pager
```

Then inspect current device status:

```bash
mvgal-info
mvgal-status --once
```

`mvgal-status` may return a non-zero exit status when the MVGAL kernel module is not loaded. That status is a degraded-mode signal, not proof that the userspace daemon failed.

## 5. Check capability support

Inspect the device capability information exposed by the installed kernel/runtime. In source version 0.7.12, the changelog states that kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle are not advertised as supported. Do not interpret a listed strategy, API function, or detected GPU as evidence those operations work.

## Secure Boot

For packages that install signed DKMS modules, follow [Secure Boot](SECURE_BOOT.md). Verify package-specific key paths and confirm enrollment with `mokutil --list-enrolled` before diagnosing module loading.

## Troubleshooting

See [Troubleshooting](TROUBLESHOOTING.md) for supported diagnostic commands. See [Status](STATUS.md) for implementation boundaries and release provenance.
