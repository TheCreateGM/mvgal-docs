# MVGAL Package Artifacts

Release binaries for the documentation workspace, built from source tag **v0.7.20**
(`76076f9`) by the upstream COPR project and the upstream CI pipeline.

Every packaging format is present at the same version. Earlier revisions of this
page documented a split where only the RPMs were current and the other formats
lagged behind; that is no longer true, and the reason for it (the CI image lacked
`appimagetool` and `flatpak-builder`) has been resolved.

`BUILD-INFO.txt` is the build pipeline's own provenance record. It is not a
distributable.

## What is here

All twelve binaries are v0.7.20. The RPMs are published by the upstream COPR
project; the remaining formats are built by the CI pipeline from the same source
tag. Every checksum below was verified against the pipeline's own `SHA256SUMS`
after copying, not transcribed from it by hand.

### RPM (Fedora / RHEL / SUSE / Mageia / Amazon Linux)

| File | Package | Notes |
|---|---|---|
| `mvgal-0.7.20-1.fc44.x86_64.rpm` | `mvgal` | Main package: binaries, libraries, headers, Vulkan layer, OpenCL ICD, polkit policy, D-Bus policy, and seven prebuilt kernel modules |
| `mvgal-dkms-0.7.20-1.fc44.x86_64.rpm` | `mvgal-dkms` | DKMS source tree under `/usr/src/mvgal-0.7.20`, built against whatever kernel you are running. **Prefer this over the prebuilt modules in `mvgal`** unless your kernel matches exactly |
| `mvgal-user-space-0.7.20-1.fc44.x86_64.rpm` | `mvgal-user-space` | Dependency metapackage — **intentionally contains no files** (see below) |
| `mvgal-0.7.20-1.fc44.src.rpm` | `mvgal` (source) | Upstream source tarball, for rebuilding or auditing |

### Other formats

| File | Notes |
|---|---|
| `mvgal_0.7.20_amd64.deb` | Debian / Ubuntu |
| `mvgal-dev_0.7.20_amd64.deb` | Headers and development files |
| `mvgal-dkms_0.7.20_amd64.deb` | DKMS source for Debian-family kernels |
| `mvgal-daemon_0.7.20_amd64.deb` | Daemon only |
| `mvgal-vulkan_0.7.20_amd64.deb` | Vulkan layer and ICD |
| `mvgal-0.7.20-x86_64.AppImage` | Portable single-file bundle |
| `mvgal-0.7.20-x86_64.tar.zst` | Source / binary tarball |
| `org.axogm.MVGAL-0.7.20-x86_64.flatpak` | Flatpak bundle |

Prefer your distribution's repository or the COPR project when one is configured.
The files here are a fallback and will not receive updates automatically.

## Install (Fedora / RPM distros)

```sh
sudo dnf install ./mvgal-dkms-0.7.20-1.fc44.x86_64.rpm
sudo dnf install ./mvgal-0.7.20-1.fc44.x86_64.rpm

sudo systemctl enable --now mvgal-daemon
mvgal-info
```

`mvgal-user-space` is a metapackage that only pulls dependencies in. Its payload
is literally `(contains no files)`; what it requires is `libdrm`, `mvgal`,
`mvgal-dkms`, `systemd` and `vulkan-loader`. Installing it alone gives you an
empty filesystem. That is by design, not a broken build.

## Two things to check before you trust an install

1. **Prebuilt modules are pinned to one kernel, and that kernel is not yours.**
   The seven `.ko` files in `mvgal` live under `/usr/lib/modules/6.19.10-300.fc44.x86_64/`
   — that is the kernel the build host was running, not a generic build. On any
   other kernel they are ignored entirely, and DKMS will build from `mvgal-dkms`
   instead. Do not read "the module is in the RPM" as "the module will load". See
   [Secure Boot](../docs/SECURE_BOOT.md) for signing DKMS-built modules.
2. **The `mvgald` polkit action points at `/usr/sbin/mvgald`,** while the RPM
   installs the binary to `/usr/bin/mvgald`. On Fedora's usrmerge
   (`/usr/sbin` → `/usr/bin`) this resolves, so the action works. On a
   distribution without usrmerge, the `com.mvgal.daemon.start` action will not
   match the installed path. Starting the daemon through systemd does not depend
   on this action.

The shipped `com.mvgal.policy` declares exactly two actions,
`com.mvgal.privileged.helper` and `com.mvgal.daemon.start`, and both default to
`auth_admin`. No action grants access to an unauthenticated caller.

## Verifying a download

```sh
rpm -qp --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' ./mvgal-0.7.20-1.fc44.x86_64.rpm
rpm -K ./mvgal-0.7.20-1.fc44.x86_64.rpm   # header signature
rpm -qlp ./mvgal-0.7.20-1.fc44.x86_64.rpm  # file list, without installing
```

SHA-256 of the files in this directory, as recorded by the build pipeline and
re-verified after copying:

```
d40e967c1400b0c0ce9e2457a6fbbe78cf0585ef813e701fc6695c68c15b93b0  mvgal-0.7.20-1.fc44.src.rpm
b293039c2639567e8c9e572300ddb3b1e120c58e9a4aa312a121e65a31501d27  mvgal-0.7.20-1.fc44.x86_64.rpm
df89392b4e6c1cf75d5826b00647381a8daeddd331a36477a3c2a795ce2c2aa0  mvgal-dkms-0.7.20-1.fc44.x86_64.rpm
60db954c333125aab6f4805541bdf8047fadc4720933a203305f60a7483fa60d  mvgal-user-space-0.7.20-1.fc44.x86_64.rpm
6e00392cab6f5c317feddf9a9883ac6f4b51cecb114f4808d3e9e4a72bd03d6d  mvgal-0.7.20-x86_64.AppImage
6f003b2badde28605d1e17e363cef3ccebbf10302575860836c7fad2a44d173e  mvgal-0.7.20-x86_64.tar.zst
49e7580328fd226a6b51ed8de8d49a7754e0925c57636d6846558e9a0a687666  mvgal_0.7.20_amd64.deb
f5f1d82a1f4e9fbd2335d39d59a3f49bff387c80968a5252f32e81d3d8ebb30e  mvgal-dev_0.7.20_amd64.deb
60639542c68f907e3dab59b93e9dce90c19aa62b558a6cc80f63344db6b8c32e  mvgal-dkms_0.7.20_amd64.deb
e904ec29c3b643e81b4730f4a7f525047ab574c4fb4d046ac816aa18ae63350d  mvgal-daemon_0.7.20_amd64.deb
e033c13af71d8c645939534e312eb7f564930923410f066cae50c299f18b6934  mvgal-vulkan_0.7.20_amd64.deb
1dcb32b8810bf4eecd37b4f7a691fc0a718346ee1c7b0ceb6000996a3ec2f18c  org.axogm.MVGAL-0.7.20-x86_64.flatpak
18706baf3d1ca9bee49aa235cbdb4b03e0367def4a2e4b381f48af2e9c967bd5  BUILD-INFO.txt
```

`rpm -K` reports `NOKEY` unless the MVGAL signing key is imported — that means
the key is not in your local RPM database, not that the signature is bad. Import
the COPR repository key if you need full verification.

## Which of these are reproducible

The source tarball inside the SRPM, and the SRPM itself, are byte-identical when
rebuilt from tag `v0.7.20`. The binary RPM is **not**: rpmbuild injects a random
ELF build-id, and the build directory is baked into DWARF, so 68 of 218 payload
files differ between two rebuilds of the same commit. Both RPMs here therefore
share a `BUILDTIME` equal to the commit date, but not a checksum. See
[Build Guide](../docs/BUILD.md) § Reproducibility.

## Licensing

The RPM metadata declares `GPL-3.0-only`, matching the packaging. See the
[repository README](../README.md#license) for the discrepancy between that
declaration and the licenses used by the kernel sources themselves.
