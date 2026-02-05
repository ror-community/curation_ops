# tests/test_ror_api.py
import time
from unittest.mock import patch

import pytest

from validate_ror_records_input_csvs.core.ror_api import RateLimiter


class TestRateLimiter:
    def test_allows_calls_under_limit(self):
        limiter = RateLimiter(max_calls=5, period=60)

        for _ in range(5):
            limiter.wait()

        # Should not raise or block significantly

    def test_tracks_call_count(self):
        limiter = RateLimiter(max_calls=5, period=60)

        for _ in range(3):
            limiter.wait()

        assert len(limiter._calls) == 3

    @patch("time.sleep")
    def test_sleeps_when_limit_reached(self, mock_sleep):
        limiter = RateLimiter(max_calls=2, period=60)

        limiter.wait()
        limiter.wait()
        limiter.wait()  # Should trigger sleep

        mock_sleep.assert_called()

    def test_prunes_old_calls(self):
        limiter = RateLimiter(max_calls=5, period=0.1)

        limiter.wait()
        limiter.wait()
        time.sleep(0.15)
        limiter.wait()

        # Old calls should be pruned
        assert len(limiter._calls) == 1
