"""Tests for Sidewinder error classification system."""
from __future__ import annotations

import pytest
from datetime import datetime

from sidewinder.core.errors import (
    ADAPTER_ERRORS,
    ERROR_DB,
    Category,
    Severity,
    SidewinderError,
    make_adapter_error,
)


class TestSidewinderError:
    def test_basic_creation(self):
        err = SidewinderError(
            severity=Severity.ERROR,
            category=Category.HARDWARE,
            what="Test error",
            why="Testing",
            how_to_fix=["Fix 1", "Fix 2"],
        )
        assert err.severity == Severity.ERROR
        assert err.category == Category.HARDWARE
        assert err.what == "Test error"
        assert len(err.how_to_fix) == 2

    def test_str_representation(self):
        err = SidewinderError(
            severity=Severity.CRITICAL,
            category=Category.PERMISSION,
            what="Root required",
            why="Monitor mode needs root",
            how_to_fix=["sudo sidewinder"],
        )
        s = str(err)
        assert "CRITICAL" in s
        assert "Root required" in s
        assert "sudo sidewinder" in s

    def test_to_dict(self):
        err = SidewinderError(
            severity=Severity.WARNING,
            category=Category.NETWORK,
            what="No handshake",
            why="No clients",
            how_to_fix=["Try deauth"],
        )
        d = err.to_dict()
        assert d["severity"] == "warning"
        assert d["category"] == "network"
        assert d["what"] == "No handshake"
        assert isinstance(d["how_to_fix"], list)
        assert isinstance(d["timestamp"], str)

    def test_is_exception(self):
        err = SidewinderError(
            severity=Severity.ERROR,
            category=Category.HARDWARE,
            what="Adapter disconnected",
            why="USB removed",
            how_to_fix=["Replug adapter"],
        )
        with pytest.raises(SidewinderError):
            raise err

    def test_timestamp_is_datetime(self):
        err = SidewinderError(
            severity=Severity.INFO,
            category=Category.USER,
            what="Test",
            why="Test",
            how_to_fix=[],
        )
        assert isinstance(err.timestamp, datetime)


class TestErrorDB:
    def test_all_required_keys_present(self):
        required = [
            "ADAPTER_NOT_FOUND",
            "MONITOR_MODE_FAILED",
            "ROOT_REQUIRED",
            "DISK_FULL",
            "NO_HANDSHAKE",
            "AIRODUMP_FAILED",
            "AIREPLAY_FAILED",
            "WRONG_DRIVER",
            "MT7902_NO_INJECTION",
        ]
        for key in required:
            assert key in ERROR_DB, f"Missing error key: {key}"

    def test_all_entries_are_sidewinder_errors(self):
        for key, err in ERROR_DB.items():
            assert isinstance(err, SidewinderError), f"{key} is not a SidewinderError"

    def test_how_to_fix_is_list(self):
        for key, err in ERROR_DB.items():
            assert isinstance(err.how_to_fix, list), f"{key}.how_to_fix is not a list"
            assert len(err.how_to_fix) > 0, f"{key}.how_to_fix is empty"

    def test_root_required_is_critical(self):
        assert ERROR_DB["ROOT_REQUIRED"].severity == Severity.CRITICAL

    def test_no_handshake_is_warning(self):
        assert ERROR_DB["NO_HANDSHAKE"].severity == Severity.WARNING


class TestAdapterErrors:
    def test_rt5370_errors_exist(self):
        assert "RT5370" in ADAPTER_ERRORS
        assert "MONITOR_FAILED" in ADAPTER_ERRORS["RT5370"]
        assert "INJECTION_SLOW" in ADAPTER_ERRORS["RT5370"]

    def test_rtl8821au_errors_exist(self):
        assert "RTL8821AU" in ADAPTER_ERRORS
        assert "WRONG_DRIVER" in ADAPTER_ERRORS["RTL8821AU"]
        assert "USB_SURPRISE" in ADAPTER_ERRORS["RTL8821AU"]

    def test_mt7902_errors_exist(self):
        assert "MT7902" in ADAPTER_ERRORS
        assert "NO_INJECTION" in ADAPTER_ERRORS["MT7902"]
        assert "KERNEL_PANIC" in ADAPTER_ERRORS["MT7902"]

    def test_each_error_has_required_fields(self):
        for chipset, errors in ADAPTER_ERRORS.items():
            for key, err_dict in errors.items():
                assert "what" in err_dict, f"{chipset}.{key} missing 'what'"
                assert "why" in err_dict, f"{chipset}.{key} missing 'why'"
                assert "how_to_fix" in err_dict, f"{chipset}.{key} missing 'how_to_fix'"


class TestMakeAdapterError:
    def test_rt5370_known_error(self):
        err = make_adapter_error("RT5370", "MONITOR_FAILED")
        assert isinstance(err, SidewinderError)
        assert "RT5370" in err.what
        assert len(err.how_to_fix) > 0

    def test_rtl8821au_wrong_driver(self):
        err = make_adapter_error("RTL8821AU", "WRONG_DRIVER", raw_error="no module")
        assert isinstance(err, SidewinderError)
        assert err.raw_error == "no module"

    def test_unknown_chipset_fallback(self):
        err = make_adapter_error("UNKNOWN_CHIP", "SOME_ERROR")
        assert isinstance(err, SidewinderError)
        assert "Check adapter and driver" in err.how_to_fix

    def test_unknown_error_key_fallback(self):
        err = make_adapter_error("RT5370", "NONEXISTENT_ERROR")
        assert isinstance(err, SidewinderError)
