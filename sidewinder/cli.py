"""Sidewinder Command Line Interface.

Parses arguments, checks root privileges, configures logging,
and launches the Textual TUI.
"""
import argparse
import os
import sys

from .core.logger import setup_logging
from .core.errors import SidewinderError
from .core.session import Session


def check_root() -> None:
    """Ensure the script is running with root privileges."""
    # On Windows (for dev/testing), os.geteuid doesn't exist
    if hasattr(os, "geteuid"):
        if os.geteuid() != 0:
            print("CRITICAL: Sidewinder requires root privileges for WiFi auditing.", file=sys.stderr)
            print("Please run via: sudo sidewinder", file=sys.stderr)
            sys.exit(1)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="sidewinder",
        description="Native Linux WiFi Audit Tool (TUI)",
        epilog="Bypasses airmon-ng. Fast, clean, reliable."
    )
    
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="Run in development mode (disables strict root checks for UI testing)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging to file"
    )
    parser.add_argument(
        "--resume", 
        type=str, 
        metavar="SESSION_ID",
        help="Attempt to resume a specific session ID (not fully implemented yet)"
    )

    args = parser.parse_args()

    if not args.dev:
        check_root()

    # Configure logging
    import logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Sidewinder CLI")

    # Launch the App
    try:
        from .ui.app import SidewinderApp
        
        # Load previous session if available
        # In a full implementation, we'd look up the session ID
        session = Session.load()
        
        app = SidewinderApp(dev_mode=args.dev, session=session)
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down.")
        print("\nExiting Sidewinder...")
    except Exception as e:
        logger.exception("Fatal error in main loop")
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
