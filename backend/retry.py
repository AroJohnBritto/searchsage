import functools
import logging
import time

from backend.errors import ConfigError, ProviderError

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 8.0):
    """Retry a function on ProviderError with exponential backoff.

    ConfigError is never retried, it propagates immediately so the caller can
    fall through to the next tier without wasting time.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except ConfigError:
                    raise
                except ProviderError as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.warning(
                            "%s failed after %s attempts, giving up. %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    logger.info(
                        "%s failed on attempt %s, retrying in %.1fs. %s",
                        func.__name__,
                        attempt,
                        delay,
                        exc,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
