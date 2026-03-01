# -*- coding: utf-8 -*-
"""Auto-rotating proxy manager — fetches and tests free proxies at runtime."""

import asyncio
import time
from typing import List, Optional

import aiohttp

# Free public proxy list sources
PROXY_SOURCES = [
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
    "https://vakhov.github.io/fresh-proxy-list/http.txt",
    "https://vakhov.github.io/fresh-proxy-list/socks5.txt",
]

# URL used to test proxies (HTTP for compatibility with simple HTTP proxies)
TEST_URL = "http://httpbin.org/ip"
TEST_TIMEOUT = 5  # seconds
MAX_PROXIES_TO_TEST = 50
MAX_CONCURRENT_TESTS = 20
STALE_AFTER = 15 * 60  # 15 minutes in seconds


class ProxyManager:
    """Fetches, tests and rotates free proxies automatically."""

    def __init__(self):
        self._proxies: List[dict] = []  # list of {"url": str, "ms": float}
        self._failed: set = set()
        self._fetched_at: Optional[float] = None

    async def init(self) -> None:
        """Fetch and test proxies from free lists. Call once at startup."""
        await self._fetch_and_test()

    def get_proxy(self) -> Optional[str]:
        """Return the best (fastest) working proxy URL, or None if unavailable."""
        for entry in self._proxies:
            url = entry["url"]
            if url not in self._failed:
                return url
        return None

    async def mark_failed(self, proxy_url: str) -> None:
        """Mark a proxy as failed so it won't be returned again."""
        self._failed.add(proxy_url)

    async def refresh_if_needed(self) -> None:
        """Re-fetch proxies if all are exhausted or the list is stale (>15 min)."""
        all_exhausted = len(self._proxies) > 0 and all(
            e["url"] in self._failed for e in self._proxies
        )
        stale = (
            self._fetched_at is None
            or (time.monotonic() - self._fetched_at) > STALE_AFTER
        )
        if all_exhausted or stale:
            await self._fetch_and_test()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_proxy_list(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """Download a plain-text proxy list and return individual proxy strings."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                return [line.strip() for line in text.splitlines() if line.strip()]
        except Exception:
            return []

    async def _test_proxy(self, session: aiohttp.ClientSession, proxy_url: str) -> Optional[dict]:
        """Test a single proxy. Returns {"url": ..., "ms": ...} on success or None."""
        start = time.monotonic()
        try:
            async with session.get(
                TEST_URL,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT),
            ) as resp:
                if resp.status == 200:
                    ms = (time.monotonic() - start) * 1000
                    return {"url": proxy_url, "ms": ms}
        except Exception:
            pass
        return None

    async def _fetch_and_test(self) -> None:
        """Download proxy lists and concurrently test up to MAX_PROXIES_TO_TEST."""
        print("[ProxyManager] Fetching proxy lists…")
        raw_proxies: List[str] = []

        async with aiohttp.ClientSession() as session:
            lists = await asyncio.gather(
                *[self._fetch_proxy_list(session, src) for src in PROXY_SOURCES]
            )

        for lst in lists:
            raw_proxies.extend(lst)

        # Normalise: keep entries that already have a scheme, add http:// otherwise
        # HTTP proxies come first (preferred over SOCKS5)
        http_proxies = []
        socks_proxies = []
        for p in raw_proxies:
            if p.startswith("socks"):
                socks_proxies.append(p)
            elif p.startswith("http"):
                http_proxies.append(p)
            else:
                http_proxies.append(f"http://{p}")

        candidates = (http_proxies + socks_proxies)[:MAX_PROXIES_TO_TEST]
        print(f"[ProxyManager] Testing {len(candidates)} proxies…")

        # Test in batches of MAX_CONCURRENT_TESTS
        results = []
        for i in range(0, len(candidates), MAX_CONCURRENT_TESTS):
            batch = candidates[i : i + MAX_CONCURRENT_TESTS]
            async with aiohttp.ClientSession() as session:
                batch_results = await asyncio.gather(
                    *[self._test_proxy(session, p) for p in batch]
                )
            results.extend(batch_results)

        working = [r for r in results if r is not None]
        # Sort by response time (fastest first)
        working.sort(key=lambda x: x["ms"])

        self._proxies = working
        self._failed = set()
        self._fetched_at = time.monotonic()

        if working:
            best = working[0]
            print(
                f"[ProxyManager] {len(working)} working proxies found. "
                f"Best: {best['url']} ({best['ms']:.0f}ms)"
            )
        else:
            print("[ProxyManager] No working proxies found — parsers will run without proxy")


proxy_manager = ProxyManager()
