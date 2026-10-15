# Requirements traceability â€” Gemini-update, 15 oktober 2026

De nieuwste instructie vervangt de eerdere voorkeur voor uitsluitend lokale AI:
de app gebruikt GEMINI_API_KEY en GEMINI_MODEL via Google Gemini.
STT/TTS en webserver blijven lokaal. Code, mocks en live bewijs staan apart.

| Requirement | Implementatie / bewijs | Stand |
| --- | --- | --- |
| Streamlit start | app.py, scripts/start.ps1; serverstart op 127.0.0.1:8502, AppTest | Bewezen |
| Chatbot en Diagnostics | Twee pagina's, Gemini-status/disclosure en zeven tabs | AppTest geslaagd |
| OfficiÃ«le Gemini SDK | google-genai-provider, JSON-schema, timeout, client sluiten | SDK-mocks + SDK met MockTransport; technische live JSON-proef PASS |
| Key/model configuratie | Automatische .env, omgevingsvoorrang, key verborgen | Unit-/AppTest; eigen key gevonden zonder waarde te tonen |
| Geen Ollama nodig | App, dashboard en scripts gebruiken Gemini | Offline getest; oude adapter alleen compatibiliteit |
| Tekstchat/context/correcties | run_turn en chat_with_agent | Offline bewezen; volledig live schema HTTP 503 |
| Maximaal drie geldige bronkaarten | Enum-kandidaten, JSON/ID/quotevalidatie en vaste renderer | Offline bewezen; echte dataset ontbreekt |
| Nederlandse STT | faster-whisper CPU/int8, local_files_only, language=nl | Mocks; modelbestanden gevonden, functie NOT_TESTED |
| Nederlandse TTS | Piper, lokale Nederlandse stem, WAV-validatie | Mocks; stem ontbreekt, live BLOCKED |
| Microfoon/historie/reset | audio_input, Session State, idempotente event-IDs | UI geÃ¯ntegreerd; tekstvolgorde/reset getest; microfoon nog live testen |
| Lege/ongeldige data | Loader, dataset_check en gecontroleerde fallback | Unit-/AppTest; geen fictieve chatbotcatalogus |
| Eerlijke fouten | Readiness apart; auth/model/quota/503 BLOCKED; downstream NOT_TESTED | Unit tests; 503 live waargenomen |
| Testdashboard | Expliciete Gemini-proef, STT/TTS, scenario's, ketentrace, pytest-worker | AppTest; geen automatische API-proef bij openen |
| Offline tests | conftest blokkeert requests/httpx-netwerk | 156 tests + 37 subtests geslaagd |
| Scraper en echte records | Fetcher/loader/opslag behouden; parser onvoltooid | Historisch HTTP 401, 0 records; geen nieuwe scrape |
| Privacy | Google-disclosure, key verborgen, geen permanente chat/audio | Tests voor logging/redactie; geen automatische PII-redactie |
| Windows-installatie | start.ps1, README; bestaande .env behouden, geen modeldownloads | PS-syntax en -SkipInstall-start getest |
| Volledige live audioketen | Controller integreert alle stappen | Mockintegratie geslaagd; echte keten NOT_TESTED |

## Behouden contracten en gewijzigde eisen

- chat_with_agent(message, history, minors) houdt response,
  recommended_minor_ids en needs_more_info. provider= blijft optioneel.
- Nederlandse prompt, bronquotes, beperkte vervolgvragen en menselijke
  doorverwijzing blijven behouden. Ongeldige output geeft geen gedeeltelijk advies.
- De eerdere eis geen externe AI / geen verplichte API-key is door de expliciete
  Gemini-keuze vervangen. Antwoorden vereisen key, internet en quota; geen
  kosteloosheidsgarantie.
- Geen fictieve data in de functionele chatbot. De geÃ¯soleerde live schemaproef
  gebruikte alleen herkenbare unit-testfixtures, zonder bestanden te wijzigen.
- Oude Ollama-adapter en regressietests behouden; geen onderdeel van de app.

Zie [TEST_REPORT](TEST_REPORT.md) voor uitvoeringen en beperkingen.
