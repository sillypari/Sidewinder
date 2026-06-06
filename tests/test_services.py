"""Tests for ServiceManager."""
import pytest
from unittest.mock import AsyncMock, patch
from sidewinder.core.services import ServiceManager, KilledProcess, KillResult
from sidewinder.core.subprocess_mgr import ProcessResult

@pytest.mark.asyncio
async def test_find_conflicting():
    mgr = ServiceManager()
    
    # Mock 'ps -A -o pid=,args=' output
    mock_ps_output = "  123 /usr/sbin/NetworkManager --no-daemon\n  456 wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf\n  789 bash\n"
    
    with patch("sidewinder.core.services.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ProcessResult(0, mock_ps_output, "")
        
        found = await mgr.find_conflicting()
        assert len(found) == 2
        assert (123, "NetworkManager") in found
        assert (456, "wpa_supplicant") in found

@pytest.mark.asyncio
async def test_kill_conflicting():
    mgr = ServiceManager()
    
    with patch.object(mgr, "find_conflicting", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [(123, "NetworkManager"), (456, "wpa_supplicant"), (789, "NetworkManager")]
        
        with patch("sidewinder.core.services.run", new_callable=AsyncMock) as mock_run, \
             patch("os.kill") as mock_kill:
            
            mock_run.return_value = ProcessResult(0, "", "")
            
            result = await mgr.kill_conflicting()
            
            assert len(result.killed) == 2
            assert result.killed[0].name == "NetworkManager"
            assert result.killed[1].name == "wpa_supplicant"
            assert len(result.skipped) == 1
            assert result.skipped[0] == "NetworkManager"
            
            assert mock_run.call_count == 2 # 2 unique services to systemctl stop
            assert mock_kill.call_count == 2 # 2 processes to os.kill

@pytest.mark.asyncio
async def test_restore_services():
    mgr = ServiceManager()
    mgr.killed_processes = [
        KilledProcess(name="NetworkManager", pid=123, was_systemd=True),
        KilledProcess(name="wpa_supplicant", pid=456, was_systemd=False)
    ]
    
    with patch("sidewinder.core.services.run", new_callable=AsyncMock) as mock_run, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_run.return_value = ProcessResult(0, "active", "")
        
        await mgr.restore()
        
        assert len(mgr.killed_processes) == 0
        # 2 services: systemctl start + systemctl is-active (returns "active" immediately) = 4 calls
        assert mock_run.call_count == 4
