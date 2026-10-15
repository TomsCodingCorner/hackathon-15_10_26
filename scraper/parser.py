"""Veilige parsergrens; de productie-modulemarkup is nog NIET toegankelijk.

Er staan bewust geen verzonnen Kies op Maat-selectors in deze module.
De homepage en een browserchallenge zijn geen minorbronnen.
"""

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

class SourceStructureUnavailable(ValueError):
    pass


@dataclass
class Listing:
    detail_urls: list[str]
    next_url: str | None = None


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True).replace("\u200b", "").replace("\ufeff", "")
    return " ".join(text.split())


def absolute_url(url: str, page_url: str) -> str:
    return urljoin(page_url, url)


def _unavailable(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    if "verifying your browser" in title or "captcha" in title:
        raise SourceStructureUnavailable("browser_challenge_is_not_minor_data")
    raise SourceStructureUnavailable("production_module_layout_not_verified")


def parse_listing(html: str, page_url: str) -> Listing:
    """Nog niet implementeerbaar: overzicht en paginering zijn niet ingezien."""
    _unavailable(html)


def parse_detail(html: str, page_url: str) -> dict:
    """Nog niet implementeerbaar: echte detail-HTML ontbreekt."""
    _unavailable(html)
