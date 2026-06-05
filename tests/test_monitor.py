"""Tests for Monitor Mode functions."""
import pytest
from unittest.mock import AsyncMock, patch
from sidewinder.core.monitor import enter_monitor_mode, exit_monitor_mode, set_channel
from sidewinder.core.subprocess_mgr import ProcessResult

@pytest.mark.asyncio
async def test_enter_monitor_mode():
    with patch("sidewinder.core.monitor.run", new_callable=AsyncMock) as mock_run, \
         patch("sidewinder.core.monitor.get_interface_mode_sync") as mock_mode:
        
        # Simulate 'iw dev wlan0 interface add wlan0mon type monitor' success
        mock_run.return_value = ProcessResult(0, "", "")
        mock_mode.return_value = "monitor"
        
        mon_iface = await enter_monitor_mode("wlan0", "phy0", 6)
        assert mon_iface == "wlan0mon"
        assert mock_run.call_count >= 3  # ip link set down, iw dev add, ip link set up

@pytest.mark.asyncio
async def test_exit_monitor_mode():
    with patch("sidewinder.core.monitor.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ProcessResult(0, "", "")
        
        await exit_monitor_mode("wlan0mon", "wlan0", "phy0")
        assert mock_run.call_count >= 3  # ip link set down, iw dev del, ip link set up wlan0

@pytest.mark.asyncio
async def test_set_channel():
    with patch("sidewinder.core.monitor.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ProcessResult(0, "", "")
        
        await set_channel("wlan0mon", 6)
        mock_run.assert_called_with(["iw", "dev", "wlan0mon", "set", "channel", "6"])
