import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import httpx

DEFAULT_USER_AGENT = "LeadShark/1.0 (+https://leadshark.io; compliance@leadshark.io)"


class TTLCache:
    """Thread-safe in-memory TTL cache for external discovery queries."""

    def __init__(self, ttl_seconds: int = 600, max_size: int = 250):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if now >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        now = time.monotonic()
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        with self._lock:
            if len(self._store) >= self.max_size:
                # Evict oldest entry
                oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
                del self._store[oldest_key]
            self._store[key] = (now + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class ProviderRateLimiter:
    """Tracks per-provider rate-limit cooldowns and minimum request intervals."""

    def __init__(self):
        self._cooldowns: Dict[str, float] = {}
        self._last_call: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_rate_limited(self, provider: str) -> Tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            until = self._cooldowns.get(provider, 0.0)
            if now < until:
                return True, round(until - now, 1)
            return False, 0.0

    def mark_rate_limited(self, provider: str, retry_after_seconds: float = 30.0) -> None:
        with self._lock:
            self._cooldowns[provider] = time.monotonic() + max(5.0, min(retry_after_seconds, 120.0))

    def throttle(self, provider: str, min_interval: float = 0.0) -> None:
        if min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            last = self._last_call.get(provider, 0.0)
            wait = min_interval - (now - last)
            if wait > 0:
                time.sleep(min(wait, 1.5))
            self._last_call[provider] = time.monotonic()


@dataclass
class HttpResponseResult:
    ok: bool
    status_code: int
    data: Optional[Any] = None
    text: str = ""
    error: Optional[str] = None
    rate_limited: bool = False
    timed_out: bool = False


_rate_limiter = ProviderRateLimiter()
_discovery_cache = TTLCache(ttl_seconds=600, max_size=300)


def get_discovery_cache() -> TTLCache:
    return _discovery_cache


def get_rate_limiter() -> ProviderRateLimiter:
    return _rate_limiter


def request_with_retry(
    provider: str,
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 8.0,
    max_retries: int = 2,
    min_interval: float = 0.0,
    expect_json: bool = True,
) -> HttpResponseResult:
    """
    Executes an HTTP request with rate-limit awareness, timeouts, and exponential backoff retries.
    Never fails silently on 429 or timeouts; reports structured diagnostics.
    """
    limited, remaining = _rate_limiter.is_rate_limited(provider)
    if limited:
        return HttpResponseResult(
            ok=False,
            status_code=429,
            error=f"Provider '{provider}' rate-limit cooldown active ({remaining}s remaining)",
            rate_limited=True,
        )

    req_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json" if expect_json else "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        req_headers.update(headers)

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            _rate_limiter.throttle(provider, min_interval=min_interval)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.request(
                    method.upper(),
                    url,
                    params=params,
                    data=data,
                    json=json_body,
                    headers=req_headers,
                )

            if resp.status_code == 429:
                retry_after = 30.0
                try:
                    retry_after = float(resp.headers.get("Retry-After", "30"))
                except ValueError:
                    retry_after = 30.0
                _rate_limiter.mark_rate_limited(provider, retry_after)
                if attempt < max_retries and retry_after <= 2.5:
                    time.sleep(retry_after)
                    continue
                return HttpResponseResult(
                    ok=False,
                    status_code=429,
                    error=f"HTTP 429 Rate Limit from {provider} (Retry-After: {retry_after}s)",
                    rate_limited=True,
                )

            if resp.status_code in (502, 503, 504):
                last_err = f"HTTP {resp.status_code} upstream gateway/capacity error from {provider}"
                if attempt < max_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return HttpResponseResult(
                    ok=False,
                    status_code=resp.status_code,
                    error=last_err,
                    timed_out=(resp.status_code == 504),
                )

            if resp.status_code >= 400:
                return HttpResponseResult(
                    ok=False,
                    status_code=resp.status_code,
                    text=resp.text[:300],
                    error=f"HTTP {resp.status_code} from {provider}",
                )

            if expect_json:
                try:
                    parsed = resp.json()
                    return HttpResponseResult(ok=True, status_code=resp.status_code, data=parsed, text=resp.text)
                except Exception as exc:
                    return HttpResponseResult(
                        ok=False,
                        status_code=resp.status_code,
                        text=resp.text[:300],
                        error=f"Invalid JSON from {provider}: {exc}",
                    )
            return HttpResponseResult(ok=True, status_code=resp.status_code, text=resp.text)

        except (httpx.TimeoutException, TimeoutError) as exc:
            last_err = f"Timeout after {timeout}s contacting {provider}: {exc}"
            if attempt < max_retries:
                time.sleep(0.4 * (2 ** attempt))
                continue
            return HttpResponseResult(ok=False, status_code=0, error=last_err, timed_out=True)
        except Exception as exc:
            last_err = f"Network error contacting {provider}: {exc}"
            if attempt < max_retries:
                time.sleep(0.4 * (2 ** attempt))
                continue
            return HttpResponseResult(ok=False, status_code=0, error=last_err)

    return HttpResponseResult(ok=False, status_code=0, error=last_err or "Unknown request error")
