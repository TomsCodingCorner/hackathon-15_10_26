"""Uitvoercontract, los van frontend en AI-agent."""

import hashlib
from urllib.parse import urljoin, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

SOURCE = "https://www.kiesopmaat.nl/modules/"
ORIGIN = "https://www.kiesopmaat.nl"


def canonical_url(value: str, base: str = SOURCE) -> str:
    """Alleen echte productie-detail-URL's; query/fragment zijn geen identiteit."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Bron-URL ontbreekt.")
    if any(char.isspace() for char in value):
        raise ValueError("Bron-URL bevat witruimte.")
    parts = urlsplit(urljoin(base, value))
    if (
        parts.scheme != "https" or parts.hostname != "www.kiesopmaat.nl"
        or parts.username or parts.password or parts.port not in (None, 443)
        or not parts.path.startswith("/modules/") or parts.path == "/modules/"
    ):
        raise ValueError("Geen HTTPS-detail-URL op de productieomgeving.")
    path = parts.path.rstrip("/") + "/"
    return urlunsplit(("https", "www.kiesopmaat.nl", path, "", ""))


def stable_id(url: str) -> str:
    return "kom-" + hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()[:24]


class Minor(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    id: str
    title: str
    institution: str
    description: str
    url: str
    language: str | None = None
    credits: str | None = None
    study_format: str | None = None
    location: str | None = None
    period: str | None = None
    requirements: str | None = None

    @field_validator("id", "title", "institution", "description")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value or value.casefold() in {"n/a", "onbekend", "geen informatie", "-"}:
            raise ValueError("Verplicht bronveld ontbreekt.")
        return value

    @field_validator("description")
    @classmethod
    def useful_description(cls, value: str) -> str:
        if len(value) < 30 or len(value.split()) < 5:
            raise ValueError("Beschrijving is te kort voor bruikbaar advies.")
        return value

    @field_validator("url")
    @classmethod
    def source_url(cls, value: str) -> str:
        return canonical_url(value)

    @field_validator("language", "credits", "study_format", "location", "period", "requirements")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split()) or None

    @model_validator(mode="after")
    def check_id(self) -> "Minor":
        if self.id != stable_id(self.url):
            raise ValueError("ID moet bij de canonieke bron-URL horen.")
        return self
