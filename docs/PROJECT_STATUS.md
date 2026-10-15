# Projectstatus â€” 15 oktober 2026

Gecontroleerd op branch main, commitbasis 7e89024 (Streamlit UI), met de
Gemini-wijzigingen in de werkmap. Geen commit, push of deployment uitgevoerd.

## Huidige implementatie

Streamlit-pagina's, controller, TF-IDF-search, bronvalidatie, sessies, scraperbasis
en lokale spraakadapters behouden. Op verzoek is **Google Gemini de actieve
AI-provider**. Ollama is niet nodig en wordt niet door de app gebruikt.
De eerdere eis uitsluitend lokale AI is hiermee vervangen.

Nieuw: officiÃ«le google-genai-provider, automatisch .env laden met
omgevingsvoorrang, GEMINI_API_KEY/GEMINI_MODEL in Settings, veilige foutcodes,
Gemini-diagnostiek, expliciete JSON-proef en Windows start/installatiescript.
chat_with_agent(message, history, minors) behoudt zijn uitvoercontract.

| Onderdeel | Actuele evidence | Stand |
| --- | --- | --- |
| Offline suite | 156 tests + 37 subtests, 0 fouten, 7,89 s | PASS |
| Streamlit | Beide pagina's, chat en Gemini-diagnostiek via AppTest; startscript -SkipInstall start server op 127.0.0.1:8502 | UI-start bewezen |
| Gemini-configuratie | .env geladen, sleutel gevonden zonder waarde te tonen; model gemini-flash-latest | Configuratie aanwezig |
| Technische Gemini JSON-proef | Echte API gaf {"status":"gemini_test_geslaagd"}, 10.152 ms | PASS voor deze proef |
| Volledig adviesschema | GeÃ¯soleerde live proef met fictieve unit-testfixtures kreeg HTTP 503 | Extern BLOCKED; live advies niet bewezen |
| Controller/validatie/kaarten | SDK-mocks, echte SDK met MockTransport, context-/quote-/ID-tests | Offline bewezen |
| Whisper | Package en vereiste modelbestanden gevonden; geen transcriptie uitgevoerd | Readiness aanwezig; functie NOT_TESTED |
| Piper | Package aanwezig; Nederlandse stem/configuratie ontbreekt of is ongeldig | Live TTS BLOCKED |
| Scraper/dataset | Productieparser onvoltooid, minors.json bevat [], historisch rapport HTTP 401 | BLOCKED, 0 echte records |
| Volledige spraakketen | Geen echte microfoon â†’ advies â†’ hoorbare audio uitgevoerd | NOT_TESTED |

De eerste kleine Gemini-proef mislukte; de gerichte hercontrole slaagde.
De volledige schemaproef werd daarna door Google met HTTP 503 afgewezen.
EÃ©n geslaagde technische aanroep bewijst geen stabiele service of advieskwaliteit.
Geen modellen gedownload, sleutel gewijzigd of echte gesprekken/audio opgeslagen.

## Privacy en veiligheid

Webapp en spraakverwerking zijn lokaal. Tekst, historie en kandidaatminoren gaan
naar Google Gemini; dit staat zichtbaar in de UI. De key is verborgen in
Settings-repr, checks en UI. Geen gesprekken, audio-inhoud of SDK-exceptions
in logs. API-aanroepen gebruiken quota. Omgevingschecks doen geen API-calls;
unit tests blokkeren echte HTTP.

IDs en letterlijke bronfragmenten worden gecontroleerd vÃ³Ã³r kaarten en TTS.
Lege data, ontbrekende key, providerfouten en ongeldige output stoppen de keten;
downstream stappen blijven NOT_TESTED. Geen providerfallback of modeldownloads.

## Eerstvolgende werk

P0-001: toegestane productietoegang en echte parser/data herstellen. Daarna live
meerbeurtsadvies met Gemini en vier scenario's inhoudelijk beoordelen.
Piper installeren en Nederlandse STT/TTS met microfoon testen kan apart.
Zie [TEST_REPORT](TEST_REPORT.md), [ROADMAP](ROADMAP.md) en
[requirements](REQUIREMENTS_TRACEABILITY.md).
