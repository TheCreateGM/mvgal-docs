# MVGAL Power Management

> **Version**: 0.5.0  
> **Last Updated**: 2026-06-06

---

## Table of Contents

1. [Overview](#overview)
2. [Power Curve System](#power-curve-system)
3. [Idle State Machine](#idle-state-machine)
4. [DVFS Control](#dvfs-control)
5. [Gamemode Integration](#gamemode-integration)
6. [Thermal Throttling](#thermal-throttling)
7. [`mvgal-powercurve` Tool](#mvgal-powercurve-tool)
8. [Vendor-Specific Power Management](#vendor-specific-power-management)

---

## Overview

MVGAL power management operates at two levels:

1. **Kernel-level** (`kernel/mvgal_power.c`, `kernel/mvgal_power.h`):
   - Per-GPU DVFS control (frequency/voltage scaling)
   - Thermal monitoring and throttling
   - Power budget enforcement

2. **Userspace daemon** (`runtime/daemon/power_manager.cpp`, `.hpp`):
   - Power curve management
   - Idle detection and power gating
   - Fan curve management
   - Metrics collection via NVML/hwmon/fdinfo

The kernel module provides the low-level controls; the daemon implements policy.
Communication flows through the `mvgal_gpu_power` struct and IOCTL interface.

---

## Power Curve System

Power curves map GPU workload intensity to power limits, expressed as a
percentage of Thermal Design Power (TDP).

### Curve Structure

```
Utilization % → Power Limit % of TDP
```

A power curve is a table of (utilization, power_limit, temperature_target)
points. Linear interpolation is used between points.

### Curve Points (Default)

| Utilization | Power Limit | Temp Target | Voltage |
|:-----------:|:-----------:|:-----------:|:-------:|
| 0% | 30% | 40°C | Min |
| 25% | 50% | 55°C | Eco |
| 50% | 75% | 70°C | Balanced |
| 75% | 90% | 80°C | Boost |
| 95% | 100% | 83°C | Max |
| 100% | 105% | 85°C | Turbo (if available) |

### Power Curve Profiles

MVGAL ships with four pre-defined profiles:

| Profile | Max Power | Temp Target | Use Case |
|---------|:---------:|:-----------:|----------|
| `powersave` | 60% TDP | 65°C | Quiet, battery |
| `balanced` | 80% TDP | 75°C | Default |
| `performance` | 100% TDP | 83°C | Gaming |
| `turbo` | 110% TDP | 85°C | Benchmarking |

Toggle profiles with:
```bash
mvgal-powercurve --profile performance
```

### Custom Curves

Users can define custom curves in JSON (`/etc/mvgal/powercurve.json`):
```json
{
  "profile": "custom",
  "points": [
    {"util": 0, "power": 30, "temp": 40},
    {"util": 30, "power": 60, "temp": 60},
    {"util": 70, "power": 85, "temp": 75},
    {"util": 100, "power": 100, "temp": 82}
  ],
  "fan_curve": "quiet"
}
```

---

## Idle State Machine

GPUs transition through four power states, defined in
`runtime/daemon/power_manager.hpp`:

```
          ┌──────────────────────────────────────────────┐
          │                                              │
          ▼                                              │
   ┌──────────┐    timeout    ┌───────────┐              │
   │  ACTIVE  │ ────────────→ │SUSTAINED  │              │
   │  (D0)    │               │  (D0-low)  │              │
   └──────────┘               └───────────┘              │
        ↑                           │                    │
        │                     timeout│                    │
        │                           ▼                    │
        │                    ┌───────────┐    timeout    │
        │                    │   IDLE    │ ─────────────  │
        │                    │  (D3hot)  │                │
        │                    └───────────┘                │
        │                           │                    │
        │                     timeout│                    │
        │                           ▼                    │
        │                    ┌───────────┐               │
        └────────────────────│   PARK    │               │
        activity wakes        │  (D3cold) │               │
                             └───────────┘
```

### State Descriptions

| State | Power | Wake Latency | Driver State |
|-------|:-----:|:------------:|-------------|
| `ACTIVE` (D0) | 100% TDP | — | Fully operational |
| `SUSTAINED` (D0-low) | 60–80% TDP | < 1 ms | Clocks reduced |
| `IDLE` (D3hot) | 10–30% TDP | 10–100 ms | VRAM self-refresh |
| `PARK` (D3cold) | ~0% TDP | 100–500 ms | VRAM off, context saved |

### Transition Timers

| Transition | Default Timer | Configurable |
|------------|:------------:|:------------:|
| ACTIVE → SUSTAINED | 5 s idle | Yes (`idle_sustained_ms`) |
| SUSTAINED → IDLE | 30 s idle | Yes (`idle_park_ms`) |
| IDLE → PARK | 120 s idle | Yes (`park_delay_ms`) |
| Any → ACTIVE | Instant (on activity) | — |

---

## DVFS Control

Dynamic Voltage and Frequency Scaling is managed through
`kernel/mvgal_power.h` with support for four DVFS modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `PERFORMANCE` | Max clock always | Gaming, ML |
| `BALANCED` | Scale on demand | Default |
| `POWERSAVE` | Min clock preferred | Battery, idle |
| `CUSTOM` | User-defined curve | Advanced tuning |

### Policy Parameters

Each DVFS policy includes:

| Parameter | Description | Default |
|-----------|-------------|:-------:|
| `min_freq_mhz` | Minimum GPU clock | 300 MHz |
| `max_freq_mhz` | Maximum GPU clock | Vendor max |
| `up_threshold` | Util% to scale up | 80% |
| `down_threshold` | Util% to scale down | 30% |
| `step_delay_ms` | Min interval between changes | 50 ms |

### Querying DVFS State

```bash
# Current DVFS mode and frequencies
mvgal-info --dvfs

# Per-GPU power state
mvgal-info --power
```

---

## Gamemode Integration

MVGAL integrates with Feral Interactive's `gamemode` daemon.

### When Gamemode Is Active

1. Power profile switches to `performance` (or `turbo` if configured).
2. DVFS mode set to `PERFORMANCE`.
3. Idle-state entry timers increased (reduces wake-from-idle latency).
4. CPU governor hint set to `performance`.
5. Fan curve set to `active` (higher fan speeds, lower temps).

### Enabling Gamemode

```bash
# Install gamemode
dnf install gamemode

# Enable gamemode daemon
systemctl enable --now gamemoded

# Run a game with gamemode
gamemoderun ./mygame

# Or configure Steam to auto-launch gamemode:
# Settings → Compatibility → Enable gamemode
```

### Configuration

MVGAL-specific gamemode config at `/etc/mvgal/gamemode.conf`:

```ini
[mvgal]
profile=performance
dvfs_mode=PERFORMANCE
idle_sustained_ms=30000
idle_park_ms=60000
fan_curve=active
```

---

## Thermal Throttling

Thermal management is implemented in `kernel/mvgal_power.c` with a five-tier
state machine defined in `runtime/daemon/power_manager.hpp`.

### Thermal States

| State | Temp Range | Action |
|-------|:----------:|--------|
| `NORMAL` | < 75°C | No action |
| `WARN` | 75–85°C | Increase fan speed, log warning |
| `HOT` | 85–92°C | Reduce max clock by 10% |
| `THROTTLING` | 92–100°C | Aggressive clock reduction, power cap |
| `CRITICAL` | > 100°C | Emergency shutdown (kernel-level) |

### Throttle Levels

When in `THROTTLING` state, the kernel applies throttle levels:

| Level | Clock Reduction | Power Cap | Duration |
|:-----:|:---------------:|:---------:|:--------:|
| 1 | 10% | 90% TDP | Until temp < 90°C |
| 2 | 25% | 75% TDP | Until temp < 85°C |
| 3 | 50% | 50% TDP | Until temp < 80°C |

### Temperature Monitoring

```bash
# Current temperatures
mvgal-info --temperature

# Thermal history
mvgal-info --temperature --history
```

---

## `mvgal-powercurve` Tool

The `mvgal-powercurve` CLI manages power profiles. Available in `tools/`.

### Commands

| Command | Description |
|---------|-------------|
| `mvgal-powercurve --list` | List available profiles |
| `mvgal-powercurve --profile <name>` | Set active profile |
| `mvgal-powercurve --status` | Show current power state |
| `mvgal-powercurve --fan <speed>` | Manual fan override (0–100) |
| `mvgal-powercurve --benchmark` | Run power benchmark |
| `mvgal-powercurve --curve <file>` | Load custom curve from JSON |

### Example Usage

```bash
# Check current state
mvgal-powercurve --status

# Set performance mode
mvgal-powercurve --profile performance

# Load custom curve
mvgal-powercurve --curve ~/my-curve.json

# Run fan at 60%
mvgal-powercurve --fan 60
```

---

## Vendor-Specific Power Management

### NVIDIA

- **NVML interface**: `runtime/daemon/nvml_loader.cpp` loads NVML dynamically.
- Exposed metrics: power draw, temperature, fan speed, clock frequencies.
- Supports `nvidia-smi`-style power limiting.
- Dynamic boost on RTX 30xx+.

### AMD

- **hwmon interface**: Reads via `/sys/class/drm/card*/device/hwmon/hwmon*/`.
- Exposed metrics: power draw (via `amdgpu` hwmon), temperature, fan speed.
- `amdgpu` firmware-based DVFS (no direct clock control from kernel module).

### Intel

- **hwmon interface**: Via `/sys/class/drm/card*/device/hwmon/hwmon*/`.
- Exposed metrics: power draw, temperature (DG2+).
- Integrated GPUs share system thermal zone.

### Moore Threads

- **Vendor API**: Proprietary MTGX power interface.
- Exposed metrics: power draw, temperature (basic).
- DVFS support in beta status.

---

*See `docs/ARCHITECTURE.md` §3—Runtime Daemon for daemon architecture.  
See `runtime/daemon/power_manager.cpp` for implementation.  
See `kernel/mvgal_power.c` for kernel-level DVFS.*
