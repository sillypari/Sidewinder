"""Tests for Sidewinder session management."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from sidewinder.core.session import (
    Client,
    CrackResult,
    HandshakeResult,
    Network,
    Session,
)


class TestNetwork:
    def test_hidden_essid(self):
        n = Network(
            bssid="AA:BB:CC:DD:EE:FF",
            channel=6,
            signal=-50,
            privacy="WPA2",
            cipher="CCMP",
            auth="PSK",
            essid="",
        )
        assert n.display_name() == "[HIDDEN]"

    def test_normal_essid(self):
        n = Network(
            bssid="AA:BB:CC:DD:EE:FF",
            channel=6,
            signal=-50,
            privacy="WPA2",
            cipher="CCMP",
            auth="PSK",
            essid="MyWiFi",
        )
        assert n.display_name() == "MyWiFi"


class TestHandshakeResult:
    def test_full_handshake(self):
        hr = HandshakeResult(status="full", m1=True, m2=True, m3=True, m4=True)
        assert hr.status == "full"
        assert hr.m1 and hr.m2 and hr.m3 and hr.m4

    def test_partial_handshake(self):
        hr = HandshakeResult(status="partial", m1=True, m2=True)
        assert hr.status == "partial"
        assert hr.m1 and hr.m2
        assert not hr.m3 and not hr.m4

    def test_invalid_handshake(self):
        hr = HandshakeResult(status="invalid")
        assert hr.status == "invalid"
        assert not hr.m1 and not hr.m2 and not hr.m3 and not hr.m4


class TestCrackResult:
    def test_found(self):
        cr = CrackResult(
            found=True,
            password="secret123",
            method="aircrack",
            wordlist="/usr/share/wordlists/rockyou.txt",
            keys_tested=50000,
            elapsed_seconds=12.5,
        )
        assert cr.found
        assert cr.password == "secret123"

    def test_not_found(self):
        cr = CrackResult(found=False)
        assert not cr.found
        assert cr.password == ""


class TestClient:
    def test_creation(self):
        c = Client(
            mac="AA:BB:CC:DD:EE:FF",
            bssid="11:22:33:44:55:66",
            signal=-60,
            packets=100,
            probe="TestNetwork",
        )
        assert c.mac == "AA:BB:CC:DD:EE:FF"
        assert c.probe == "TestNetwork"


class TestSession:
    def test_creation_with_defaults(self):
        s = Session()
        assert s.id  # UUID generated
        assert s.start_time  # ISO timestamp
        assert s.adapter == ""
        assert s.scan_results == []
        assert s.clients == []
        assert s.selected_target is None
        assert s.captures == []
        assert s.handshake is None
        assert s.cracked_passwords == []

    def test_log_entry(self):
        s = Session()
        s.log("scan_started", channel=6)
        assert len(s.logs) == 1
        assert s.logs[0]["event"] == "scan_started"
        assert s.logs[0]["channel"] == 6
        assert "time" in s.logs[0]

    def test_multiple_log_entries(self):
        s = Session()
        s.log("scan_started")
        s.log("target_selected", bssid="AA:BB:CC:DD:EE:FF")
        s.log("capture_started")
        assert len(s.logs) == 3

    def test_elapsed_seconds_returns_float(self):
        s = Session()
        elapsed = s.elapsed_seconds()
        assert isinstance(elapsed, float)
        assert elapsed >= 0


class TestSessionSaveLoad:
    def test_save_and_load_empty_session(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.save(str(session_file))
        assert session_file.exists()

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert loaded.id == s.id
        assert loaded.scan_results == []
        assert loaded.cracked_passwords == []

    def test_save_and_load_with_networks(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.scan_results = [
            Network(
                bssid="AA:BB:CC:DD:EE:FF",
                channel=6,
                signal=-50,
                privacy="WPA2",
                cipher="CCMP",
                auth="PSK",
                essid="TestNet",
            ),
            Network(
                bssid="11:22:33:44:55:66",
                channel=11,
                signal=-70,
                privacy="WPA2",
                cipher="TKIP",
                auth="PSK",
                essid="HiddenNet",
            ),
        ]
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert len(loaded.scan_results) == 2
        assert isinstance(loaded.scan_results[0], Network)
        assert loaded.scan_results[0].essid == "TestNet"
        assert loaded.scan_results[1].display_name() == "HiddenNet"

    def test_save_and_load_with_selected_target(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.selected_target = Network(
            bssid="AA:BB:CC:DD:EE:FF",
            channel=6,
            signal=-50,
            privacy="WPA2",
            cipher="CCMP",
            auth="PSK",
            essid="TargetNet",
        )
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert isinstance(loaded.selected_target, Network)
        assert loaded.selected_target.essid == "TargetNet"

    def test_save_and_load_with_handshake(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.handshake = HandshakeResult(
            status="full", m1=True, m2=True, m3=True, m4=True, eapol_count=8
        )
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert isinstance(loaded.handshake, HandshakeResult)
        assert loaded.handshake.status == "full"
        assert loaded.handshake.m1 is True
        assert loaded.handshake.m3 is True

    def test_save_and_load_with_crack_result(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.cracked_passwords = [
            CrackResult(
                found=True,
                password="pass123",
                method="aircrack",
                wordlist="/usr/share/wordlists/rockyou.txt",
                keys_tested=1000,
                elapsed_seconds=5.2,
            )
        ]
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert len(loaded.cracked_passwords) == 1
        assert isinstance(loaded.cracked_passwords[0], CrackResult)
        assert loaded.cracked_passwords[0].password == "pass123"

    def test_save_and_load_with_clients(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.clients = [
            Client(
                mac="AA:BB:CC:DD:EE:FF",
                bssid="11:22:33:44:55:66",
                signal=-55,
                packets=200,
                probe="MyWiFi",
            )
        ]
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert len(loaded.clients) == 1
        assert isinstance(loaded.clients[0], Client)
        assert loaded.clients[0].probe == "MyWiFi"

    def test_save_and_load_full_session(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session(adapter="wlan1")
        s.scan_results = [
            Network(
                bssid="AA:BB:CC:DD:EE:FF",
                channel=6,
                signal=-45,
                privacy="WPA2",
                cipher="CCMP",
                auth="PSK",
                essid="TestNet",
                wps=True,
            )
        ]
        s.selected_target = s.scan_results[0]
        s.clients = [
            Client(
                mac="DE:AD:BE:EF:00:01",
                bssid="AA:BB:CC:DD:EE:FF",
                signal=-50,
            )
        ]
        s.handshake = HandshakeResult(
            status="full", m1=True, m2=True, m3=True, m4=True
        )
        s.cracked_passwords = [
            CrackResult(found=True, password="hunter2", method="hashcat")
        ]
        s.log("scan_started")
        s.log("handshake_captured")

        s.save(str(session_file))
        loaded = Session.load(str(session_file))

        assert loaded is not None
        assert loaded.adapter == "wlan1"
        assert len(loaded.scan_results) == 1
        assert loaded.scan_results[0].wps is True
        assert isinstance(loaded.selected_target, Network)
        assert loaded.selected_target.essid == "TestNet"
        assert len(loaded.clients) == 1
        assert isinstance(loaded.handshake, HandshakeResult)
        assert loaded.handshake.status == "full"
        assert len(loaded.cracked_passwords) == 1
        assert isinstance(loaded.cracked_passwords[0], CrackResult)
        assert loaded.cracked_passwords[0].found is True
        assert len(loaded.logs) == 2
        assert loaded.logs[0]["event"] == "scan_started"
        assert loaded.logs[1]["event"] == "handshake_captured"

    def test_load_nonexistent_file(self):
        result = Session.load("/nonexistent/path/session.json")
        assert result is None

    def test_save_creates_parent_dirs(self, tmp_path):
        session_file = tmp_path / "deep" / "nested" / "session.json"
        s = Session()
        s.save(str(session_file))
        assert session_file.exists()

    def test_default_path_used_when_empty(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        # Save with explicit path
        s.save(str(session_file))
        # Verify default path is still the default
        assert s.DEFAULT_PATH == "~/.sidewinder/session.json"

    def test_load_preserves_logs(self, tmp_path):
        session_file = tmp_path / "session.json"
        s = Session()
        s.log("event_a", foo="bar")
        s.log("event_b", num=42)
        s.save(str(session_file))

        loaded = Session.load(str(session_file))
        assert loaded is not None
        assert len(loaded.logs) == 2
        assert loaded.logs[0]["event"] == "event_a"
        assert loaded.logs[0]["foo"] == "bar"
        assert loaded.logs[1]["event"] == "event_b"
        assert loaded.logs[1]["num"] == 42
