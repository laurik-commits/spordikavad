"""Ühine HTTP-kiht: viisakas User-Agent, paus päringute vahel, ajapiirang ja kordused.

Ainult standardteek, väliseid sõltuvusi pole.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

log = logging.getLogger(__name__)


class FetchError(Exception):
    """Lehte ei õnnestunud alla laadida ka pärast kordusi."""


class Fetcher:
    def __init__(
        self,
        user_agent: str,
        *,
        delay: float = 3.0,
        host_delays: dict[str, float] | None = None,
        timeout: float = 20.0,
        retries: int = 3,
        backoff: float = 5.0,
        sleep=time.sleep,
        clock=time.monotonic,
        opener=urllib.request.urlopen,
    ) -> None:
        self.user_agent = user_agent
        self.delay = delay
        self.host_delays = host_delays or {}
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._sleep = sleep
        self._clock = clock
        self._open = opener
        self._last: dict[str, float] = {}

    def _wait_for(self, host: str) -> None:
        gap = self.host_delays.get(host, self.delay)
        last = self._last.get(host)
        if last is not None:
            remaining = gap - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()

    def get(self, url: str) -> str:
        """Tagastab lehe teksti. Viskab FetchError, kui kõik katsed ebaõnnestuvad."""
        host = urlsplit(url).hostname or ""
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept-Language": "et,en"})
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._wait_for(host)
            try:
                with self._open(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    charset = resp.headers.get_content_charset() or "utf-8"
                    return raw.decode(charset, errors="replace")
            except urllib.error.HTTPError as e:
                last_error = e
                # 4xx (v.a 429) ei parane kordamisest
                if 400 <= e.code < 500 and e.code != 429:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = e
            log.warning("%s: katse %d/%d ebaõnnestus: %s", url, attempt, self.retries, last_error)
            if attempt < self.retries:
                self._sleep(self.backoff * attempt)
        raise FetchError(f"{url}: {last_error}")
