# Test report — 15 oktober 2026

## Resultaten

| Uitvoering | Werkelijk resultaat | Betekenis |
| --- | --- | --- |
| Baseline vóór deze opdracht | 74 tests + 37 unittest-subtests geslaagd | Bestaande functionaliteit bevestigd. |
| Bestaande tests na provideruitbreiding | 74 + 37 geslaagd | Legacy-interface en scraper behouden. |
| Laatste volledige CLI-suite | **133 tests + 37 subtests geslaagd**, 0 fouten, 5,56 s | Alle oude en nieuwe offline checks. |
| Expliciete dashboardknop → worker → pytest | PASS; 170 JUnit-cases geslaagd, 0 gefaald, 0 overgeslagen, 10,08 s | 133 tests + 37 subtests; UI toont aantallen uit JUnit inclusief subtests. Browserresultaat gecontroleerd. |
| Dependencycontrole | `python -m pip check`: geen conflicten | Geïnstalleerde omgeving consistent. |
| Werkelijke Streamlit-start | Uvicorn op 127.0.0.1:8501 | Lokale serverstart bewezen, geen deployment. |
| Werkelijke browsercontrole | Chatbot en Diagnostics bereikbaar; tekstbericht met lege data, juiste fallback, geen aanbevelingen | UI-start en lege-datapad bewezen. |
| Ollama inventaris | Server bereikbaar; qwen2.5:3b ontbreekt | Readiness, geen generatiebewijs voor standaardmodel. |
| Losse echte modelproef | qwen2.5:1.5b-instruct: geldige technische JSON, 6.729 ms | Alleen lokale generatie/JSON, geen studentdata of minoradvies. Bestaand model, geen download. |
| Whisper/Piper | Imports en API-signatures gecontroleerd; standaardmodelbestanden ontbreken | Geen live transcriptie of synthese bewezen. |
| Productiescraper | Geen nieuwe bronaanroep uitgevoerd | Laatste rapport blijft HTTP 401, nul echte records. |

Laatste volledige testopdracht:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.venv/pytest-app-final --tb=short --junitxml=.runtime/pytest-final.xml
.\.venv\Scripts\python.exe -m pip check
```

Live technische proef (expliciet uitgevoerd, alleen bestaand lokaal model):

```powershell
.\.venv\Scripts\python.exe scripts/check_local_ai.py --model qwen2.5:1.5b-instruct
```

Geldige output: `{"status":"lokale_test_geslaagd"}`. Dit voorbeeld is een
technisch controleschema en bevat geen fictieve minor of gebruikersinformatie.

## Testdekking in gedrag

- Bestaande AI-tests: vier scenario's, context, bronfragmenten, maximaal drie
  aanbevelingen, onbekende ID's, ongeldige output, veilige logging en fouten.
- Bestaande scraperchecks: datamodel, URL's, ID's, ontdubbelen, unieke limiet,
  timeouts, robots, redirects, geblokkeerde bron, JSON en atomaire opslag.
- Controller: geschiedenis/correctie doorgeven, volgorde, eventdeduplicatie,
  vervolgvragen, doorverwijzing, lege/ongeldige data en ontbrekend model.
- Geen kaarten of TTS bij ongeldige JSON, ongeldige ID's of verkeerde bronquotes.
- Speech: mock-Nederlandse STT, mock-Piper-WAV, ongeldige audio, ontbrekende
  modellen/packages, Nederlandstalige stemcontrole en veilige foutmeldingen.
- Diagnostics: statusclassificatie, missing dependencies/data, ongeldige JSON,
  readiness versus functiebewijs, lokale modelproef, testtimeout en JUnit-telling.
- Integratie: gemockte bron → werkelijke pipeline → bestand → loader → controller
  → agent; daarnaast gesimuleerde audioketen met STT/LLM/TTS-mocks en foutpaden.
- AppTest: appstart zonder key/modellen, lege dataset, tekstinput, reruns zonder
  duplicaten, reset, gecontroleerde kaarten en Diagnostics zonder automatische tests.
- Lokale provider: loopback-only, geen redirects/proxy/cloudmodel, JSON-schema.
- Kleine dashboard-scrape: expliciete toestemming, max. 5 records/12 requests;
  requestbudget vóór een volgende HTTP-aanroep gecontroleerd.

Er is geen coveragepercentage gemeten. Geslaagde mocks bewijzen geen
inhoudelijke advieskwaliteit of herkenning van echte gesproken audio.

## Omgeving en beperkingen

Windows, Python 3.12.14, Streamlit 1.66.0, google-genai 1.75.0,
requests 2.34.2, BeautifulSoup 4.15.0, Pydantic 2.14.1, pytest 9.1.1,
faster-whisper 1.2.1 en piper-tts 1.8.0. Geen AI-/stemmodellen geïnstalleerd
of gedownload tijdens deze opdracht. Het bestaande 1.5B-model is alleen geladen.

AppTest liep in de Codex-sandbox vast in een lokale socketpair. De eigen
vastgelopen pytest-processen zijn gestopt; de volledige suite is daarna buiten
de socketbeperking uitgevoerd. Dat is apart van de gewone Windows-runtime.
Testartefacten en de browserscreenshot staan genegeerd onder `.runtime/`;
er staan geen echte audio-opnamen of chatlogs in Git.

Niet bewezen: echte minorparsing, 50+ bronrecords, standaardmodelgeneratie met
qwen2.5:3b, echte Nederlandse STT, hoorbare Piper-uitvoer en de volledige live
microfoon-tot-advies-tot-audio-keten. Deze blijven expliciet open.
