# Sidewinder — Adapter Setup Guide

**Your adapters and what needs to be done before Sidewinder works.**

---

## Your Hardware

| Adapter | Chipset | Bus | WiFi Gen | Status | Action Needed |
|---------|---------|-----|----------|--------|---------------|
| `wlo1` (built-in) | MediaTek MT7902 | PCIe | 802.11ax | [OK] Works | None — internet only |
| `wlx001ea6c65744` (USB) | Ralink RT5370 | USB | 802.11n | [OK] Works | None — driver included in kernel |
| `wlx5c628b765de2` (USB) | Realtek RTL8821AU | USB | 802.11ac | [FAIL] **Needs driver** | **Install morrownr driver** |

---

## Why You Need a New Driver for T2U Plus

### The Problem

Your TP-Link Archer T2U Plus uses the **Realtek RTL8821AU** chipset. Ubuntu's default kernel driver (`rtw88`) **does not support monitor mode**.

Without monitor mode, Sidewinder **cannot**:
- Capture WiFi packets
- Detect EAPOL handshakes
- Perform any WiFi auditing

### What Happens When You Plug In T2U Plus (Without morrownr)

```
USB detected → rtw88 kernel driver loads → Interface appears (wlan2)
→ But: iw list shows NO monitor mode support
→ Sidewinder cannot use this adapter for attacks
```

### What Happens After Installing morrownr

```
USB detected → morrownr 8821au driver loads → Interface appears (wlan2)
→ iw list shows FULL monitor mode + injection
→ Sidewinder can use this adapter for all operations
```

### Comparison

| Feature | rtw88 (default) | morrownr (required) |
|---------|:---------------:|:-------------------:|
| Interface works | [OK] | [OK] |
| Managed mode | [OK] | [OK] |
| **Monitor mode** | [FAIL] **No** | [OK] **Yes** |
| **Packet injection** | [FAIL] **No** | [OK] **Yes** |
| **802.11ac VHT** | [WARN] Limited | [OK] **Full** |
| **5GHz support** | [WARN] Partial | [OK] **Full** |
| **Radiotap header** | [FAIL] No | [OK] **Yes** |
| **Signal strength reporting** | [FAIL] No | [OK] **Yes (dBm)** |
| **Power save auto-disable** | [FAIL] No | [OK] **Yes** |
| Works on Ubuntu | [WARN] Partial | [OK] **Yes (DKMS)** |

**Bottom line:** Without morrownr, your T2U Plus is just a regular WiFi card. With morrownr, it becomes a **professional audit tool**.

---

## Driver Sources

### Source Code

```
Repository: https://github.com/morrownr/8821au-20210708
Driver: 8821au (DKMS)
Kernel support: 5.7 - 6.12+
Chipset: RTL8811AU / RTL8821AU
USB VID:PID: 2357:0120 (TP-Link T2U Plus)
License: GPL v2
```

### What's in the Driver

| Component | Description |
|-----------|-------------|
| **Monitor mode** | Full radiotap RX with signal, MCS, VHT, AMPDU fields |
| **Injection** | Radiotap-iterator-based TX with 3-attempt retry logic |
| **5GHz VHT** | MCS 0-9, 80/160 MHz, beamforming |
| **Power save** | Auto-disabled in monitor mode (no manual intervention) |
| **USB IDs** | 50+ devices supported (TP-Link, Netgear, D-Link, etc.) |

---

## Installation Steps

### Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build dependencies
sudo apt install -y build-essential dkms git bc libelf-dev linux-headers-$(uname -r)
```

### Step 1: Clone the Driver

```bash
cd ~
git clone https://github.com/morrownr/8821au-20210708.git
cd 8821au-20210708
```

### Step 2: Install the Driver

```bash
# Option A: Automatic install (recommended)
sudo ./install-driver.sh

# Option B: Manual DKMS install
sudo cp -r 8821au /usr/src/8821au-20210708
sudo dkms add 8821au/20210708
sudo dkms build 8821au/20210708
sudo dkms install 8821au/20210708
```

### Step 3: Load the Driver

```bash
# Blacklist the bad driver (rtw88)
sudo tee /etc/modprobe.d/blacklist-rtw88.conf > /dev/null <<'EOF'
blacklist rtw88
blacklist rtw88_core
blacklist rtw88_pci
blacklist rtw88_8821a
EOF

# Load the good driver
sudo modprobe -r rtw88 2>/dev/null
sudo modprobe 8821au

# Update initramfs
sudo update-initramfs -u
```

### Step 4: Reboot

```bash
sudo reboot
```

### Step 5: Verify Installation

```bash
# Check driver is loaded
lsmod | grep 8821au
# Expected: 8821au  1234567  0

# Check interface exists
ip link show
# Expected: wlx5c628b765de2 (or similar)

# Check monitor mode support
iw list | grep -A 5 "Supported"
# Expected: * monitor

# Check USB VID:PID
lsusb | grep 2357
# Expected: Bus 001 Device 003: ID 2357:0120 TP-Link Archer T2U Plus
```

---

## Verification Checklist

After installation, verify each item:

- [ ] `lsmod | grep 8821au` shows module loaded
- [ ] `iw list` shows `* monitor` under interface modes
- [ ] `lsusb` shows `2357:0120` (TP-Link T2U Plus)
- [ ] No kernel errors: `dmesg | grep -i 8821` shows clean load
- [ ] Monitor mode works: `sudo iw dev wlx5c628b765de2 set type monitor`
- [ ] Injection works: `sudo aireplay-ng --test wlx5c628b765de2`

---

## Troubleshooting

### Driver Not Loading

```bash
# Check for errors
dmesg | tail -20

# Check if rtw88 is still loaded
lsmod | grep rtw

# Force unload rtw88
sudo modprobe -r rtw88_8821a
sudo modprobe -r rtw88_pci
sudo modprobe -r rtw88_core
sudo modprobe -r rtw88

# Load morrownr
sudo modprobe 8821au
```

### Monitor Mode Not Available

```bash
# Check what driver is bound
ls -la /sys/class/net/wlx5c628b765de2/device/driver

# If it shows rtw88, reinstall morrownr
cd ~/8821au-20210708
sudo ./install-driver.sh

# Reboot
sudo reboot
```

### USB Device Not Detected

```bash
# Check USB
lsusb | grep 2357

# If not showing, try different USB port
# If still not showing, check USB cable

# Reset USB
echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 2
echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind
```

### Kernel Panic on Some Hardware

```bash
# Blacklist the module
echo 'blacklist mt7902' | sudo tee /etc/modprobe.d/blacklist-mt7902.conf
sudo update-initramfs -u

# Reboot and try again
sudo reboot
```

---

## Uninstallation

If you need to remove the morrownr driver:

```bash
cd ~/8821au-20210708
sudo ./uninstall-driver.sh

# Or manually
sudo dkms remove 8821au/20210708 --all
sudo rm -rf /usr/src/8821au-20210708
sudo rm /etc/modprobe.d/blacklist-rtw88.conf
sudo update-initramfs -u
sudo reboot
```

---

## Adapter Priority for Sidewinder

| Priority | Adapter | Role | Why |
|----------|---------|------|-----|
| **1** | RTL8821AU (morrownr) | **Primary attack** | Full monitor + injection + 5GHz + VHT |
| **2** | RT5370 | **Backup attack** | Works out of box, 2.4GHz only, limited injection |
| **3** | MT7902 (built-in) | **Internet only** | No injection, RX-only monitor mode |

---

## Summary

| Task | Command |
|------|---------|
| **Install morrownr** | `sudo ./install-driver.sh` |
| **Verify** | `lsmod \| grep 8821au` |
| **Check monitor** | `iw list \| grep monitor` |
| **Uninstall** | `sudo ./uninstall-driver.sh` |
| **GitHub** | https://github.com/morrownr/8821au-20210708 |
