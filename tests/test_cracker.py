"""Tests for crack engine."""
import pytest
from sidewinder.core.cracker import _parse_aircrack_line, _parse_hashcat_line

def test_parse_aircrack_progress():
    line = "                           KEY FOUND! [ mypassword123 ]"
    res = _parse_aircrack_line(line)
    # The current regex for aircrack line expects keys tested to be > 0 to return progress.
    # The KEY FOUND logic is handled in crack_aircrack, not _parse_aircrack_line.
    # Let's test actual progress line:
    res = _parse_aircrack_line("1234 keys tested (5678.90 k/s)")
    assert res is not None
    assert res.keys_tested == 1234
    assert res.keys_per_second == 5678900.0

def test_parse_hashcat_progress():
    line = "Progress.........: 1234567/14344391 (8.60%)"
    res = _parse_hashcat_line(line)
    assert res is not None
    assert res.keys_tested == 1234567
    assert res.total_keys == 14344391
    assert res.percent == 8.6
