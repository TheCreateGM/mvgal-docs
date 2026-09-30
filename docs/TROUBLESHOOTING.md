---
tags: [mvgal, troubleshooting, guide]
aliases: [Troubleshooting, FAQ]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: guide
mvgal_order: 4
---

# MVGAL Troubleshooting Guide

> Source metadata is **0.7.16**; the source changelog documents releases through **0.7.16**. Unsupported kernel submission and VRAM allocation paths return `-EOPNOTSUPP`. Diagnose the installed build and the specific capability in question.

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

`mvgal-status` returns a non-zero status if the MVGAL kernel module is not loaded. `mvgal-info` can still discover GPUs through the system's DRM/sysfs interfaces. Discovery alone does not establish that submission, allocation, DMA-BUF export, or P2P works.

## Package or command not found

Check the artifact matches your distribution and architecture, then inspect its contents with the package manager (`rpm -ql <package>` or `dpkg -L <package>`). Package files in this documentation workspace do not establish that a remote COPR repository is currently published. The installed binaries' `--help` output is authoritative for their command syntax.

## Daemon does not start

```bash
systemctl status mvgald
journalctl -u mvgald -b --no-pager
```

Check that the unit and daemon were installed by the selected package. Do not create a socket or D-Bus policy manually using paths copied from an older release; compare against the packaged unit and configuration files.

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
mokutil --list-enrolled
```

The module must also have been built for the running kernel. A successful MOK enrollment does not fix a missing or incompatible module build.

## GPU is missing from MVGAL output

```bash
lspci -nn | grep -Ei 'VGA|3D|Display'
ls -l /sys/class/drm/
lsmod | grep -E 'mvgal|amdgpu|nvidia|i915|xe|mtgpu'
mvgal-info
```

Confirm the operating system detects the device and its native vendor driver is installed. MVGAL 0.7.12 removed GPU PCI binding so that native drivers retain device ownership. GPU detection is read-only and does not make MVGAL the GPU's kernel driver.

## Operation reports unsupported

This can be expected. In 0.7.12, runtime capability probing deliberately leaves kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle unsupported. Vendor operations that previously returned success without doing work were changed to return `-EOPNOTSUPP`. Check the source changelog and probed capability information rather than assuming a strategy or API name is implemented for the device.

## Steam / Proton

Use `mvgal-steam-setup --help` to see setup options provided by the installed build. Check game logs and the Vulkan loader's layer discovery output when investigating a layer. Do not use `mvgal-sched`, `mvgal-powercurve`, or environment-variable examples unless those commands/variables are present in the installed version; they are not all provided by the current build definitions.

## Report a reproducible issue

Include the installed MVGAL version, distribution, kernel version, GPU model and native driver, exact command, full error output, and relevant service or kernel log lines. Separate successful discovery from successful allocation, submission, synchronization, and transfer tests.
