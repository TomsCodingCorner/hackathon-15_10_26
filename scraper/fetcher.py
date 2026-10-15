"""Seriële HTTP-verzoeken; geen browser-, authenticatie- of blokkadeomzeiling."""

import math
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .models import ORIGIN

USER_AGENT = "MinorHackathonScraper/0.1 (educational prototype)"


class FetchError(RuntimeError):
    def __init__(self, code: str, url: str, status: int | None = None):
        super().__init__(code)
        self.code, self.url, self.status = code, url, status


@dataclass
class FetchStats:
    pages_requested: int = 0
    pages_succeeded: int = 0


class Fetcher:
    def __init__(self, delay: float = 1.5, timeout: float = 20, retries: int = 2):
        if not math.isfinite(delay) or not math.isfinite(timeout) or delay < 0 or timeout <= 0 or not 0 <= retries <= 3:
            raise ValueError("Ongeldige delay, timeout of retries.")
        self.delay, self.timeout, self.retries = delay, timeout, retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.stats = FetchStats()
        self.robots: RobotFileParser | None = None
        self.last_request: float | None = None

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _allowed_origin(url: str) -> bool:
        try:
            parts = urlsplit(url)
            return (
                parts.scheme == "https" and parts.hostname == "www.kiesopmaat.nl"
                and not parts.username and not parts.password and parts.port in (None, 443)
            )
        except ValueError:
            return False

    def _request(self, url: str, *, check_robots: bool = True) -> str:
        # Redirects worden eerst gecontroleerd, voordat hun doel wordt opgevraagd.
        for redirect in range(4):
            if not self._allowed_origin(url):
                raise FetchError("disallowed_origin", ORIGIN)
            if check_robots and (self.robots is None or not self.robots.can_fetch(USER_AGENT, url)):
                raise FetchError("robots_denied_or_unavailable", url)
            response = None
            for attempt in range(self.retries + 1):
                if self.last_request is not None:
                    time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
                self.last_request = time.monotonic()
                self.stats.pages_requested += 1
                try:
                    response = self.session.get(url, timeout=self.timeout, allow_redirects=False)
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == self.retries:
                        raise FetchError("network_error_or_timeout", url) from None
                    continue
                except requests.RequestException:
                    raise FetchError("request_error", url) from None
                if response.status_code in (401, 403, 429):
                    response.close()
                    raise FetchError("access_restricted", url, response.status_code)
                if response.status_code in (500, 502, 503, 504) and attempt < self.retries:
                    response.close()
                    continue
                break
            assert response is not None
            try:
                if response.status_code in (301, 302, 303, 307, 308):
                    target = response.headers.get("Location")
                    if not target:
                        raise FetchError("invalid_redirect", url, response.status_code)
                    url = urljoin(url, target)
                    continue
                if not 200 <= response.status_code < 300:
                    raise FetchError("http_error", url, response.status_code)
                self.stats.pages_succeeded += 1
                text = response.text
                if "verifying your browser" in text.lower() or "<title>captcha" in text.lower():
                    raise FetchError("browser_challenge", url, response.status_code)
                return text
            finally:
                response.close()
        raise FetchError("too_many_redirects", url)

    def load_robots(self) -> None:
        url = ORIGIN + "/robots.txt"
        text = self._request(url, check_robots=False)
        if not any(line.lower().startswith("user-agent:") for line in text.splitlines()):
            raise FetchError("invalid_robots", url)
        parser = RobotFileParser(url)
        parser.parse(text.splitlines())
        self.robots = parser
        self.delay = max(self.delay, float(parser.crawl_delay(USER_AGENT) or 0))

    def get(self, url: str) -> str:
        return self._request(url)
