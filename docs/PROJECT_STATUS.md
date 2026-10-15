# Projectstatus — 15 oktober 2026

Gecontroleerd op lokale branch `main`, remote TomsCodingCorner/hackathon-15_10_26,
commitbasis `b3262be` plus bestaande werkmapwijzigingen. Die wijzigingen en de
projectgeschiedenis zijn behouden; er is niet gecommit, gepusht of gedeployed.

## Wat bestaat en wat is toegevoegd?

Bestaand: Gemini-agent, Nederlandse prompt, JSON-/ID-/bronvalidatie, scraperbasis,
Pydantic-dataformaat, veilige opslag en 74 geslaagde tests. De eerdere fix waarbij
alleen unieke minoren de scrape-limiet vullen is behouden.

Nieuw: één Streamlit-entrypoint, twee pagina's, centrale lokale configuratie,
conversation controller, sessiebeheer tegen dubbele reruns, Ollama-provider,
TF-IDF-ranking, lokale STT/TTS-adapters, elf componentstatussen en zeven
diagnostiektabs. Inclusief scenario's, losse JSON-modelproef, spraaktests,
ketentraces en een pytest-worker met timeout. Geen nieuwe backend of database.

## Aantoonbare huidige stand

| Onderdeel | Evidence | Status |
| --- | --- | --- |
| Chatbot en Diagnostics | AppTest én lokale browsercontrole; server start op 127.0.0.1:8501. Tekstinvoer met lege data geeft de bedoelde blokkade. | UI gerealiseerd |
| Geschiedenis / herstart / reruns | AppTest en unit tests; volgorde behouden, dubbele event-ID genegeerd. | Offline bewezen |
| Tekstadvies met lokale provider | Controller- en UI-tests met gemockte modeloutput en tijdelijke testdata. | Offline bewezen, echte advieskwaliteit nog niet bewezen |
| Ollama server | Echte lokale /api/tags-controle uitgevoerd. | Bereikbaar |
| Standaardmodel qwen2.5:3b | Niet in lokale modelinventaris. | BLOCKED |
| Bestaand qwen2.5:1.5b-instruct | Echte technische JSON-generatieproef, 6.729 ms, geldige gecontroleerde uitvoer. Geen studentdata/minoren gebruikt. | PASS voor deze technische proef |
| STT en TTS | Packages geïnstalleerd/imports gecontroleerd; adapters getest met mocks. Whisper/Piper-modellen ontbreken op standaardpaden. | Live spraak BLOCKED |
| Scraper | Productieparser nog niet geïmplementeerd. Laatste bewaarde bronrun: HTTP 401 op /modules/. Geen nieuwe bronrun in deze opdracht. | BLOCKED |
| Dataset | data/minors.json bevat [], ongewijzigd. | BLOCKED |
| Volledige live audioketen | Nog geen echte transcriptie, minoradvies en synthese samen uitgevoerd. | NOT_TESTED / afhankelijkheden geblokkeerd |

Er zijn geen modellen gedownload, betaalde modelcalls gedaan of echte
gebruikersgesprekken/-audio opgeslagen. Een poging om Ollama te starten wees uit
dat de server al draaide; de bestaande server is niet gestopt of vervangen.

## Behoud van interfaces en veiligheid

`chat_with_agent(message, history, minors)` behoudt de drie uitvoervelden.
Een optioneel keyword `provider=` voegt lokale ondersteuning toe. Bestaande
Gemini-callers blijven werken; de app injecteert altijd Ollama en valt nooit
terug naar Gemini. `analyze_chat` voegt alleen sessiegebonden diagnostiek toe.
De bestaande validator wordt gebruikt voordat kaarten of TTS worden opgebouwd.

Lege/ongeldige data stopt retrieval en laat model/validatie/TTS NOT_TESTED.
Geen STT/TTS-model wordt tijdens een health check geladen. Modelbestandscontrole
is geen functionaliteitsclaim. Relevantie en hoorbaarheid vragen menselijke
beoordeling. De kleine scraperactie is expliciet, robotsbewust en begrensd tot
5 records en 12 HTTP-verzoeken.

## Wat is nog nodig voor een echte demo?

1. Toegestane productietoegang, echte parserfixtures en echte minoren.
2. Het gekozen Ollama-model beschikbaar maken (standaard 3B of een lokale override).
3. Whisper-small en een Nederlandse Piper-stem handmatig installeren.
4. Een Nederlandse microfoonopname, STT, meerbeurts advies en hoorbare TTS live testen.

Zie [TEST_REPORT](TEST_REPORT.md), [ROADMAP](ROADMAP.md),
[TECHNICAL_AUDIT](TECHNICAL_AUDIT.md) en [requirements](REQUIREMENTS_TRACEABILITY.md).
