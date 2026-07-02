"""Shared Redis connection helper.

All Redis connections should use get_redis() from this module
instead of hardcoding host/port.
"""
import logging

logger = logging.getLogger(__name__)


def get_redis(db: int = 0, socket_timeout: int = 3, decode: bool = True):
    """Return a Redis connection configured from conf.env.

    Args:
        db: Redis database number (default 0).
        socket_timeout: Connection timeout in seconds (default 3).
        decode: Decode responses as strings (default True).

    Usage:
        r = get_redis()
        r.set('key', 'value')
        r.get('key')  # -> 'value'
    """
    from django.conf import settings
    import redis

    host = getattr(settings, 'REDIS_HOST', '127.0.0.1')
    port = getattr(settings, 'REDIS_PORT', 6379)

    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 6379

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        socket_connect_timeout=socket_timeout,
        decode_responses=decode,
    )
