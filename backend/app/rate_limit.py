from __future__ import annotations

import os
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional


@dataclass
class _Window:
    start: float
    count: int


_TRUST_PROXY = os.getenv("HELIX_TRUST_PROXY", "").strip().lower() in {"1", "true", "yes", "on"}
# Hard cap on tracked keys so a client spraying unique identifiers cannot grow
# the in-memory map without bound.
_MAX_KEYS = 100_000


def client_ip(request) -> str:
    """Return the client address used to key rate limits.

    By default this is the transport peer address (``request.client.host``),
    which cannot be spoofed by the client. ``X-Forwarded-For`` is only honored
    when ``HELIX_TRUST_PROXY`` is explicitly set to a truthy value, i.e. when
    Helix is run behind a reverse proxy that is trusted to set the header.
    """
    if _TRUST_PROXY and request is not None:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    try:
        client = getattr(request, "client", None)
        return (getattr(client, "host", "") or "") if client else ""
    except Exception:
        return ""


class FixedWindowRateLimiter:
    """Simple in-process fixed-window rate limiter.

    This is intentionally lightweight (no Redis). It limits abuse in a single-worker
    deployment and provides a baseline even when multiple workers are used.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: "OrderedDict[str, _Window]" = OrderedDict()

    def allow(self, key: str, *, limit: int, window_s: int) -> bool:
        now = time.time()
        window_s = max(1, int(window_s))
        limit = max(1, int(limit))
        k = key or ""
        if not k:
            return True
        with self._lock:
            w = self._buckets.get(k)
            if w is not None:
                # Most-recently-used bookkeeping.
                self._buckets.move_to_end(k)
            if not w or (now - w.start) >= window_s:
                self._buckets[k] = _Window(start=now, count=1)
            else:
                if w.count >= limit:
                    return False
                w.count += 1
            # Opportunistic cleanup: expire old windows, then LRU-evict the
            # oldest keys if the map has grown too large.
            if len(self._buckets) > 10000:
                self._prune_locked(now, window_s * 4)
            if len(self._buckets) > _MAX_KEYS:
                self._buckets.popitem(last=False)
            return True

    def _prune_locked(self, now: float, max_age_s: int) -> None:
        dead = []
        for k, w in self._buckets.items():
            if (now - w.start) > max_age_s:
                dead.append(k)
        for k in dead:
            self._buckets.pop(k, None)


RATE_LIMITER = FixedWindowRateLimiter()


def make_key(*, scope: str, user_id: Optional[str], ip: str) -> str:
    scope = (scope or "").strip()
    uid = (user_id or "").strip()
    ip = (ip or "").strip()
    # Prefer user id; fall back to IP (still useful for unauth endpoints).
    ident = uid or ip or "anon"
    return f"{scope}:{ident}"
