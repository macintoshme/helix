"""Unit tests for security-relevant logic, run under the pinned dependencies.

The password round-trip specifically exercises the passlib 1.7.4 + bcrypt 4.0.1
combination chosen for M-6 (bcrypt was held at 4.0.1 for passlib compatibility),
so a future incompatible bcrypt bump fails here immediately instead of at runtime.
"""
from app.rate_limit import FixedWindowRateLimiter, make_key
from app.security import hash_password, verify_password

_PW = "correct-horse-battery-staple"


def test_password_roundtrip():
    hashed = hash_password(_PW)
    assert verify_password(_PW, hashed) is True


def test_password_wrong_value_rejected():
    hashed = hash_password(_PW)
    assert verify_password("not-the-password", hashed) is False


def test_password_hash_is_bcrypt():
    hashed = hash_password("hello")
    assert hashed.startswith("$bcrypt-sha256$"), hashed


def test_rate_limiter_enforces_limit():
    limiter = FixedWindowRateLimiter()
    assert limiter.allow("k", limit=2, window_s=60) is True
    assert limiter.allow("k", limit=2, window_s=60) is True
    assert limiter.allow("k", limit=2, window_s=60) is False


def test_rate_limiter_empty_key_always_allowed():
    limiter = FixedWindowRateLimiter()
    assert all(limiter.allow("", limit=1, window_s=60) for _ in range(5))


def test_make_key_prefers_user_id_over_ip():
    assert make_key(scope="login", user_id="u1", ip="1.2.3.4") == "login:u1"
    assert make_key(scope="login", user_id="", ip="1.2.3.4") == "login:1.2.3.4"
    assert make_key(scope="login", user_id="", ip="") == "login:anon"
