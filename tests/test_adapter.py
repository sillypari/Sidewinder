"""Tests for Adapter detection module."""
import pytest
from unittest.mock import AsyncMock, patch
from sidewinder.core.adapter import AdapterInfo
from sidewinder.adapters import AdapterManager
from sidewinder.core.subprocess_mgr import ProcessResult

@pytest.mark.asyncio
async def test_detect_adapter_sysfs():
    with patch("sidewinder.core.adapter.list_interfaces", return_value=[]):
        mgr = AdapterManager()
        await mgr.discover()
        assert len(mgr.adapters) == 0

@pytest.mark.asyncio
async def test_detect_adapter_properties():
    info = AdapterInfo(
        iface="wlan0",
        phy="phy0",
        driver="rt2800usb",
        chipset="RT5370",
        mac="00:11:22:33:44:55",
        monitor_capable=True,
        injection_capable=True,
        bands=["2.4GHz"],
        current_mode="managed"
    )
    assert info.iface == "wlan0"
    assert info.monitor_capable is True
        
@pytest.mark.asyncio
async def test_get_best_for_operation():
    mgr = AdapterManager()
    mgr.adapters = {
        "wlan0": AdapterInfo(iface="wlan0", phy="phy0", driver="rtw88", chipset="RTL8821CE", mac="00:00:00:00:00:01", monitor_capable=False, injection_capable=False, bands=["2.4GHz"], current_mode="managed"),
        "wlan1": AdapterInfo(iface="wlan1", phy="phy1", driver="rt2800usb", chipset="RT5370", mac="00:00:00:00:00:02", monitor_capable=True, injection_capable=True, bands=["2.4GHz"], current_mode="managed"),
        "wlan2": AdapterInfo(iface="wlan2", phy="phy2", driver="mt7902", chipset="MT7902", mac="00:00:00:00:00:03", monitor_capable=True, injection_capable=False, bands=["2.4GHz", "5GHz"], current_mode="managed"),
    }
    
    # Injection requires True, True
    best_inj = mgr.get_best_for_operation("capture")
    assert best_inj is not None
    assert best_inj.iface == "wlan1"
    
    # Scan only requires Monitor=True
    best_scan = mgr.get_best_for_operation("scan")
    assert best_scan is not None
    assert best_scan.iface in ["wlan1", "wlan2"]
