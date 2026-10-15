# MinorAdviseur AI

Streamlit Proof of Concept voor Hackathon 4: Spraakagent. Nederlandstalige chat
via **Google Gemini**, met lokale faster-whisper STT en Piper TTS.
De webapp draait op je eigen computer; tekst en gesprekscontext gaan naar Google.
Ollama is niet nodig. Geen hosting, database of eigen backend.

## Current Project Status

De Gemini-provider, controller, chatgeschiedenis, outputvalidatie en het
diagnostiekdashboard zijn geÃ¯ntegreerd. **156 tests en 37 subtests slagen.**
Een echte technische Gemini JSON-proef is geslaagd. De afzonderlijke proef met
het volledige adviesschema kreeg HTTP 503; live minoradvies is nog niet bewezen.
De echte dataset is leeg, de productieparser ontbreekt en het laatste bronrapport
bevat HTTP 401. De volledige live spraakdemo is nog niet bewezen.

Zie [PROJECT_STATUS](docs/PROJECT_STATUS.md), [TEST_REPORT](docs/TEST_REPORT.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [TECHNICAL_AUDIT](docs/TECHNICAL_AUDIT.md),
[ROADMAP](docs/ROADMAP.md) en [requirements](docs/REQUIREMENTS_TRACEABILITY.md).

## Installeren en starten op Windows

Vereist: Python 3.10+, bij voorkeur de geteste Python 3.12. Vanuit de repositoryroot:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -WithSpeech
```

Het script maakt zo nodig .venv, installeert de Python-packages en start
Streamlit op [127.0.0.1:8501](http://127.0.0.1:8501). Bestaande .env blijft
behouden. Ontbreekt .env, dan wordt alleen het lege voorbeeld gekopieerd;
vul daarna zelf je sleutel in en herstart. Er worden **geen modellen gedownload**.
Zonder -WithSpeech worden alleen de basispackages geÃ¯nstalleerd.

Gebruik je bestaande .env in de repositoryroot, met:

```dotenv
GEMINI_API_KEY=jouw_eigen_api_key
GEMINI_MODEL=gemini-flash-latest
```

GEMINI_MODEL mag jouw gewenste beschikbare modelnaam bevatten. .env wordt
automatisch geladen; echte omgevingsvariabelen hebben voorrang. De sleutel
wordt niet getoond, gelogd of opgenomen in Git. **Herstart Streamlit na een
.env-wijziging.** Een key, internet en quota zijn nodig voor Gemini-antwoorden;
eventuele kosten hangen af van je Google-account en gekozen model.

Volgende keren starten zonder opnieuw te installeren:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -SkipInstall
```

Handmatige equivalenten:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-speech.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Stop met Ctrl+C. Bij een bezette poort kan het startscript -Port 8502 gebruiken.
Alleen loopback wordt beluisterd; Streamlit-telemetrie is uitgeschakeld.
De UI blijft bruikbaar zonder API-key, data of spraakmodellen, met duidelijke
blokkades en tekstinvoer als alternatief.

## Lokale spraakmodellen

Speechpackages zijn nog geen modellen. Installeer deze bestanden zelf;
app, health checks en unit tests starten geen downloads:

| Onderdeel | Verwachte bestanden | Indicatieve download |
| --- | --- | --- |
| faster-whisper small | Volledige CTranslate2-directory models/whisper-small, inclusief model.bin, config.json, tokenizer.json en vocabulary.txt | Circa 486 MB |
| Piper Nederlands | models/piper/nl_NL-mls-medium.onnx en naastgelegen .onnx.json | Circa 77 MB plus configuratie |

Onderstaande opdrachten starten die downloads **expliciet**, wanneer je ze zelf
uitvoert na installatie van requirements-speech.txt:

```powershell
.\.venv\Scripts\hf.exe download Systran/faster-whisper-small --local-dir models/whisper-small
.\.venv\Scripts\python.exe -m piper.download_voices nl_NL-mls-medium --download-dir models/piper
```

Bronbestanden en licenties: [Whisper](https://huggingface.co/Systran/faster-whisper-small/tree/main),
[Nederlandse Piper-stem](https://huggingface.co/rhasspy/piper-voices/tree/main/nl/nl_NL/mls/medium).
Omvang is indicatief; controleer de bron vÃ³Ã³r downloaden. STT gebruikt CPU/int8,
Nederlands en local_files_only. Piper controleert de Nederlandse stemcode.
De microfoon accepteert WAV, maximaal 60 seconden / 8 MB.

## Configuratie en integratie

config.py en .env.example beschrijven GEMINI_API_KEY, GEMINI_MODEL, MINORS_PATH,
SCRAPE_REPORT_PATH, WHISPER_MODEL_PATH, PIPER_MODEL_PATH en RUNTIME_DIR.
Standaardpaden liggen onder de repositoryroot. Alle appaanroepen gebruiken de
ingestelde Gemini-key en modelnaam. Er is geen Ollama-fallback.

```python
from config import Settings
from core.controller import run_turn
from scraper.pipeline import load_minors

settings = Settings()
minors = load_minors(settings.dataset_path)
history = []  # Eerdere {"role": "user"/"assistant", "content": "..."}-berichten.
turn = run_turn("Ik studeer ICT en wil ondernemen", history, minors, settings)
print(turn.result)  # response, recommended_minor_ids, needs_more_info
```

chat_with_agent(message, history, minors) blijft beschikbaar en gebruikt dezelfde
Gemini-provider. provider= is optioneel voor mocks. Zie [AI-contract](docs/LEGACY_AI.md)
voor normalisatie en schema. De oude Ollama-adapter blijft alleen voor
compatibiliteit in de repository; app, omgevingscheck en scripts gebruiken hem niet.

Een dataset bevat een JSON-lijst met id, title, institution, description en url.
Optionele velden zijn tekst of null. De loader controleert schema, unieke IDs,
canonieke productie-URLs, stabiele URL-hash en bruikbare beschrijvingen.
Zie [scraperhandleiding](scraper/README.md). Geen fictieve fallbackcatalogus:
zonder echte records worden geen minoren aanbevolen. Brondata blijven niet
automatisch actueel; controleer bronlinks en laatste scrape-tijd.

## Diagnostics en tests

Het dashboard bevat omgeving, scraper/data, Gemini/scenario's, STT, TTS,
end-to-end en automatische tests. Readiness is apart van functioneel bewijs.
De Gemini-knop doet Ã©Ã©n echte aanroep en verbruikt quota; omgevingschecks doen
geen modelaanroepen. Scenario's vragen menselijke beoordeling van relevantie.
Ruwe output is uitsluitend als ongevalideerde diagnostiek beschikbaar.

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
# EÃ©n expliciete echte Gemini-aanroep zonder studentgegevens:
.\.venv\Scripts\python.exe scripts/check_gemini.py
# Volledig offline suite, geen echte API-calls:
.\.venv\Scripts\python.exe -m pytest -q
```

De pytest-worker start uitsluitend na klikken, met vaste opdracht, timeout en
begrensde uitvoer. De kleine scraperactie controleert robots en toegestane
toegang, begrenst tot vijf records / twaalf requests en stopt bij 401/403/429.
De onvoltooide parser kan geen succesvolle scrape suggereren.

## Privacy en grenzen

De UI vermeldt dat tekst, geschiedenis en geselecteerde minorbeschrijvingen naar
Google Gemini gaan. Audio blijft bij lokale STT/TTS; herkende tekst gaat wel naar
Gemini. Deel geen onnodige persoonsgegevens; er is geen automatische PII-redactie.
Zie [Google API-voorwaarden](https://ai.google.dev/gemini-api/terms) voor verwerking
aan de providerzijde.

Gesprekken, transcripties en audio blijven uitsluitend in Streamlit Session State.
Geen permanente chat-/audio-opslag of inhoudelijke debuglogs. Een nieuw gesprek
leegt de chat; diagnostische resultaten hebben een eigen wisknop. Alleen
gevalideerde IDs en bronfragmenten worden als kaarten/spraak gebruikt.
HTTP 400/401/403/404/429/503, netwerkfouten, timeouts en ongeldige JSON geven
veilige meldingen. Relevantie en hoorbaarheid vereisen live beoordeling.
