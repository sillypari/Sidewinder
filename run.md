# Running Sidewinder on Linux

Sidewinder is a native Linux tool. It interacts directly with the `sysfs` filesystem (`/sys/class/net/`), modifies physical network interfaces (putting them into monitor mode), and kills conflicting services like `NetworkManager`. Therefore, **it must be run as root**.

## 1. Install System Dependencies

Sidewinder requires several native networking tools to handle monitor mode, packet injection, and offline cracking. Open your terminal and run:

```bash
sudo apt update
sudo apt install aircrack-ng rfkill iw xclip
```

**Optional but recommended** (for advanced attacks):
```bash
sudo apt install hashcat hcxdumptool hcxtools reaver
```
*(Note: `hcxtools` provides the `hcxpcapngtool` needed for PMKID conversion)*

## 2. Install Sidewinder Python Dependencies

Navigate to the root directory of the Sidewinder project and install the required Python packages (such as `Textual` for the TUI). You can do this using the `Makefile` or `pip`:

```bash
cd /path/to/Sidewinder
make install

# OR manually:
pip install -e ".[dev]"
```

## 3. Run the App

You can start it using the built-in Makefile command:
```bash
make run
```

Or you can run it directly with Python:
```bash
sudo python3 -m sidewinder.sidewinder
```

---

## Diagnostics & Troubleshooting

If you want to ensure your system is perfectly set up before running the tool, you can use the built-in diagnostic commands from the Makefile:

*   **`make check-tools`**: Verifies that all required underlying binaries (aircrack-ng, iw, rfkill, hashcat) are installed and in your PATH.
*   **`make check-adapters`**: Checks if your USB WiFi adapters are detected and if they support monitor mode.
