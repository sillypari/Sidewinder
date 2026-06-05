"""Tests for capture engine."""
import pytest
from sidewinder.core.capture import is_m1, is_m2, is_m3, is_m4

def test_is_m1():
    # Pairwise(0x0008) | ACK(0x0080)
    ki = 0x0088
    assert is_m1(ki) is True
    assert is_m2(ki) is False
    assert is_m3(ki) is False
    assert is_m4(ki) is False

def test_is_m2():
    # Pairwise(0x0008) | MIC(0x0100)
    ki = 0x0108
    assert is_m1(ki) is False
    assert is_m2(ki) is True
    assert is_m3(ki) is False
    assert is_m4(ki) is False

def test_is_m3():
    # Pairwise(0x0008) | Install(0x0040) | ACK(0x0080) | MIC(0x0100) | Secure(0x0200)
    ki = 0x03C8
    assert is_m1(ki) is False
    assert is_m2(ki) is False
    assert is_m3(ki) is True
    assert is_m4(ki) is False

def test_is_m4():
    # Pairwise(0x0008) | MIC(0x0100) | Secure(0x0200)
    ki = 0x0308
    assert is_m1(ki) is False
    assert is_m2(ki) is False
    assert is_m3(ki) is False
    assert is_m4(ki) is True
