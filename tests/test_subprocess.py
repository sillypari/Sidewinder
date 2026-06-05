"""Tests for SubprocessManager."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sidewinder.core.subprocess_mgr import SubprocessManager, ProcessResult

@pytest.mark.asyncio
async def test_run_success():
    mgr = SubprocessManager()
    
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"hello\n", b"")
    mock_proc.returncode = 0
    
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_proc
        
        result = await mgr.run(["echo", "hello"])
        
        assert result.success is True
        assert result.stdout == "hello"
        assert result.stderr == ""
        assert result.returncode == 0

@pytest.mark.asyncio
async def test_run_timeout():
    mgr = SubprocessManager()
    
    mock_proc = AsyncMock()
    mock_proc.communicate.side_effect = asyncio.TimeoutError()
    mock_proc.returncode = None
    mock_proc.pid = 12345
    
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec, \
         patch("os.killpg", create=True) as mock_kill, \
         patch("os.getpgid", create=True, return_value=12345), \
         patch("signal.SIGKILL", create=True):
        
        mock_exec.return_value = mock_proc
        
        with pytest.raises(TimeoutError):
            await mgr.run(["sleep", "10"], timeout=0.1)
        
        assert mock_kill.call_count == 2  # SIGTERM and SIGKILL

@pytest.mark.asyncio
async def test_stream():
    mgr = SubprocessManager()
    
    mock_proc = AsyncMock()
    # Mock an async iterator for stdout
    async def mock_stdout():
        yield b"line 1\n"
        yield b"line 2\n"
    
    mock_proc.stdout = mock_stdout()
    mock_proc.returncode = None
    mock_proc.pid = 12345
    
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec, \
         patch("os.killpg", create=True) as mock_kill, \
         patch("os.getpgid", create=True, return_value=12345), \
         patch("signal.SIGKILL", create=True):
        
        mock_exec.return_value = mock_proc
        
        lines = []
        async for line in mgr.stream(["echo", "line 1\nline 2"]):
            lines.append(line)
            
        assert lines == ["line 1", "line 2"]
        assert mock_kill.call_count > 0  # Kills in finally block

