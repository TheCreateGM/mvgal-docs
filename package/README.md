# MVGAL Package Artifacts

Release binaries for the documentation workspace, built from source tag **v0.7.16**
(`a9e19f6`) and produced by the upstream CI pipeline.

Every packaging format is present at the same version. Earlier revisions of this
page documented a split where only the RPMs were current and the other formats
lagged behind; that is no longer true, and the reason for it (the CI image lacked
`appimagetool` and `flatpak-builder`) has been resolved.

## What is here

All twelve binaries are v0.7.16. The three RPMs are published by the upstream COPR
project and are signed; the remaining formats are built by the CI pipeline from the
same source tag.

### RPM (Fedora / RHEL / SUSE / Mageia / Amazon Linux)

| File | Package | Notes |
|---|---|---|
| `mvgal-0.7.16-1.fc44.x86_64.rpm` | `mvgal` | Main package: binaries, libraries, headers, Vulkan layer, OpenCL ICD, polkit policy, D-Bus policy, and seven prebuilt kernel modules |
| `mvgal-dkms-0.7.16-1.fc44.x86_64.rpm` | `mvgal-dkms` | DKMS source tree under `/usr/src/mvgal-0.7.16`, built against whatever kernel you are running. **Prefer this over the prebuilt modules in `mvgal`** unless your kernel matches exactly |
| `mvgal-user-space-0.7.16-1.fc44.x86_64.rpm` | `mvgal-user-space` | Dependency metapackage — **intentionally contains no files** (see below) |
| `mvgal-0.7.16-1.fc44.src.rpm` | `mvgal` (source) | Upstream source tarball, for rebuilding or auditing |

### Other formats

| File | Notes |
|---|---|
| `mvgal_0.7.16_amd64.deb` | Debian / Ubuntu |
| `mvgal-dev_0.7.16_amd64.deb` | Headers and development files |
| `mvgal-dkms_0.7.16_amd64.deb` | DKMS source for Debian-family kernels |
| `mvgal-daemon_0.7.16_amd64.deb` | Daemon only |
| `mvgal-vulkan_0.7.16_amd64.deb` | Vulkan layer and ICD |
| `mvgal-0.7.16-x86_64.AppImage` | Portable single-file bundle |
| `mvgal-0.7.16-x86_64.tar.zst` | Source / binary tarball |
| `org.axogm.MVGAL-0.7.16-x86_64.flatpak` | Flatpak bundle |

Prefer your distribution's repository or the COPR project when one is configured.
The files here are a fallback and will not receive updates automatically.

## Install (Fedora / RPM distros)

```sh
sudo dnf install ./mvgal-dkms-0.7.16-1.fc44.x86_64.rpm
sudo dnf install ./mvgal-0.7.16-1.fc44.x86_64.rpm

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
   — that is the kernel the CI image was running, not a generic build. On any other
   kernel they are ignored entirely, and DKMS will build from `mvgal-dkms` instead.
   Do not read "the module is in the RPM" as "the module will load". See
   [Secure Boot](../docs/SECURE_BOOT.md) for signing DKMS-built modules.
2. **The `mvgald` polkit action points at `/usr/sbin/mvgald`,** while the RPM
   installs the binary to `/usr/bin/mvgald`. On Fedora's usrmerge
   (`/usr/sbin` → `/usr/bin`) this resolves, so the action works. On a
   distribution without usrmerge, the `com.mvgal.daemon.start` action will not
   match the installed path. Starting the daemon through systemd does not depend
   on this action.

## Verifying a download

```sh
rpm -qp --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' ./mvgal-0.7.16-1.fc44.x86_64.rpm
rpm -K ./mvgal-0.7.16-1.fc44.x86_64.rpm   # header signature
rpm -qlp ./mvgal-0.7.16-1.fc44.x86_64.rpm  # file list, without installing
```

SHA-256 of the files in this directory, as recorded by the build pipeline:

```
8e16b0d68b087d20db3c5f7a0409214d9169a995d18a0ce9f38ace830ed7fd2d  mvgal-0.7.16-1.fc44.x86_64.rpm
33ab04c5dce2a210d6dffe09f7645e5ec241bf903658f11c4ef89096f8bbb155  mvgal-dkms-0.7.16-1.fc44.x86_64.rpm
fd8ce2af920aeba392e83eb0ca553a3f9f995772b3f5269ae5f051a6827375bf  mvgal-user-space-0.7.16-1.fc44.x86_64.rpm
f95ac72adbf6b95198d9e12096ad10681caac36ad7eeb2fbaf5afd006e2cf2a3  mvgal-0.7.16-1.fc44.src.rpm
95b0058a041025d8239b170a738baf2c6804383e9b0c5702f5c42ea6af12722a  mvgal-0.7.16-x86_64.AppImage
daaa88861c469de62e532fbf24892a516f7f2fc0db77e825757872481d6b8eb0  mvgal-0.7.16-x86_64.tar.zst
14fcc1e597319cdafd24f980f3f6620f5ef5fe638fe548405e0c6207def03acb  mvgal_0.7.16_amd64.deb
85d2463be53325536ecfb134114a69d12fdd7d4563f2d98cef3ac705212cfa89  mvgal-dev_0.7.16_amd64.deb
c904b534a548348d1d06337193526c1facdad15a9d562004cc7efd8478a1af88  mvgal-dkms_0.7.16_amd64.deb
55d57b5088d743078e1fca0b9c04f303a9ba8fee6678803de69b8d33300ee2f2  mvgal-daemon_0.7.16_amd64.deb
2740bce3ef4b1f04791784757306c9323e6c14738feb3a05d2a6afca2a08d01d  mvgal-vulkan_0.7.16_amd64.deb
5afd8e3960cca2356c8b700b3709848d011f6abe5721b3d4a658b89b8e771273  org.axogm.MVGAL-0.7.16-x86_64.flatpak
```

`rpm -K` reports `NOKEY` unless the MVGAL signing key is imported — that means
the key is not in your local RPM database, not that the signature is bad. Import
the COPR repository key if you need full verification.

## Licensing

The RPM metadata declares `GPL-3.0-only`, matching the packaging. See the
[repository README](../README.md#license) for the discrepancy between that
declaration and the licenses used by the kernel sources themselves.
