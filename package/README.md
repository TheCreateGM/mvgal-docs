# MVGAL Package Artifacts

Release binaries for the documentation workspace. **Read the version column before
installing** — this directory holds more than one release, and the formats are
not in sync.

## What is here

### v0.7.14 — RPM only

These are the artifacts published by the upstream COPR build for Fedora 44. They
are the current release and are the ones to install.

| File | Package | Notes |
|---|---|---|
| `mvgal-0.7.14-1.fc44.x86_64.rpm` | `mvgal` | Main package: binaries, libraries, headers, Vulkan layer, OpenCL ICD, polkit policy, D-Bus policy, prebuilt kernel modules |
| `mvgal-dkms-0.7.14-1.fc44.x86_64.rpm` | `mvgal-dkms` | DKMS source tree under `/usr/src/mvgal-0.7.14` for building against a running kernel. **Prefer this over the prebuilt modules in `mvgal`** unless your kernel matches exactly |
| `mvgal-user-space-0.7.14-1.fc44.x86_64.rpm` | `mvgal-user-space` | Dependency metapackage — **intentionally contains no files** (see below) |
| `mvgal-0.7.14-1.fc44.src.rpm` | `mvgal` (source) | Upstream source tarball for rebuilding or auditing |

### v0.7.13 — every other format

`mvgal_0.7.13_amd64.deb`, `mvgal-dev_0.7.13_amd64.deb`, `mvgal-vulkan_0.7.13_amd64.deb`,
`mvgal-daemon_0.7.13_amd64.deb`, `mvgal-dkms_0.7.13_amd64.deb`,
`mvgal-0.7.13-x86_64.AppImage`, `mvgal-0.7.13-x86_64.tar.zst`, and
`org.axogm.MVGAL-0.7.13-x86_64.flatpak` are the **previous** release. They are
retained because no v0.7.14 equivalents were built when this page was updated —
see *Why only RPMs* below. Do not expect them to contain the v0.7.14 fixes listed
in the [changelog](../docs/CHANGELOG.md).

## Why only RPMs

The v0.7.14 RPMs are the real, signed, published release builds. The
0.7.13 files in the other formats could not be regenerated for 0.7.14 in the
environment where this page was written: the AppImage needs `appimagetool` and
the Flatpak needs `flatpak-builder`, and neither was available. Rather than
publish locally assembled binaries of unknown provenance, this directory carries
verified 0.7.14 RPMs and leaves the older formats at 0.7.13, clearly labelled.

If you need a 0.7.14 `.deb`, AppImage, tarball or Flatpak, build it from source
with the [Build Guide](../docs/BUILD.md), or watch the upstream repository for
CI-produced artifacts.

## Install (Fedora / RPM distros)

```sh
# DKMS builds the modules against your running kernel.
sudo dnf install ./mvgal-dkms-0.7.14-1.fc44.x86_64.rpm
sudo dnf install ./mvgal-0.7.14-1.fc44.x86_64.rpm

sudo systemctl enable --now mvgal-daemon
mvgal-info
```

`mvgal-user-space` is a metapackage that only pulls dependencies in; installing
it alone gives you an empty filesystem payload. That is by design, not a broken
build.

Prefer your distribution's repository or COPR when one is configured — the RPMs
here are a fallback and will not receive updates automatically.

## Two things to check before you trust an install

1. **Prebuilt modules are pinned to one kernel.** `mvgal` ships `.ko` files under
   `/usr/lib/modules/7.2.7-200.fc44.x86_64/`. On any other kernel they will be
   ignored, so use `mvgal-dkms` instead. See [Secure Boot](../docs/SECURE_BOOT.md)
   for signing the DKMS-built modules.
2. **The `mvgald` polkit action points at `/usr/sbin/mvgald`,** while the RPM
   installs the binary to `/usr/bin/mvgald`. On Fedora's usrmerge
   (`/usr/sbin` → `/usr/bin`) this resolves, so the action works. On a
   distribution without usrmerge, the `com.mvgal.daemon.start` action will not
   match the installed path. Starting the daemon through systemd does not depend
   on this action.

## Verifying a download

```sh
rpm -qp --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' ./mvgal-0.7.14-1.fc44.x86_64.rpm
rpm -K ./mvgal-0.7.14-1.fc44.x86_64.rpm   # header signature
rpm -qlp ./mvgal-0.7.14-1.fc44.x86_64.rpm  # file list, without installing
```

SHA-256 of the v0.7.14 files in this directory:

```
ec88452a8a42a88021ea9d2ed55493e1ef4a4f272f2bab72148f54779e261b1d  mvgal-0.7.14-1.fc44.x86_64.rpm
f71c9c5e6a41d9a6a3634967dfb38f608a348307b07af4ca406df57924e2f74f  mvgal-dkms-0.7.14-1.fc44.x86_64.rpm
23306e1d540541ee75fc2533c6e1c28efaf00164e7029da32b915fdb29c2421f  mvgal-user-space-0.7.14-1.fc44.x86_64.rpm
ab217e483c958262644c68d386f169db4ac4a5d63f65c752ca1d20a6c917efe8  mvgal-0.7.14-1.fc44.src.rpm
```

`rpm -K` reports `NOKEY` unless the MVGAL signing key is imported — that means
the key is not in your local RPM database, not that the signature is bad. Import
the COPR repository key if you need full verification.

## Licensing

The RPM metadata declares `GPL-3.0-only`, matching the packaging. See the
[repository README](../README.md#license) for the discrepancy between that
declaration and the licenses used by the kernel sources themselves.
