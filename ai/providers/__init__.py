"""Providers voor gestructureerde modeloutput."""

from typing import Protocol


class Provider(Protocol):
    def generate(self, payload: str, schema: dict, system_prompt: str) -> str: ...


class ProviderError(RuntimeError):
    """Veilige foutcode zonder prompt, response of netwerkexceptiontekst."""


ERROR_MESSAGES = {
    "gemini_unavailable": "Google Gemini is tijdelijk niet beschikbaar (HTTP 503). Probeer het later opnieuw.",
    "gemini_invalid_request": "Gemini accepteert de aanvraag niet (HTTP 400). Controleer het model en de SDK-configuratie.",
    "missing_api_key": "GEMINI_API_KEY ontbreekt. Stel deze in via .env of een omgevingsvariabele.",
    "missing_model": "GEMINI_MODEL ontbreekt. Configureer een Gemini-model met JSON-schema-ondersteuning.",
    "invalid_provider_config": "De Gemini-providerconfiguratie is ongeldig.",
    "gemini_auth_error": "Gemini heeft de toegang geweigerd. Controleer de API-key en de rechten van het project.",
    "gemini_model_not_found": "Het ingestelde Gemini-model is niet gevonden of niet toegankelijk. Controleer GEMINI_MODEL.",
    "gemini_rate_limited": "De Gemini-limiet of het quota is bereikt. Controleer het API-project en probeer het later opnieuw.",
    "gemini_timeout": "Gemini antwoordde niet binnen de ingestelde timeout. Probeer het later opnieuw.",
    "gemini_unreachable": "Gemini is niet bereikbaar. Controleer de internetverbinding.",
    "gemini_empty_output": "Gemini gaf geen bruikbare tekst terug. Het antwoord kan zijn geblokkeerd of afgebroken.",
    "gemini_api_error": "De Gemini-aanroep is mislukt. Controleer de configuratie in Diagnostics.",
    "api_error": "De AI-dienst kon geen antwoord geven. Controleer Diagnostics.",
    # Bestaande expliciet geïnjecteerde adapters blijven compatibel.
    "model_missing": "Het model ontbreekt.",
    "ollama_timeout": "De modelaanroep duurde te lang.",
    "ollama_unreachable": "De modelserver is niet bereikbaar.",
    "ollama_http_error": "De modelserver gaf een fout terug.",
    "ollama_invalid_response": "De modelserver gaf een ongeldig antwoord terug.",
}
