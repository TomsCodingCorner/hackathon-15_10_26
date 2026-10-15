"""Normalisatie van scraperdata en onafhankelijke controle van modeloutput."""

import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


FIELD_ALIASES = {
    "id": ("id", "minor_id", "code"),
    "title": ("title", "titel", "name", "naam"),
    "description": ("description", "beschrijving", "summary"),
    "institution": ("institution", "institution_name", "instelling", "aanbieder", "hogeschool"),
    "url": ("url", "link", "detail_url"),
}


class ValidationError(ValueError):
    """Ongeldige invoer/output; foutteksten bevatten geen aangeleverde data."""


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Een verplicht tekstveld ontbreekt.")
    parser = _PlainText()
    try:
        parser.feed(value)
        parser.close()
    except (AssertionError, ValueError) as exc:
        raise ValidationError("Een tekstveld bevat ongeldige HTML.") from exc
    return " ".join(" ".join(parser.parts).split())


def normalize_minors(minors: object) -> list[dict[str, str]]:
    """Accepteer een lijst, JSON-string of wrapper met minors/results/data.

    Vereist alle vijf bronvelden; genereert geen ID's of inhoud. Bij één
    ongeldige rij of dubbel ID wordt de dataset afgewezen, nooit stil aangepast.
    """
    if isinstance(minors, str):
        try:
            minors = json.loads(minors)
        except (ValueError, RecursionError) as exc:
            raise ValidationError("De dataset is geen geldige JSON.") from exc
    if isinstance(minors, dict):
        wrappers = [key for key in ("minors", "results", "data") if key in minors]
        if len(wrappers) != 1:
            raise ValidationError("Gebruik één datasetlijst.")
        minors = minors[wrappers[0]]
    if not isinstance(minors, list):
        raise ValidationError("De dataset moet een lijst zijn.")

    normalized = []
    seen = set()
    for row in minors:
        if not isinstance(row, dict):
            raise ValidationError("Elke minor moet een object zijn.")
        minor = {}
        for field, aliases in FIELD_ALIASES.items():
            values = [row[key] for key in aliases if key in row and row[key] is not None]
            if not values or any(value != values[0] for value in values):
                raise ValidationError("Een bronveld ontbreekt of heeft conflicterende aliassen.")
            value = values[0]
            if field == "id":
                if type(value) is int:
                    value = str(value)
                if not isinstance(value, str) or not value.strip():
                    raise ValidationError("Een minor-ID moet tekst of een geheel getal zijn.")
                minor[field] = value.strip()
            elif field == "url":
                if not isinstance(value, str) or not value.strip():
                    raise ValidationError("Een minor-URL ontbreekt.")
                try:
                    url = urljoin("https://www.kiesopmaat.nl/", value.strip())
                    parts = urlsplit(url)
                    valid = (
                        parts.scheme in ("http", "https") and parts.hostname
                        and not parts.username and not parts.password
                    )
                    # Het uitlezen valideert ook ongeldige of te grote poorten.
                    parts.port
                except ValueError as exc:
                    raise ValidationError("Een minor-URL is ongeldig.") from exc
                if not valid or any(char.isspace() for char in value):
                    raise ValidationError("Een minor-URL moet een HTTP(S)-link zijn.")
                minor[field] = url
            else:
                minor[field] = _text(value)
                if not minor[field]:
                    raise ValidationError("Een verplicht tekstveld is leeg.")
        if minor["id"] in seen:
            raise ValidationError("Dubbel minor-ID in dataset.")
        seen.add(minor["id"])
        normalized.append(minor)
    return normalized


def validate_recommendations(output: object, minors: list[dict], user_messages: list[str]) -> dict:
    """Controleer structuur, ID's, aantallen en letterlijke brononderbouwing.

    Eén fout maakt de volledige modeloutput ongeldig, zodat ook bij gemengde
    geldige/ongeldige resultaten geen ongecontroleerde tekst naar de UI gaat.
    """
    if not isinstance(output, dict) or set(output) != {"action", "question_topic", "recommendations"}:
        raise ValidationError("Onjuist outputschema.")
    action, topic, recommendations = output["action"], output["question_topic"], output["recommendations"]
    if action not in ("ask", "recommend", "refer") or topic not in ("study", "interests", "preferences", "none"):
        raise ValidationError("Onbekende actie of vraagcategorie.")
    if not isinstance(recommendations, list) or len(recommendations) > 3:
        raise ValidationError("Maximaal drie aanbevelingen toegestaan.")
    if action == "ask":
        if topic == "none" or recommendations:
            raise ValidationError("Een vraag mag geen aanbevelingen bevatten.")
    elif topic != "none" or (action == "recommend") != bool(recommendations):
        raise ValidationError("Actie en aanbevelingen spreken elkaar tegen.")

    by_id = {minor["id"]: minor for minor in minors}
    seen = set()
    for recommendation in recommendations:
        if not isinstance(recommendation, dict) or set(recommendation) != {"minor_id", "student_quote", "description_quote"}:
            raise ValidationError("Onjuiste aanbevelingsstructuur.")
        minor_id = recommendation["minor_id"]
        if not isinstance(minor_id, str) or minor_id not in by_id or minor_id in seen:
            raise ValidationError("Onbekend of dubbel aanbevolen minor-ID.")
        seen.add(minor_id)
        for field, minimum, maximum in (("student_quote", 3, 160), ("description_quote", 10, 350)):
            quote = recommendation[field]
            if not isinstance(quote, str) or not minimum <= len(quote.strip()) <= maximum:
                raise ValidationError("Ongeldig bronfragment.")
        if not any(recommendation["student_quote"] in text for text in user_messages):
            raise ValidationError("Interesse komt niet uit een studentantwoord.")
        if recommendation["description_quote"] not in by_id[minor_id]["description"]:
            raise ValidationError("Onderbouwing komt niet uit deze minorbeschrijving.")
    return output
