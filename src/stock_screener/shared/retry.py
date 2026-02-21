from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SENTINEL = object()


def retry_on_rate_limit[T](
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    default: Any = _SENTINEL,
) -> T:
    """Execute func with exponential backoff on rate-limit (429) and connection errors.

    Args:
        func: Zero-argument callable to execute.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubled each retry).
        default: If provided, return this value instead of raising on final failure.

    Returns:
        The return value of func.

    Raises:
        The last exception if max_retries exceeded and no default is set.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.info("Rate limited, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, max_retries)
                    time.sleep(delay)
                    continue
            else:
                if default is not _SENTINEL:
                    return default  # type: ignore[return-value]
                raise
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.info("Connection error, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, max_retries)
                time.sleep(delay)
                continue

    if default is not _SENTINEL:
        return default  # type: ignore[return-value]
    raise last_exception  # type: ignore[misc]
