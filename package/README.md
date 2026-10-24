# MVGAL Package Artifacts

This directory currently contains package files named for MVGAL **0.7.27**, produced by the `mvgal-packages` Jenkins job together with `BUILD-INFO.txt` (the source commit, build date and builder) and `SHA256SUMS` over every artefact here. Verify the checksums before installing; check each file's package metadata and signature too.

## Files present

| File | Format |
|---|---|
| `mvgal-0.7.27-1.fc44.src.rpm` | Fedora source RPM |
| `mvgal-0.7.27-1.fc44.x86_64.rpm` | Fedora binary RPM |
| `mvgal-dkms-0.7.27-1.fc44.x86_64.rpm` | Fedora DKMS RPM |
| `mvgal-user-space-0.7.27-1.fc44.x86_64.rpm` | Fedora userspace metapackage |
| `mvgal_0.7.27_amd64.deb` | Debian-family main package |
| `mvgal-daemon_0.7.27_amd64.deb` | Debian-family daemon package |
| `mvgal-dev_0.7.27_amd64.deb` | Debian-family development package |
| `mvgal-dkms_0.7.27_amd64.deb` | Debian-family DKMS package |
| `mvgal-vulkan_0.7.27_amd64.deb` | Debian-family Vulkan package |
| `mvgal-0.7.27-x86_64.AppImage` | AppImage |
| `mvgal-0.7.27-x86_64.tar.zst` | Compressed tar archive |
| `org.axogm.MVGAL-0.7.27-x86_64.flatpak` | Flatpak bundle |
| `SHA256SUMS` | Checksums over the files in this directory |
| `BUILD-INFO.txt` | Build provenance: version, git commit, build date, builder |

## Inspect before installing

```sh
sha256sum -c SHA256SUMS
rpm -qp --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' ./*.rpm
rpm -K ./*.rpm
dpkg-deb -f ./mvgal_0.7.27_amd64.deb Package Version Architecture
```

`rpm -K` may report `NOKEY` when the signing key is not imported locally. Confirm the key and source of each package through the channel that supplied it. The Fedora RPMs are also built on COPR (`axogm/mvgal`); installation through that repository is described in the [Install guide](../docs/INSTALL.md). A package file's presence here does not mean it is current in a remote repository or tested on your GPU/kernel combination.

For module signing and kernel compatibility, see [Secure Boot](../docs/SECURE_BOOT.md). For supported build paths and options, see [Build Guide](../docs/BUILD.md). The project's [status page](../docs/STATUS.md) distinguishes packaging evidence from runtime and hardware validation.
