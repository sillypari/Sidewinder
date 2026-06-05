"""Sidewinder RFKill Management.

Detects and resolves hardware/software blocks on wireless interfaces.
"""
import asyncio
import logging
from typing import Tuple

from .subprocess_mgr import run

logger = logging.getLogger(__name__)


async def is_rfkill_blocked() -> Tuple[bool, str]:
    """Check if WiFi is blocked by rfkill.

    Returns:
        Tuple of (is_blocked, details_string).
    """
    try:
        result = await run(["rfkill", "list", "wifi"], check=False)
        output = result.stdout.lower()
        if "soft blocked: yes" in output or "hard blocked: yes" in output:
            logger.warning("WiFi is blocked by rfkill:\n%s", result.stdout)
            return True, result.stdout
        return False, ""
    except Exception as e:
        logger.debug("Failed to check rfkill: %s", e)
        return False, str(e)


async def unblock_rfkill() -> bool:
    """Attempt to unblock WiFi via software rfkill unblock.

    Returns:
        True if successfully unblocked (or wasn't blocked), False if hard blocked.
    """
    logger.info("Attempting to unblock WiFi via rfkill...")
    try:
        await run(["rfkill", "unblock", "wifi"], check=False)
        
        # Verify if it worked
        blocked, details = await is_rfkill_blocked()
        if blocked:
            if "hard blocked: yes" in details.lower():
                logger.error("WiFi is HARD BLOCKED. Check physical switch/Fn keys.")
            else:
                logger.error("Failed to unblock WiFi (software block persists).")
            return False
            
        logger.info("WiFi unblocked successfully.")
        return True
    except Exception as e:
        logger.error("Error running rfkill unblock: %s", e)
        return False
