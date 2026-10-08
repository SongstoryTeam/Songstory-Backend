import logging
import time

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 15.0


class ResilientRedisCache(RedisCache):
    def __init__(self, server, params):
        options = dict(params.get("OPTIONS") or {})
        self._cooldown = float(options.pop("cooldown", DEFAULT_COOLDOWN_SECONDS))
        self._suspended_until = 0.0
        super().__init__(server, {**params, "OPTIONS": options})

    def _call(self, operation, fallback, *args, **kwargs):
        if time.monotonic() < self._suspended_until:
            return fallback
        try:
            return getattr(super(), operation)(*args, **kwargs)
        except RedisError as exc:
            self._suspended_until = time.monotonic() + self._cooldown
            logger.warning("Redis cache unavailable (%s); bypassing it for %.0fs", exc, self._cooldown)
            return fallback

    def get(self, key, default=None, version=None):
        return self._call("get", default, key, default, version)

    def get_many(self, keys, version=None):
        return self._call("get_many", {}, keys, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("set", None, key, value, timeout, version)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("set_many", [], data, timeout, version)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("add", True, key, value, timeout, version)

    def incr(self, key, delta=1, version=None):
        return self._call("incr", delta, key, delta, version)

    def has_key(self, key, version=None):
        return self._call("has_key", False, key, version)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("touch", False, key, timeout, version)

    def delete(self, key, version=None):
        return self._call("delete", False, key, version)

    def delete_many(self, keys, version=None):
        return self._call("delete_many", None, keys, version)

    def clear(self):
        return self._call("clear", None)
