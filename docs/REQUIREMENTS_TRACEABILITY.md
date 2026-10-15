# Requirements traceability — lokale Streamlit-opdracht

Bijgewerkt op 15 oktober 2026. Eerdere AI-/scraperinterfaces en tests zijn behouden.
Gerealiseerde code, offline mocks en live bewijs worden expliciet onderscheiden.

| DoD / requirement | Implementatie en bewijs | Stand |
| --- | --- | --- |
| 1. Streamlit start lokaal | app.py, .streamlit/config.toml; echte serverstart op 127.0.0.1:8501 en browsercontrole | Live UI-start bewezen |
| 2. Chatbot-pagina | pages/1_Chatbot.py; AppTest, browsertekstinvoer, vaste AI-disclosure | Gerealiseerd; advies met echte data nog geblokkeerd |
| 3. Testing & Diagnostics | pages/2_Testing_Diagnostics.py; zeven tabs, elf componenten, AppTest en browsercontrole | Gerealiseerd |
| 4. Tekstchat via controller | core/controller.py; lokale provider, context/correcties doorgegeven, kaarten | Offline bewezen met mocks; live minoradvies niet bewezen |
| 5. Microfoonopname | st.audio_input en expliciete verwerkknop, WAV-validatie, epoch/event-ID | Geïntegreerd; echte microfoonopname nog handmatig testen |
| 6. Nederlandse STT | faster-whisper CPU/int8, language=nl, local_files_only; mock- en fouttests | Code gerealiseerd; model ontbreekt, live BLOCKED |
| 7. Nederlandse TTS | PiperVoice, Nederlandse configuratie, synthesize_wav naar geheugen; mocktests | Code gerealiseerd; stem ontbreekt, live BLOCKED |
| 8. Zichtbare historie en reset | core/session.py, Session State; volgorde, dedup en reset in unit tests/AppTest | Offline en tekstbrowserpad bewezen |
| 9. Maximaal drie bronkaarten | Bestaande validator en renderer hergebruikt; ID's en bronquotes gecontroleerd vóór TTS | Offline bewezen; echte catalogus ontbreekt |
| 10. Lege/ongeldige dataset | load_minors, dataset_check en gecontroleerde fallback; UI/AppTest/JSON-tests | Bewezen; lege dataset bevat geen fictieve minoren |
| 11. Eerlijke diagnostiek | Check, Step en tijd/modus; downstream NOT_TESTED, readiness apart | Offline getest, werkelijke omgeving gecontroleerd |
| 12. Automatische tests expliciet | core/test_service.py, vaste shell=False-opdracht, achtergrondworker, 90s-timeout/JUnit | Servicefouten/commandocontract getest; dashboardproef afzonderlijk gerapporteerd |
| 13. Vier scenario's | core/scenarios.py; invoer, verwacht gedrag, echte uitvoer en handmatige relevantiebeoordeling | Beschikbaar; relevantie standaard NOT_TESTED |
| 14. Modulaire structuur | UI → controller → retrieval/provider/validation → speech; scraper onafhankelijk | Gerealiseerd, geen nieuwe backend/database |
| 15. Projectdossier | Status, audit, architectuur, roadmap, matrix en testrapport | Bijgewerkt |
| 16. Geen betaalde externe AI nodig | App maakt alleen loopback-Ollama aan; geen providerfallback, proxy of cloudmodelnaam | Tests en lokale technische modelproef; geen externe AI-calls gedaan |

## Behouden oorspronkelijke eisen

- Bestaande functie chat_with_agent behoudt response, recommended_minor_ids en
  needs_more_info. provider= is een optionele uitbreiding; Gemini blijft legacy.
- JSON-schema, Nederlandse prompt, bronquotes, maximaal drie geldige ID's,
  menselijke doorverwijzing en begrensde vervolgvragen blijven getest.
- Scraper heeft timeout/retries/robots, stabiele URL-ID's, schema en unieke limiet,
  loader en atomaire opslag. Kleine dashboardruns krijgen ook een requestbudget.
- Productieparsing, bronbevestigde minor/vak-classificatie en 50+ echte records
  zijn nog NIET gerealiseerd. Oude HTTP 401 is historische evidence.
- Geen permanente chat-/audio-opslag, geen logging van volledige gesprekken,
  geen modellen/audio/keys/venv in Git. Geen PII-detectie of biasvrijheidsgarantie;
  de prompt beperkt advies tot inhoudelijke interesses en vermijdt stereotypen.

De definitieve testuitslagen en grenzen staan in [TEST_REPORT](TEST_REPORT.md).
