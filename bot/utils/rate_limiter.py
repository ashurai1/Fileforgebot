"""
ConvertX Bot - Per-user Rate Limiter
Uses a sliding window counter stored in memory.
"""

import time
from collections import defaultdict
from bot.config import RATE_LIMIT_MAX_OPS, RATE_LIMIT_WINDOW, logger


class RateLimiter:
    """Thread-safe, in-memory sliding window rate limiter keyed by user_id."""

    def __init__(
        self,
        max_ops: int = RATE_LIMIT_MAX_OPS,
        window: int = RATE_LIMIT_WINDOW,
    ) -> None:
        self.max_ops = max_ops
        self.window = window
        # user_id -> list of timestamps
        self._hits: dict[int, list[float]] = defaultdict(list)

    def _prune(self, user_id: int) -> None:
        """Remove expired timestamps for a user."""
        cutoff = time.monotonic() - self.window
        self._hits[user_id] = [
            t for t in self._hits[user_id] if t > cutoff
        ]

    def is_allowed(self, user_id: int) -> bool:
        """Return True if the user has not exceeded the rate limit."""
        self._prune(user_id)
        if len(self._hits[user_id]) >= self.max_ops:
            logger.warning("Rate limit exceeded for user %s", user_id)
            return False
        self._hits[user_id].append(time.monotonic())
        return True

    def remaining(self, user_id: int) -> int:
        """Return how many operations the user has left in the current window."""
        self._prune(user_id)
        return max(0, self.max_ops - len(self._hits[user_id]))


# Singleton instance used across the bot
rate_limiter = RateLimiter()
