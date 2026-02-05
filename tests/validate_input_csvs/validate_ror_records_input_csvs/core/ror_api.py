"""ROR API client with rate limiting."""

import threading
import time


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, max_calls: int = 1000, period: float = 300):
        """
        Args:
            max_calls: Maximum calls allowed in the period
            period: Time period in seconds (default 5 minutes)
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Wait if necessary to stay under rate limit."""
        with self._lock:
            now = time.time()
            # Prune old calls
            self._calls = [t for t in self._calls if now - t < self.period]

            if len(self._calls) >= self.max_calls:
                sleep_time = self.period - (now - self._calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # Prune again after sleeping
                now = time.time()
                self._calls = [t for t in self._calls if now - t < self.period]

            self._calls.append(time.time())
