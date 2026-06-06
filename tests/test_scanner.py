"""Tests for Scanner module."""
import pytest
from unittest.mock import AsyncMock, patch
from sidewinder.core.scanner import ScanEngine
from sidewinder.core.session import Network

@pytest.mark.asyncio
async def test_scan_engine_parse_csv():
    engine = ScanEngine()
    
    csv_content = """BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
AA:BB:CC:DD:EE:FF, 2026-06-05 10:00:00, 2026-06-05 10:01:00,  6,  54, WPA2, CCMP, PSK, -50,       10,        0,   0.  0.  0.  0,  12, TestNetwork, 

Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
11:22:33:44:55:66, 2026-06-05 10:00:00, 2026-06-05 10:01:00, -60,       20, AA:BB:CC:DD:EE:FF, 
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        networks = []
        clients = []
        
        def on_network(n):
            networks.append(n)
        def on_client(c):
            clients.append(c)
        
        await engine._parse_csv(temp_path, on_network, on_client)
        
        assert len(networks) == 1
        assert networks[0].bssid == "AA:BB:CC:DD:EE:FF"
        assert networks[0].essid == "TestNetwork"
        assert networks[0].channel == 6
        assert networks[0].signal == -50
        
        assert len(clients) == 1
        assert clients[0].mac == "11:22:33:44:55:66"
        assert clients[0].bssid == "AA:BB:CC:DD:EE:FF"
    finally:
        os.unlink(temp_path)

@pytest.mark.asyncio
async def test_scan_engine_start_stop():
    engine = ScanEngine()
    
    with patch("sidewinder.core.subprocess_mgr.SubprocessManager.start_background", new_callable=AsyncMock) as mock_start, \
         patch("sidewinder.core.subprocess_mgr.SubprocessManager.kill_background", new_callable=AsyncMock) as mock_kill, \
         patch("sidewinder.core.scanner.os.path.exists", return_value=False):
        
        import asyncio
        task = asyncio.create_task(engine.scan("wlan0mon"))
        
        await asyncio.sleep(0.01)
        assert engine._running is True
        
        await engine.stop_and_wait()
        assert engine._running is False
        assert mock_kill.call_count >= 1
        
        task.cancel()


@pytest.mark.asyncio
async def test_mock_interface_scan():
    engine = ScanEngine()
    networks = []
    clients = []
    
    def on_network(n):
        networks.append(n)
    def on_client(c):
        clients.append(c)
        
    import asyncio
    task = asyncio.create_task(engine.scan("wlan0 (MOCK)", on_network=on_network, on_client=on_client))
    
    # Wait a bit for mock scan loop to run
    await asyncio.sleep(1.2)
    
    assert len(networks) > 0
    assert len(clients) > 0
    assert any(n.essid == "HomeWiFi" for n in networks)
    
    engine.stop()
    await engine.stop_and_wait()
    assert engine._running is False
    try:
        await task
    except asyncio.CancelledError:
        pass

