---
tags: [mvgal, secure-boot, mok, kernel, guide]
aliases: [Secure Boot, MOK, MOK Enrollment]
---

# MVGAL Secure Boot & MOK Enrollment

**Version:** 0.7.8 | **Updated:** September 2026

MVGAL ships kernel modules (`mvgal.ko`, `mvgal_amd.ko`, `mvgal_nvidia.ko`, `mvgal_intel.ko`, `mvgal_mtt.ko`, `mvgal_adreno.ko`, `mvgal_ntsync.ko`). On systems with **UEFI Secure Boot** enabled, the kernel refuses to load modules that are not signed by a trusted key. MVGAL solves this with **per-machine key signing** and **MOK (Machine Owner Key) enrollment**.

---

## How It Works

1. **Install time** — the RPM `%post` script generates a per-machine MVGAL signing key and signs the DKMS-installed modules in `/lib/modules/*/updates/dkms` (v0.7.5+). Kernel-tree modules are signed as well.
2. **Enrollment** — the per-machine key must be enrolled into the machine's MOK list so the kernel trusts it. This is a one-time, interactive step (requires a reboot into the MOK manager).
3. **Verification** — `mvgal-enroll-mok` verifies the pending MOK list with `mokutil --list-new` before reporting success (v0.7.8+ — no more false positives).

---

## Enrolling the MVGAL Key (Recommended)

After installing MVGAL, run:

```bash
mvgal-enroll-mok
```

What happens:

- If no password is supplied, a **one-time password** is generated and shown.
- The password is fed to `mokutil --import` **via stdin** (the `-p` flag is rejected by mokutil 0.7.2).
- The pending MOK list is verified with `mokutil --list-new`.
- **Reboot** — the MOK Manager (blue screen) appears during boot; select **Enroll MOK → Continue → Yes** and enter the one-time password.

> **Note:** `mvgal-enroll-mok` works through `pkexec` without a TTY. If you prefer to supply the password yourself, use `mvgal-enroll-mok -p 'your-password'`.

### Manual enrollment (alternative)

```bash
# Generate a key (if not already present)
sudo mokutil --import /etc/pki/mvgal/MVGal-MOK.der
# Or with a password
sudo mokutil --import /etc/pki/mvgal/MVGal-MOK.der --password 'your-password'
```

Then reboot and complete enrollment in the MOK Manager.

---

## Verifying Enrollment

```bash
mokutil --list-enrolled | grep -i mvgal   # enrolled keys
mokutil --list-new | grep -i mvgal        # pending keys (should be empty after reboot)
```

If the module still fails to load, check:

```bash
sudo dmesg | grep -i "module verification\|mvgal"
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
sudo modprobe mvgal
# or
mvgal-load        # self-escalates via pkexec
```

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `mvgal-enroll-mok` reports success but module still rejected | Pre-v0.7.8 false positive. Update to v0.7.8+, or verify with `mokutil --list-enrolled`. |
| `mokutil --import` fails with `-p` flag | mokutil 0.7.2 rejects `-p`. Use v0.7.8+ `mvgal-enroll-mok` (password via stdin) or omit the flag. |
| MOK Manager doesn't appear on reboot | Secure Boot may be disabled, or the key was already enrolled. Check `mokutil --list-enrolled`. |
| `modprobe mvgal` → "Required key not available" | The key is not enrolled. Run `mvgal-enroll-mok` and reboot. |
| DKMS modules rejected but kernel-tree modules load | Pre-v0.7.5 behavior. Update to v0.7.5+ so DKMS modules are signed too. |

---

## Security Notes (v0.7.8)

- The daemon **drops capabilities after init** — effective/permitted/inheritable sets are cleared and the bounding set is pruned to `CAP_SYS_ADMIN CAP_DAC_OVERRIDE CAP_SYS_RAWIO`.
- The systemd unit adds `CapabilityBoundingSet` / `AmbientCapabilities` / `NoNewPrivileges`.
- The D-Bus policy for `org.mvgal.MVGAL` is restricted to **root** and the **`mvgal` group** — other users are denied.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more issues and [STATUS.md](STATUS.md) for the release history.