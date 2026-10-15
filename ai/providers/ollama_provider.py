"""Ollama REST API op loopback; geen proxy, redirects, cloud of downloads."""

from urllib.parse import urlsplit

import requests

from . import ProviderError


class OllamaProvider:
    def __init__(self, url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:3b", timeout: float = 60):
        parts = urlsplit(url)
        if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parts.username or parts.password or parts.path not in {"", "/"} or parts.query or parts.fragment):
            raise ValueError("Ollama moet een HTTP-loopbackadres gebruiken.")
        if not model.strip() or "cloud" in model.lower() or not 0 < timeout <= 120:
            raise ValueError("Gebruik een lokaal model en een timeout van maximaal 120 seconden.")
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    def _request(self, method: str, route: str, **kwargs) -> dict:
        try:
            with requests.Session() as session:
                session.trust_env = False
                response = session.request(method, self.url + route, timeout=self.timeout,
                                           allow_redirects=False, **kwargs)
                try:
                    if response.status_code == 404:
                        raise ProviderError("model_missing")
                    if response.status_code != 200:
                        raise ProviderError("ollama_http_error")
                    result = response.json()
                    if not isinstance(result, dict):
                        raise ProviderError("ollama_invalid_response")
                    return result
                finally:
                    response.close()
        except requests.Timeout:
            raise ProviderError("ollama_timeout") from None
        except requests.RequestException:
            raise ProviderError("ollama_unreachable") from None
        except ValueError:
            raise ProviderError("ollama_invalid_response") from None

    def models(self) -> list[str]:
        rows = self._request("GET", "/api/tags").get("models")
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in rows):
            raise ProviderError("ollama_invalid_response")
        return [row["name"] for row in rows]

    def generate(self, payload: str, schema: dict, system_prompt: str) -> str:
        result = self._request("POST", "/api/generate", json={
            "model": self.model, "prompt": payload, "system": system_prompt,
            "format": schema, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 1800, "num_ctx": 8192},
        })
        if result.get("done") is not True or not isinstance(result.get("response"), str):
            raise ProviderError("ollama_invalid_response")
        return result["response"]
