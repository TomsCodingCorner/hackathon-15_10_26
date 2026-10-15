# Test report â€” 15 oktober 2026, Gemini-update

## Uitgevoerde controles

| Controle | Werkelijk resultaat | Betekenis |
| --- | --- | --- |
| Volledige offline pytest-suite | **156 tests + 37 subtests geslaagd**, 0 fouten, 7,89 s | Alle bestaande en nieuwe checks; 193 JUnit-cases inclusief subtests |
| Gerichte nieuwe provider/configuratiechecks | 20 geslaagd vÃ³Ã³r uitbreiding met 400/503 en UI-regressie | Opgenomen en opnieuw geslaagd in volledige suite |
| pip check | No broken requirements found | Geen dependencyconflicten in geÃ¯nstalleerde omgeving |
| PowerShell AST | start.ps1 zonder syntaxfouten | Geen syntaxclaim voor onuitgevoerde branches |
| Werkelijke scriptstart | start.ps1 -SkipInstall -Port8502 start Streamlit op127.0.0.1:8502 | Echte lokale serverstart, geen deployment |
| Streamlit AppTest | Beide pagina's, geschiedenis/reset/reruns, kaarten, expliciete Gemini-proef en verborgen key | Offline UI-bewijs |
| Kleine echte Gemini JSON-proef | PASS, gemini-flash-latest, 10.152 ms, {"status":"gemini_test_geslaagd"} | Provider/key/model werkten voor deze technische proef |
| Volledige echte adviesschemaproef | HTTP503 bij Google met geÃ¯soleerde fictieve testfixtures | Live adviesschema/aanbevelingen niet bewezen; geen datasetwijziging |
| Lokale readiness | Key aanwezig; Whisper-bestanden gevonden; Piper-stem/configuratie ontbreekt of ongeldig | Geen bewijs van echte STT/TTS |
| Scraper/data | Geen nieuwe scrape; [] en historisch HTTP401 behouden | Nul echte minorrecords, geen nieuwe bronclaim |

De eerste kleine API-proef gaf een veilige generieke fout; de gerichte hercontrole
slaagde. De volledige schemaproef kreeg vervolgens HTTP503. Daarom is expliciete
503-classificatie met BLOCKED-status en regressietest toegevoegd. Een latere
hercontrole met hetzelfde volledige adviesschema bevestigde HTTP 503 en de
nieuwe BLOCKED-classificatie; alle downstream stappen bleven NOT_TESTED. Geen verborgen
automatische retry of omschakeling naar een ander model.

## Reproduceerbare opdrachten

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.venv/pytest-gemini-final --tb=short --junitxml=.runtime/pytest-gemini.xml
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_environment.py
# Expliciet live, gebruikt Google API-quota; geen studentgegevens:
.\.venv\Scripts\python.exe scripts/check_gemini.py
# App starten zonder herinstallatie:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -SkipInstall -Port 8502
```

Alle pytest-tests zijn offline. Een autouse-fixture blokkeert echte HTTP via
requests en httpx; SDK-mocks en MockTransport mogen wel. Geen modeldownloads,
echte API-keys of gesprekken in testfixtures. De live schemaproef buiten pytest
gebruikte uitsluitend herkenbare fictieve data uit bestaande unittest-fixtures,
zonder permanente opslag of tonen als echte chatbotcatalogus.

## Gedragsdekking

- Bestaande AI/scrapertests behouden: vier scenario's, context, bronquotes,
  maxdrie, onbekende ID, ongeldige JSON, logging, URL/ID/modelvalidatie,
  unieke limiet, timeouts/robots/blokkades en veilige opslag.
- Gemini: key/model uit omgeving en .env, omgevingsvoorrang, verborgen key,
  officieel SDK-schema/endpoint, timeout, gesloten client, Ã©Ã©n poging,
  400/401/403/404/429/500/503, netwerk, timeout en lege responses.
- Echte SDK met MockTransport: HTTP-contract en expliciete keyvoorrang, 429
  zonder retries. Geen netwerk.
- Controller: Gemini-default, context, valide aanbevelingen, ontbrekende key,
  ongeldige output, lege data en 503 met downstream NOT_TESTED.
- Speech: mocks voor Nederlandse STT/TTS en ongeldige audio/modellen/fouten.
- Integratie: gemockte bron tot loader/controller/agent, gesimuleerde audioketen.
- UI: beide pagina's, geen automatische tests/modelcalls bij starten, verborgen
  key, expliciete modelknop, juiste historie/reset en gevalideerde kaarten.
- Diagnostics/pytest-worker: statusclassificatie, readiness apart, timeout,
  gecontroleerde commandolijst en JUnit-telling.

Er is geen coveragepercentage gemeten. Inhoudelijke advieskwaliteit en hoorbare
spraakuitvoer vragen menselijke live beoordeling.

## Omgeving en historische evidence

Windows, Python3.12.14, Streamlit1.66.0, google-genai1.75.0,
python-dotenv1.2.4, requests2.34.2, BeautifulSoup4.15.0, Pydantic2.14.1,
pytest9.1.1, faster-whisper1.2.1 en piper-tts1.8.0.

Vorige versie: 133 tests + 37 subtests; browsercontrole en pytest-dashboardworker
werden toen uitgevoerd. De toenmalige Ollama-proef is historische evidence,
geen huidige providerclaim. Het gewijzigde startscript is nu met bestaande
venv en -SkipInstall uitgevoerd; een nieuwe schone volledige pip-installatie
of modeldownload is in deze wijziging niet uitgevoerd.

Codex-sandbox blokkeert lokale AppTest-sockets; de volledige suite is buiten
die beperking uitgevoerd met schrijfbare testmap. Geen tests overgeslagen.
Artefacten staan genegeerd onder .runtime. Niet bewezen: echte productieparsing,
50+ bronrecords, live meerbeurtsadvies, echte Nederlandse transcriptie,
hoorbare Piper-uitvoer en complete microfoon-tot-advies-tot-audio-keten.
