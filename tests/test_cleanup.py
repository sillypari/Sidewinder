"""Tests for Cleanup module."""
import pytest
from unittest.mock import AsyncMock, patch
from sidewinder.core.cleanup import CleanupManager

@pytest.mark.asyncio
async def test_kill_attack_processes():
    mgr = CleanupManager()
    
    with patch("sidewinder.core.subprocess_mgr.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value.success = True
        
        await mgr._kill_attack_processes()
        
        # Should call killall for all processes in ATTACK_PROCESSES
        assert mock_run.call_count >= 3

@pytest.mark.asyncio
async def test_full_cleanup():
    mgr = CleanupManager()
    
    with patch.object(mgr, "_kill_attack_processes", new_callable=AsyncMock) as mock_kill, \
         patch("sidewinder.adapters.AdapterManager.discover", new_callable=AsyncMock), \
         patch("sidewinder.core.monitor.get_interface_mode_sync") as mock_mode, \
         patch("sidewinder.core.monitor.exit_monitor_mode", new_callable=AsyncMock) as mock_exit, \
         patch("sidewinder.core.services.ServiceManager.restore", new_callable=AsyncMock) as mock_restore, \
         patch("sidewinder.core.cleanup.run", new_callable=AsyncMock) as mock_run:
         
         mock_mode.return_value = "monitor"
         
         await mgr.full_cleanup()
         
         mock_kill.assert_called_once()
         mock_restore.assert_called_once()
