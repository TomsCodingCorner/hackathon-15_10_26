"""Gemini Developer API via de officiële google-genai SDK."""

import os

import httpx
from google import genai
from google.genai import types

from config import DEFAULT_GEMINI_MODEL
from . import ProviderError

DEFAULT_MODEL = DEFAULT_GEMINI_MODEL


class GeminiProvider:
    """Sleutel blijft privé; fouten bevatten alleen vaste foutcodes.

    Er wordt pas een client/netwerkverzoek aangemaakt bij generate(). Eén poging
    per aanroep, zodat quota-/authenticatiefouten geen retry-lus veroorzaken.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 30,
                 max_output_tokens: int = 4096):
        key = api_key if api_key is not None else (os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip())
        if not isinstance(key, str) or not key.strip():
            raise ProviderError("missing_api_key")
        model = model if model is not None else (os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL)
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("missing_model")
        if not 0 < timeout <= 120 or not 1 <= max_output_tokens <= 8192:
            raise ProviderError("invalid_provider_config")
        self._api_key = key.strip()
        self.model = model.strip().removeprefix("models/")
        self.timeout, self.max_output_tokens = timeout, max_output_tokens

    def generate(self, payload: str, schema: dict, system_prompt: str) -> str:
        try:
            with genai.Client(
                api_key=self._api_key, vertexai=False, enterprise=False,
                http_options=types.HttpOptions(
                    base_url="https://generativelanguage.googleapis.com",
                    timeout=int(self.timeout * 1000), retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ) as client:
                completion = client.models.generate_content(
                    model=self.model, contents=payload,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json", response_json_schema=schema,
                        temperature=0.2, max_output_tokens=self.max_output_tokens,
                    ),
                )
                text = completion.text
                if not isinstance(text, str) or not text.strip():
                    raise ProviderError("gemini_empty_output")
                return text
        except ProviderError:
            raise
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderError("gemini_timeout") from None
        except httpx.NetworkError:
            raise ProviderError("gemini_unreachable") from None
        except Exception as exc:
            code = getattr(exc, "code", None)
            category = {400: "gemini_invalid_request", 401: "gemini_auth_error", 403: "gemini_auth_error",
                        404: "gemini_model_not_found", 429: "gemini_rate_limited",
                        503: "gemini_unavailable"}.get(code, "gemini_api_error")
            raise ProviderError(category) from None
