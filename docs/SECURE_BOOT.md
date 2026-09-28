---
tags: [mvgal, secure-boot, mok, kernel, guide]
aliases: [Secure Boot, MOK, MOK Enrollment]
mvgal_version: "0.7.14"
mvgal_verified: 2026-09-28
mvgal_role: guide
mvgal_order: 3
---

# MVGAL Secure Boot & MOK Enrollment

> **Implementation status:** Source metadata is 0.7.14. The source changelog documents through 0.7.14. Treat design/API descriptions as available only where the relevant code path and runtime capability are verified; unsupported kernel submission and VRAM allocation return `-EOPNOTSUPP`.

**Source version:** 0.7.14 | **Updated:** September 2026

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

```bash
mokutil --list-enrolled | grep 'CN=MVGAL Kernel Module Signing Key'   # enrolled keys
mokutil --list-new | grep 'CN=MVGAL Kernel Module Signing Key'        # pending keys (empty after reboot)
```

> **Note:** grep for the certificate's **common name**, not the bare word `mvgal`. mokutil prints `Issuer/Subject: CN=MVGAL Kernel Module Signing Key, O=MVGAL`; the filename `mvgal-signing` never appears in its output.

If the module still fails to load, check:

```bash
journalctl -k -b | grep -i "module verification\|mvgal"
```

---

## Degraded Mode (Module Not Loaded)

If the `mvgal` kernel module is **not loaded** (e.g. MOK not yet enrolled, or Secure Boot rejected the module), MVGAL runs in **degraded userspace-only mode**:

- `mvgal-status` prints:

  ```
  Kernel Module: NOT LOADED (degraded userspace-only mode)
  ```

  with a MOK enrollment hint, and exits non-zero (v0.7.6+).
- The load-balance figure is a real estimate, or `N/A` when fewer than 2 enabled GPUs / no workload data (v0.7.8+).
- `mvgal-hw-validate` attributes device-node failures to "kernel module not loaded" with a load hint (v0.7.8+).

To load the module manually:

```bash
pkexec modprobe mvgal
# or, if the package is installed -- the shared inventory handles order:
pkexec mvgal-load
```

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
| DKMS modules rejected but kernel-tree modules load | Pre-v0.7.5 behavior. Update to v0.7.5+ so DKMS modules are signed too. |

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
