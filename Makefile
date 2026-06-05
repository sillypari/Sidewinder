.PHONY: run dev install test lint typecheck clean

# ── Install ───────────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

# ── Run ───────────────────────────────────────────────────────────────────────

run:
	sudo python -m sidewinder.sidewinder

dev:
	sudo python -m sidewinder.sidewinder --dev

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v --cov=sidewinder --cov-report=term-missing

test-fast:
	pytest tests/ -v -x -q

# ── Code Quality ──────────────────────────────────────────────────────────────

lint:
	ruff check sidewinder/ tests/

lint-fix:
	ruff check --fix sidewinder/ tests/

typecheck:
	pyright sidewinder/

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache dist build

# ── Hardware Verification ─────────────────────────────────────────────────────

check-adapters:
	@echo "=== USB Adapters ==="
	@lsusb | grep -E "148f|2357|14c3" || echo "No known adapters found"
	@echo ""
	@echo "=== Interfaces ==="
	@ip link show | grep wl || echo "No wireless interfaces"
	@echo ""
	@echo "=== Monitor Mode Support ==="
	@iw list 2>/dev/null | grep -A2 "Supported interface" | head -20

check-tools:
	@echo "=== Required Tools ==="
	@which aircrack-ng && echo "[OK] aircrack-ng" || echo "[FAIL] aircrack-ng"
	@which airodump-ng && echo "[OK] airodump-ng" || echo "[FAIL] airodump-ng"
	@which aireplay-ng && echo "[OK] aireplay-ng" || echo "[FAIL] aireplay-ng"
	@which hashcat && echo "[OK] hashcat" || echo "[WARN] hashcat (optional)"
	@which hcxpcapngtool && echo "[OK] hcxpcapngtool" || echo "[WARN] hcxpcapngtool (optional)"
	@which rfkill && echo "[OK] rfkill" || echo "[FAIL] rfkill"
	@which iw && echo "[OK] iw" || echo "[FAIL] iw"
