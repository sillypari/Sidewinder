"""Sidewinder Entry Point.

Invoked via `python -m sidewinder` or the `sidewinder` console script.
"""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
