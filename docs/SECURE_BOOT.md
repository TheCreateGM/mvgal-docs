---
tags: [mvgal, secure-boot, mok, kernel, guide]
aliases: [Secure Boot, MOK, MOK Enrollment]
mvgal_version: "0.7.29"
mvgal_verified: 2026-10-27
mvgal_role: guide
mvgal_order: 3
---

# MVGAL Secure Boot & MOK Enrollment

> **Implementation status:** Source metadata is 0.7.28. The source changelog documents through 0.7.28. Treat design/API descriptions as available only where the relevant code path and runtime capability are verified; unsupported kernel submission and VRAM allocation return `-EOPNOTSUPP`.

**Source version:** 0.7.29 | **Updated:** October 2026

MVGAL ships seven kernel modules. On systems with **UEFI Secure Boot** enabled, the kernel refuses to load modules that are not signed by a trusted key. MVGAL solves this with **per-machine key signing** and **MOK (Machine Owner Key) enrollment**.

The modules, in the order `/usr/lib/mvgal/modules.sh` loads them (dependencies first):

| Module | Role |
|---|---|
| `mvgal_ntsync.ko` | NTSYNC synchronisation. `mvgal.ko` declares a dependency on it, so it must load first. |
| `mvgal.ko` | Core, device node, and all subsystems — one combined module. |
| `mvgal_nvidia.ko` | NVIDIA shim (optional) |
| `mvgal_amd.ko` | AMD shim (optional) |
| `mvgal_intel.ko` | Intel shim (optional) |
| `mvgal_mtt.ko` | Moore Threads shim (optional) |
| `mvgal_adreno.ko` | Adreno shim (optional) |

`mvgal-load`, `mvgal-unload`, and the pkexec helper all source that one inventory, so they cannot disagree about order or membership. Set `$MVGAL_MODULE_LIST` to override it.

---

## How It Works

1. **Install time** — the RPM `%post` script generates a per-machine MVGAL signing keypair under `/var/lib/mvgal/keys` (directory mode `0700`, private key mode `0600`) and signs the installed modules with `/usr/lib/mvgal/sign-file`. Both kernel-tree and DKMS modules are signed (v0.7.5+). The files are `mvgal-signing.priv`, `mvgal-signing.x509`, and the DER form `mvgal-signing.der`. The certificate subject is `CN=MVGAL Kernel Module Signing Key, O=MVGAL`.
2. **Enrollment** — the per-machine key must be enrolled into the machine's MOK list so the kernel trusts it. This is a one-time, interactive step (requires a reboot into the MOK manager).
3. **Verification** — `mvgal-enroll-mok` verifies the pending MOK list with `mokutil --list-new` before reporting success (v0.7.8+, corrected in v0.7.14 — see below).

---

## Enrolling the MVGAL Key (Recommended)

After installing MVGAL, run:

```bash
mvgal-enroll-mok
```

What happens:

- If no password is supplied, a **one-time password** is generated and shown.
- The password is piped to `mokutil --import` **via stdin, twice** — mokutil 0.7.2 prompts for the one-time password *and* a confirmation, and feeding it a single line ends in `could not read confirmation password`.
- The pending MOK list is verified with `mokutil --list-new`, matching the certificate's real common name.
- **Reboot** — the MOK Manager (blue screen) appears during boot; select **Enroll MOK → Continue → Yes** and enter the one-time password.

> **Note:** `mvgal-enroll-mok` works through `pkexec` without a TTY. If you prefer to supply the password yourself, use `mvgal-enroll-mok -p 'your-password'`. That `-p` belongs to `mvgal-enroll-mok`, not to `mokutil` — mokutil's own `-p`/`--password` is not usable (see [Troubleshooting](#troubleshooting)).

### Manual enrollment (alternative)

If the keypair already exists at `/var/lib/mvgal/keys/`, you can import the certificate directly:

```bash
# Import the certificate (DER form; mvgal-signing.x509 also works)
pkexec mokutil --import /var/lib/mvgal/keys/mvgal-signing.der
```

`mokutil` then prompts twice for the one-time password on its terminal. Do **not** pass
`--password`: mokutil 0.7.2 prints its usage and **exits 0** on that flag, reporting
success without importing anything.

If the keypair does not exist yet, generate it first:

```bash
pkexec mkdir -p /var/lib/mvgal/keys && pkexec chmod 700 /var/lib/mvgal/keys
pkexec openssl req -new -x509 -newkey rsa:4096 -nodes -days 3650 \
    -subj '/CN=MVGAL Kernel Module Signing Key/O=MVGAL' \
    -keyout /var/lib/mvgal/keys/mvgal-signing.priv \
    -out /var/lib/mvgal/keys/mvgal-signing.x509
```

Then reboot and complete enrollment in the MOK Manager.

---

## Verifying Enrollment

Ask whether **this machine's certificate** is enrolled — not whether some MVGAL
certificate is:

```bash
mokutil --test-key /var/lib/mvgal/keys/mvgal-signing.der
```

`--test-key` exits 0 only if that exact certificate is in the platform keyring.

> **Do not verify by grepping the enrolled list.** `mokutil --list-enrolled |
> grep MVGAL` looks like it works and does not: every MVGAL keypair shares the
> subject `CN=MVGAL Kernel Module Signing Key, O=MVGAL`, so after the key is
> regenerated — a reinstall that lost `/var/lib/mvgal/keys`, a restore from
> backup, a deliberate rotation — the **old** certificate is still listed, the
> grep succeeds, and every module signed by the **new** key is still rejected.
> This was a live bug: `mvgald` performed exactly that check and stayed silent.
> Fixed in v0.7.22, which uses `mokutil --test-key`.

If the module still fails to load, check:

```bash
journalctl -k -b | grep -i "module verification\|mvgal"
```

## Modules compressed in a format the kernel cannot read (fixed in v0.7.25)

This is the reason a Secure Boot install could not be made to work at all on
v0.7.21 and v0.7.22, **even after enrolling the MOK correctly**.

The modules were compressed with `xz -9e`, which produces a **CRC64**-checked
xz stream. The kernel's xz decoder rejects any check type above CRC32:

```c
/* lib/xz/xz_dec_stream.c */
if (s->check_type > XZ_CHECK_CRC32)
        return XZ_OPTIONS_ERROR;
```

The kernel's decoder only carries an internal CRC32 implementation
(`lib/xz/xz_crc32.c`) and no CRC64 at all, so a CRC64 stream is rejected as
"encoded with settings that are not supported by this XZ decoder". The
kernel reports that as `EINVAL`:

```
insmod: ERROR: could not insert module ...: Invalid parameters
dmesg:  decompression failed with status 6
```

The critical detail is **where** it fails. Decompression happens *before*
the Secure Boot signature is examined, so a module that fails this way
never reaches the signature check. Enrolling the MOK cannot fix it, and
the journal mentions a signature problem only because the signature check
is the next thing that would have happened.

> **CRC64 is xz's default check type at *every* compression level.** Plain
> `xz -9` is just as broken as `xz -9e`. The "extreme" preset is not what
> causes it.

v0.7.25 uses the kernel's own settings, copied verbatim from
`scripts/Makefile.modinst`:

```
cmd_xz = $(XZ) --check=crc32 --lzma2=dict=1MiB -f $<
```

Two consequences worth knowing:

- the signed module is **byte-identical** to what DKMS builds for the same
  `.ko`, so the two no longer disagree;
- because the output matches the kernel's own compression, the file is
  accepted by the kernel's module decompressor by construction.

Check what you have on disk:

```bash
xz --list --verbose /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/mvgal/mvgal.ko.xz | grep Check
```

`Check: CRC32` is correct. `Check: CRC64` means the module cannot be
decompressed, whatever the MOK says.

Repair it:

```bash
pkexec /usr/lib/mvgal/mvgal-sign-modules.sh
```

`mvgal-enroll-mok` also re-signs the installed modules before it queues
the certificate, so from v0.7.25 the enrollment itself completes the fix
instead of only half of it.

> The "already signed" check compares the **decompressed** image, so a
> module signed by v0.7.21/v0.7.22 looked correct and was left in place
> with its CRC64 container intact — the upgrade would have silently
> repaired nothing. v0.7.25 checks the container first.

## Modules signed with the wrong key (fixed in v0.7.22)

If `mvgal_ntsync` is rejected but the other modules are not, compare the keys
that actually signed them:

```bash
for ko in $(find /lib/modules/$(uname -r) -name 'mvgal*.ko*'); do
  echo "$ko"; modinfo -F signer "$ko" 2>/dev/null || echo "  (unsigned)"
done
```

Every module must show `MVGAL Kernel Module Signing Key`. Anything showing
`DKMS module signing key` is the v0.7.21 defect: `mvgal_ntsync.ko` — a hard
dependency of `mvgal.ko` — was signed with DKMS's own key while
`mvgal-enroll-mok` enrolled only the MVGAL one, so the documented remediation
(enroll, reboot, confirm) could never succeed.

Re-sign every installed module:

```bash
pkexec /usr/lib/mvgal/mvgal-sign-modules.sh
```

The helper searches all the places a module can end up (the kernel tree,
`updates/dkms`, `extra`, `weak-updates`, `updates`), handles `.ko`, `.ko.xz`
and `.ko.zst` by decompressing, signing and recompressing, and is idempotent —
it leaves already-correct modules byte-identical. It also runs automatically
from the RPM `%post`, from `mvgal-dkms` `%post`, and from `dkms.conf` after
each DKMS rebuild.

> A compressed module cannot be signed in place: the signature covers the ELF
> image and the kernel verifies it after decompression. That is why the modules
> DKMS installs on a compression-enabled distro are `mvgal_ntsync.ko.xz` and
> have to be signed *before* compression.

---

## Degraded Mode (Module Not Loaded)

If the `mvgal` kernel module is **not loaded** (e.g. MOK not yet enrolled, or Secure Boot rejected the module), MVGAL runs in **degraded userspace-only mode**:

- `mvgal-status` prints:

  ```
  Kernel Module: NOT LOADED (degraded userspace-only mode)
  ```

  with a MOK enrollment hint, and exits `1` (v0.7.6+, upgraded to the three-tier scheme in v0.7.29).
- The load-balance figure is a real estimate, or `N/A` when fewer than 2 enabled GPUs / no workload data (v0.7.8+).
- `mvgal-hw-validate` attributes device-node failures to "kernel module not loaded" with a load hint (v0.7.8+).

**How you learn about it changed in v0.7.21.** Degraded mode was previously
discoverable only by running a diagnostic tool, or by reading the journal after
wondering why aggregation does nothing. The daemon now checks at startup whether
Secure Boot is enabled *and* the MVGAL key is absent from the enrolled list, and
prints a boxed banner to the journal naming the remedy and the certificate path:

```
journalctl -u mvgald -b | grep -A6 'Secure Boot is enabled'
```

The RPM `%post` prints the same guidance at install time. Treat that banner as
the reason aggregation and kernel-side memory management are unavailable — the
userspace discovery you see in `mvgal list-gpus` still works, which is exactly
why degraded mode is easy to mistake for a working install.

Because this state looks healthy from several angles, the tools now agree on it
via a three-tier exit code (v0.7.29): `mvgal status` exits `0` when healthy
(daemon up, module loaded), `1` when degraded (daemon up, module absent), and
`2` when the daemon is not running at all. This matches `mvgal-status --once`,
which uses the same codes. Earlier versions disagreed — `mvgal status`
returned 0 for the same condition where `mvgal-status` returned 1.

To load the module manually:

```bash
pkexec mvgal-load
```

> Use `mvgal-load`, not `modprobe mvgal`. `mvgal.ko` declares `mvgal_ntsync.ko`
> as a hard dependency, so `modprobe` reports only the outermost failure and
> tells you nothing about which module was actually rejected. `mvgal-load` loads
> the inventory in order, names the module that failed, and prints the
> enrollment instructions itself when Secure Boot is the cause.

> **Note:** the loader is `/usr/bin/mvgal-load` and its counterpart `/usr/bin/mvgal-unload`. Both source `/usr/lib/mvgal/modules.sh` for the module list.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `mvgal-enroll-mok` reports success but module still rejected | Complete enrollment in MOK Manager, verify with `mokutil --list-enrolled`, then check module build and kernel logs. |
| `mokutil --import` fails with `could not read confirmation password` | mokutil prompts twice and the password was supplied once. Fixed in v0.7.14 — upgrade, or pipe the password twice by hand. |
| `mokutil --import --password ...` appears to succeed but enrols nothing | mokutil 0.7.2 prints usage and exits 0 on that flag. Use the packaged `mvgal-enroll-mok` helper (password via stdin) or omit the flag. |
| `mvgal-enroll-mok` says the key is not in the pending list | The key really did not import. Read the keys it prints — that is the actual `mokutil --list-new` output, not a guess. |
| MOK Manager doesn't appear on reboot | Secure Boot may be disabled, or the key was already enrolled. Check `mokutil --list-enrolled`. |
| `modprobe mvgal` → "Required key not available" | The key is not enrolled. Run `mvgal-enroll-mok` and reboot. |
| `mvgald` is `active (running)` but no module is loaded | The unit's `ExecStartPre` `modprobe` failed. Pre-v0.7.14 this was silent. Check `journalctl -u mvgald -b` for the reported reason. |
| `mvgal load-module` seems to hang | Pre-v0.7.21 it waited on the polkit dialog with no bound, so a cancelled or ignored prompt left it blocked with no output. v0.7.21+ gives up after 60 s and says so. |
| `mvgal_ntsync` rejected while other modules load | **v0.7.21 and earlier.** ntsync was signed with DKMS's key; the older "update to v0.7.5+" advice did not fix it. Upgrade to v0.7.22+, or re-sign with `pkexec /usr/lib/mvgal/mvgal-sign-modules.sh`, then enroll as described above. |
| Modules still rejected after enrolling | Check for a stale key: `mokutil --test-key /var/lib/mvgal/keys/mvgal-signing.der`. If it fails, an older MVGAL certificate is enrolled instead — enroll the current one (`pkexec mvgal-enroll-mok && reboot`). |
| Everything rejected right after a kernel update | Pre-v0.7.22: DKMS rebuilt the modules with its own key and no RPM scriptlet ran. v0.7.22+ sets a `POST_INSTALL` hook in `dkms.conf` to re-sign. Workaround on older versions: `pkexec /usr/lib/mvgal/mvgal-sign-modules.sh`. |

---

## Security Notes (v0.7.8, capabilities corrected in v0.7.14)

- The daemon **drops capabilities after init** — effective/permitted/inheritable sets are cleared and the bounding set is pruned to `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO CAP_SYS_MODULE`.
- The systemd unit sets `CapabilityBoundingSet` / `AmbientCapabilities` to `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO CAP_SYS_MODULE` and `NoNewPrivileges=yes`.
- `CAP_SYS_MODULE` is **required**: the unit's `ExecStartPre` runs `modprobe`, which cannot succeed without it. Its absence was the reason the unit could never load a module (see below).
- The D-Bus policy for `org.mvgal.MVGAL` is restricted to **root** and the **`mvgal` group** — other users are denied. The policy file is `/etc/dbus-1/system.d/org.mvgal.MVGAL.conf`.
- polkit actions are exactly two, both requiring `auth_admin`: `com.mvgal.privileged.helper` (bound to `/usr/lib/mvgal/mvgal-pkexec-helper.sh`) and `com.mvgal.daemon.start` (bound to `/usr/sbin/mvgald`). The v0.7.14 rewrite removed ten action IDs that no executable was annotated with, two of which granted `allow_any=yes` — no authentication at all.

---

## What v0.7.14 Fixed Here

The v0.7.14 release exists because of a field report from a Fedora 44 machine with an Intel UHD 770 and Secure Boot enabled. On that machine the module could not load, and every diagnostic pointed somewhere unhelpful. Four separate defects were involved:

| Defect | Symptom | Fix |
|---|---|---|
| `mokutil --import` prompts for the password **twice** | Every enrollment ended in `could not read confirmation password` | The password is now written twice |
| Verification grepped for `mvgal-signing` | mokutil prints `CN=MVGAL Kernel Module Signing Key, O=MVGAL` and never the filename, so a *successful* import was reported as a failure | The check matches the real common name |
| `mvgal-enroll-mok -p PASS` parsed options *before* re-executing via `pkexec "$0" "$@"` | The parse loop had already emptied `"@"`, so the password arrived as nothing | Elevates first, with a non-consuming pre-scan so `--help` still works unprivileged; a password containing a space now survives |
| Secure Boot state matched with nested `case` globs | `disabled` and `not enabled` were not both recognised | The state is lower-cased once and matched against explicit patterns; an unreadable state warns instead of silently proceeding |
| `CAP_SYS_MODULE` missing from the unit, and `-` on each `ExecStartPre` | `modprobe` was guaranteed `EPERM`; the `-` discarded both status and message, so the unit reported `active (running)` with no kernel module | Capability granted, status no longer discarded, and the message names the real fix (`pkexec mvgal-enroll-mok`) |

The net effect: a Secure Boot machine was told to reboot, rebooted, and still had no trusted key — while every message said enrollment had succeeded.

The unit now also declares `RuntimeDirectory=mvgal` with `RuntimeDirectoryPreserve=yes`, because `/run` is tmpfs and the socket's parent directory did not otherwise survive a reboot.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more issues and [STATUS.md](STATUS.md) for the release history.
