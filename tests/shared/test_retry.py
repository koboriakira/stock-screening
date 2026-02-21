from __future__ import annotations

import pytest
import requests

from stock_screener.shared.retry import retry_on_rate_limit


class TestRetryOnRateLimit:
    def test_returns_result_on_success(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = retry_on_rate_limit(func, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    def test_retries_on_rate_limit_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = requests.models.Response()
                resp.status_code = 429
                raise requests.exceptions.HTTPError(response=resp)
            return "ok"

        result = retry_on_rate_limit(func, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        def func():
            resp = requests.models.Response()
            resp.status_code = 429
            raise requests.exceptions.HTTPError(response=resp)

        with pytest.raises(requests.exceptions.HTTPError):
            retry_on_rate_limit(func, max_retries=2, base_delay=0.01)

    def test_non_429_error_not_retried(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            resp = requests.models.Response()
            resp.status_code = 500
            raise requests.exceptions.HTTPError(response=resp)

        with pytest.raises(requests.exceptions.HTTPError):
            retry_on_rate_limit(func, max_retries=3, base_delay=0.01)
        assert call_count == 1

    def test_retries_on_connection_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                msg = "Connection reset"
                raise requests.exceptions.ConnectionError(msg)
            return "recovered"

        result = retry_on_rate_limit(func, max_retries=3, base_delay=0.01)
        assert result == "recovered"
        assert call_count == 2

    def test_default_returns_on_failure(self):
        def func():
            resp = requests.models.Response()
            resp.status_code = 429
            raise requests.exceptions.HTTPError(response=resp)

        result = retry_on_rate_limit(func, max_retries=1, base_delay=0.01, default="fallback")
        assert result == "fallback"
