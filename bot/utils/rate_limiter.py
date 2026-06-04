"""
Rate Limiter — Per-provider 429 tracker with automatic unblock.

Tracks which providers are temporarily blocked due to rate limits
and automatically unblocks them after a cooldown period.
"""

from __future__ import annotations

import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Track 429s per provider with automatic unblock after cooldown."""

    def __init__(self):
        self._blocked: dict[str, float] = {}  # provider → unblock_timestamp
        self._fail_counts: dict[str, int] = {}  # provider → consecutive failures

    def block(self, provider: str, seconds: int = 60) -> None:
        """Block a provider for `seconds` due to rate limiting."""
        count = self._fail_counts.get(provider, 0) + 1
        self._fail_counts[provider] = count
        
        # Exponential backoff: 60s → 120s → 240s (cap at 300s)
        backoff = min(seconds * (2 ** (count - 1)), 300)
        self._blocked[provider] = time.time() + backoff
        logger.warning(f"🚫 {provider} blocked for {backoff:.0f}s (failure #{count})")

    def is_blocked(self, provider: str) -> bool:
        """Check if a provider is currently blocked."""
        if provider not in self._blocked:
            return False
        if time.time() > self._blocked[provider]:
            del self._blocked[provider]
            # Reset fail count on successful unblock
            self._fail_counts.pop(provider, None)
            logger.info(f"✅ {provider} unblocked")
            return False
        return True

    def reset(self, provider: str) -> None:
        """Manually reset a provider's block status (e.g., on success)."""
        self._blocked.pop(provider, None)
        self._fail_counts.pop(provider, None)

    def status(self) -> dict[str, str]:
        """Get status of all tracked providers."""
        now = time.time()
        result = {}
        for provider, unblock_at in self._blocked.items():
            remaining = max(0, unblock_at - now)
            result[provider] = f"blocked ({remaining:.0f}s remaining)"
        return result
