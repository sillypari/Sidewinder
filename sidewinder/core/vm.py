"""Sidewinder VM Detection.

Detects if Sidewinder is running inside a Virtual Machine or WSL.
WiFi adapters (especially USB passthrough) often misbehave in VMs,
failing to enter monitor mode or drop packets during injection.
"""
import logging
import os
from typing import Tuple

from .subprocess_mgr import run

logger = logging.getLogger(__name__)


async def detect_vm() -> Tuple[bool, str]:
    """Detect if running inside a VM or WSL.
    
    Returns:
        Tuple of (is_vm, vm_type_string).
        vm_type_string might be 'wsl', 'virtualbox', 'vmware', 'qemu', etc.
    """
    # 1. Check WSL
    if hasattr(os, "uname"):
        release = os.uname().release.lower()
        if "microsoft" in release or "wsl" in release:
            logger.warning("WSL environment detected.")
            return True, "wsl"

    # 2. Check systemd-detect-virt
    try:
        result = await run(["systemd-detect-virt"], check=False)
        output = result.stdout.strip().lower()
        if result.returncode == 0 and output != "none":
            logger.warning("VM environment detected via systemd: %s", output)
            return True, output
    except Exception:
        pass

    # 3. Fallback: Check dmesg or lscpu for common hypervisor strings
    try:
        result = await run(["lscpu"], check=False)
        output = result.stdout.lower()
        if "hypervisor vendor:" in output:
            for line in output.splitlines():
                if "hypervisor vendor:" in line:
                    vendor = line.split(":", 1)[1].strip()
                    logger.warning("VM environment detected via lscpu: %s", vendor)
                    return True, vendor
    except Exception:
        pass

    return False, "native"
