# MVGAL Troubleshooting Guide

> **Version**: 0.5.0  
> **Last Updated**: 2026-06-06

---

## Table of Contents

1. [Diagnostic Commands](#diagnostic-commands)
2. [Installation Issues](#installation-issues)
3. [GPU Not Detected](#gpu-not-detected)
4. [Kernel Module Issues](#kernel-module-issues)
5. [Performance Issues](#performance-issues)
6. [Steam / Proton Integration](#steam--proton-integration)
7. [Daemon & Runtime Issues](#daemon--runtime-issues)
8. [Multi-GPU Issues](#multi-gpu-issues)
9. [Collecting Logs & Reporting Bugs](#collecting-logs--reporting-bugs)

---

## Diagnostic Commands

MVGAL provides several diagnostic tools. Run these first when troubleshooting:

```bash
# System-wide health check
mvgal-info --all

# Daemon status
mvgald --status

# Connected GPUs
mvgal-info --devices

# Scheduler status
mvgal-sched status

# Power state
mvgal-powercurve --status

# Configuration
mvgal-config --dump

# Full system report (for bug reports)
mvgal-info --report > mvgal-report.txt
```

---

## Installation Issues

### Package Not Found

**Problem**: `dnf install mvgal` fails with "package not found".

**Solutions**:
1. Enable the COPR repository:
   ```bash
   dnf copr enable mvgal/mvgal
   dnf install mvgal
   ```
2. Verify your Fedora version (`mvgal` requires Fedora 40+):
   ```bash
   cat /etc/fedora-release
   ```
3. For other distributions, build from source (see `docs/KERNEL_MODULE.md`).

### Dependency Conflicts

**Problem**: `dpkg` / `rpm` reports conflicting dependencies.

**Solutions**:
1. Ensure your kernel headers are installed:
   ```bash
   # Fedora/RHEL
   dnf install kernel-devel kernel-headers
   ```
2. Verify Vulkan SDK ≥ 1.3 is installed:
   ```bash
   vulkaninfo --summary
   ```
3. For Rust components, ensure `rustc` ≥ 1.70:
   ```bash
   rustc --version
   ```

### Build Fails from Source

**Problem**: `cmake --build build` fails.

**Solutions**:
1. Check CMake output for missing dependencies.
2. Ensure you have the full build chain:
   ```bash
   # Fedora/RHEL
   dnf builddep mvgal
   ```
3. For kernel module, verify DKMS:
   ```bash
   dkms status
   ```

---

## GPU Not Detected

### No GPUs Listed

**Problem**: `mvgal-info --devices` returns empty.

**Checks**:
1. Verify GPUs are visible to Linux:
   ```bash
   lspci | grep -E "VGA|3D|Display"
   ```
2. Check the daemon is running:
   ```bash
   systemctl status mvgald
   ```
3. Check dmesg for MVGAL messages:
   ```bash
   dmesg | grep -i mvgal
   ```
4. Verify the NVIDIA/AMD driver is loaded:
   ```bash
   lsmod | grep -E "nvidia|amdgpu|i915"
   ```

### Vendor-Specific GPU Not Showing

**NVIDIA**:
- Ensure `nvidia-drm` is loaded with `modeset=1`:
  ```bash
  cat /sys/module/nvidia_drm/parameters/modeset
  # should output: Y
  ```
- Check NVML is accessible:
  ```bash
  nvidia-smi
  ```

**AMD**:
- Ensure `amdgpu` supports your GPU:
  ```bash
  dmesg | grep amdgpu | head -20
  ```
- Check for P2P support (needed for multi-GPU):
  ```bash
  cat /sys/kernel/debug/dri/*/p2p_support
  ```

**Intel**:
- Ensure `i915` is loaded:
  ```bash
  lsmod | grep i915
  ```
- For discrete Arc GPUs, verify firmware:
  ```bash
  ls /lib/firmware/i915/
  ```

**Moore Threads**:
- Ensure `mtgpu` driver is installed (vendor-provided).
- Beta status: some P2P features may not work.

---

## Kernel Module Issues

### Module Fails to Load

**Problem**: `modprobe mvgal` fails.

**Diagnostic**:
```bash
# Check kernel version compatibility
uname -r

# Check module file
modinfo mvgal

# Try loading with verbose output
insmod /lib/modules/$(uname -r)/extra/mvgal/mvgal.ko 2>&1

# Check dmesg
dmesg | tail -50 | grep -i mvgal
```

**Solutions**:
1. Kernel too old: MVGAL requires 5.15 LTS minimum.
2. Missing symbols: Rebuild against current kernel headers.
3. Secure Boot: The packaged modules are signed with a per-install key.
   Enroll it with the firmware MOK database (do NOT disable Secure Boot):
   ```bash
   sudo mvgal-enroll-mok
   sudo reboot
   # At the blue MOK Manager screen after reboot, choose
   # 'Enroll key from disk' -> /usr/lib/mvgal/keys/mvgal-signing.der
   # and confirm with the one-time password you chose.
   ```
   After enrollment, `modprobe mvgal` works and `Key was rejected by
   service` no longer appears.  DKMS-rebuilt modules are signed with the
   same key automatically.
4. SELinux: Check for AVC denials:
   ```bash
   ausearch -m avc -ts recent | grep mvgal
   ```

### DKMS Build Fails

**Problem**: `dkms build mvgal` fails.

**Solutions**:
1. Ensure kernel-devel matches running kernel:
   ```bash
   dnf list installed kernel-devel
   uname -r
   ```
2. Check DKMS logs:
   ```bash
   cat /var/lib/dkms/mvgal/*/build/make.log
   ```

### IOCTL Returns -ENOTTY

**Problem**: Application reports "Invalid argument" on IOCTL.

**Checks**:
1. Verify device node exists:
   ```bash
   ls -l /dev/mvgal*
   ```
2. Check device permissions (should be `crw-rw----`):
   ```bash
   getfacl /dev/mvgal0
   ```
3. Ensure udev rules are installed:
   ```bash
   cat /etc/udev/rules.d/99-mvgal.rules
   ```

---

## Performance Issues

### Below Expected FPS

**Diagnostic**:
```bash
# Check GPU utilisation
mvgal-info --utilization

# Check scheduler
mvgal-sched status
mvgal-sched analyze

# Check power state (may be throttling)
mvgal-powercurve --status

# Check VRAM usage
mvgal-info --memory
```

**Solutions**:
1. **VRAM pressure**: Reduce texture quality or resolution.
2. **Thermal throttling**: Check GPU temperatures:
   ```bash
   mvgal-info --temperature
   ```
3. **Scheduler mismatch**: Try a different strategy:
   ```bash
   mvgal-sched setpolicy <appname> rld
   ```
4. **Power state**: Ensure gamemode is active:
   ```bash
   gamemoded -s
   ```

### Stuttering / Frame Pacing

**Diagnostic**:
```bash
# Check frame time variance
mvgal-info --frametimes

# Check for compositor interference
mvgal-info --compositor
```

**Solutions**:
1. Disable compositor for full-screen apps.
2. Use `AFF` scheduler strategy to pin the app to one GPU:
   ```bash
   mvgal-sched setpolicy <appname> aff
   ```
3. Check NTSYNC is working (for Windows games):
   ```bash
   cat /proc/sys/kernel/ntsync
   ```

---

## Steam / Proton Integration

### Steam Games Not Detected

**Problem**: Games launch but MVGAL is not intercepting.

**Solutions**:
1. Verify the Steam runtime hook is active:
   ```bash
   ls ~/.steam/steam/steamapps/common/MVGAL/
   ```
2. Set Proton environment variables:
   ```bash
   # In Steam launch options for the game:
   MVGAL_ENABLE=1 PROTON_ENABLE_NVAPI=1 %command%
   ```
3. Check the frame pacer is running:
   ```bash
   ps aux | grep mvgal-pacer
   ```

### Proton FPS Lower Than Native

**Problem**: Proton games underperform native Linux games.

**Diagnostic**:
```bash
# Check which WCL shims are loaded
mvgal-info --wcl

# Check DXVK/VKD3D-Proton integration
mvgal-info --vulkan-layers
```

**Solutions**:
1. Ensure VKD3D-Proton is up to date.
2. Enable NVAPI translation for NVIDIA GPUs:
   ```bash
   PROTON_ENABLE_NVAPI=1
   ```
3. Try different scheduler strategies — some games benefit from `PRI`.

---

## Daemon & Runtime Issues

### Daemon Won't Start

**Problem**: `systemctl start mvgald` fails.

**Diagnostic**:
```bash
# Check daemon status
systemctl status mvgald

# Check journal
journalctl -u mvgald -n 50

# Try running manually as root
sudo mvgald --foreground
```

**Solutions**:
1. D-Bus service not installed:
   ```bash
   sudo cp runtime/daemon/org.mvgal.daemon.conf /etc/dbus-1/system.d/
   ```
2. Socket conflict: Check port 8080 (REST API) is free:
   ```bash
   ss -tlnp | grep 8080
   ```
3. Permission denied on `/dev/mvgal*`:
   ```bash
   sudo chmod 666 /dev/mvgal0
   ```

### IPC Connection Failure

**Problem**: Tools can't connect to daemon.

**Diagnostic**:
```bash
# Test D-Bus
dbus-send --system --dest=org.mvgal.daemon --print-reply /org/mvgal/daemon org.freedesktop.DBus.Ping

# Check Unix socket
ls -l /run/mvgald.sock
```

---

## Multi-GPU Issues

### Only One GPU Used

**Problem**: All work lands on a single GPU.

**Solutions**:
1. Check scheduler strategy — default is `PRI` which prefers fastest:
   ```bash
   mvgal-sched getpolicy <appname>
   ```
2. Force load balancing:
   ```bash
   mvgal-sched setpolicy <appname> rr
   ```
3. Verify P2P connectivity between GPUs:
   ```bash
   mvgal-info --topology
   ```

### P2P Transfer Slow

**Problem**: Inter-GPU transfers bottleneck performance.

**Checks**:
```bash
# Check topology
mvgal-info --topology

# Measure bandwidth
mvgal-info --benchmark-p2p
```

**Solutions**:
1. Use NVLink/XGMI devices when available.
2. For PCIe-connected GPUs, ensure PCIe Gen4+.
3. The `GA` strategy prefers NVLink peers.
4. Consider `PPL` for pipeline workloads — reduces cross-GPU transfers.

---

## Collecting Logs & Reporting Bugs

### Gather System Info

```bash
# Comprehensive report
mvgal-info --report > mvgal-report.txt

# Daemon logs
journalctl -u mvgald > mvgald.log

# Kernel messages
dmesg | grep -i mvgal > mvgal-kernel.log

# Configuration
mvgal-config --dump > mvgal-config.txt
```

### Debug Mode

Enable debug logging for more detail:

```bash
# Daemon
sudo mvgald --foreground --log-level=debug

# Per-app
MVGAL_LOG_LEVEL=debug ./myapp
```

### Report a Bug

Report issues at: https://github.com/your-org/mvgal/issues

Include:
- `mvgal-info --report` output
- `dmesg | grep -i mvgal`
- `mvgald.log`
- Steps to reproduce
- GPU model and driver version

---

*See `docs/ARCHITECTURE.md` for system architecture.  
See `docs/KERNEL_MODULE.md` for module build/install.  
See `docs/HARDWARE_COMPATIBILITY.md` for supported hardware.*
