# MinorAdviseur AI

Volledig lokale Streamlit Proof of Concept voor Hackathon 4: Spraakagent.
Nederlandse tekstchat, push-to-talk, lokale Ollama, faster-whisper en Piper.
Geen hosting, database, betaalde modelcalls of verplichte API-key.

## Current Project Status

De UI en controller werken ook met lege data of ontbrekende modellen. De echte
minorendataset is nog leeg; de productieparser ontbreekt en de laatste vastgelegde
Kies op Maat-run gaf HTTP 401. De volledige **live** spraakdemo is daarom nog niet
bewezen. Modellen worden nooit automatisch gedownload.

Zie [PROJECT_STATUS](docs/PROJECT_STATUS.md), [TEST_REPORT](docs/TEST_REPORT.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [TECHNICAL_AUDIT](docs/TECHNICAL_AUDIT.md),
[ROADMAP](docs/ROADMAP.md) en [requirements](docs/REQUIREMENTS_TRACEABILITY.md).

## Snel starten op Windows

Python 3.10+, bij voorkeur de geteste Python 3.12, vanuit de repositoryroot:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Met een geactiveerde virtuele omgeving is het startcommando `streamlit run app.py`.
Open [de lokale app](http://127.0.0.1:8501). Alleen loopback wordt beluisterd;
Streamlit-gebruikstelemetrie is uitgeschakeld in `.streamlit/config.toml`.
De app bevat **Chatbot** en **Testing & Diagnostics**. Zonder data/model kun je
navigatie en tekstinvoer proberen, fouten bekijken en de spraakonderdelen los testen.

## Lokale modellen handmatig installeren

Deze downloads worden **niet** door de app, health checks of tests gestart:

| Onderdeel | Bestanden / omvang | Voorbeeldbron |
| --- | --- | --- |
| Ollama `qwen2.5:3b` | Circa 1,9 GB; houd daarnaast RAM beschikbaar voor inferentie. | [Ollama-modelpagina](https://ollama.com/library/qwen2.5:3b) |
| faster-whisper `small` | Circa 486 MB, volledige CTranslate2-directory. | [Systran modelbestanden](https://huggingface.co/Systran/faster-whisper-small/tree/main) |
| Piper Nederlands | Circa 77 MB ONNX plus JSON-configuratie. | [nl_NL-mls-medium](https://huggingface.co/rhasspy/piper-voices/tree/main/nl/nl_NL/mls/medium) |

Installeer [Ollama voor Windows](https://ollama.com/download/windows). Kies daarna
zelf wanneer je de download wilt starten:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
ollama serve # Alleen als Ollama nog niet draait; laat dit in een apart venster draaien.
ollama pull qwen2.5:3b # Expliciete download van circa 1,9 GB.
```

`qwen2.5:3b` is de standaard. Een ander reeds geïnstalleerd **lokaal** model kan via
`$env:OLLAMA_MODEL = "qwen2.5:1.5b-instruct"` worden geselecteerd vóór de appstart.
Externe hosts, redirects en modelnamen met `cloud` worden geweigerd.

Optionele speechpackages installeren (dit zijn nog geen modellen):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-speech.txt
```

Download vervolgens zelf de volledige Whisper-directory (inclusief `model.bin`,
`config.json`, `tokenizer.json`, `vocabulary.txt`) en de Nederlandse Piper-stem:

```powershell
.\.venv\Scripts\hf.exe download Systran/faster-whisper-small --local-dir models/whisper-small
.\.venv\Scripts\python.exe -m piper.download_voices nl_NL-mls-medium --download-dir models/piper
```

De app verwacht `models/piper/nl_NL-mls-medium.onnx` én de naastgelegen
`nl_NL-mls-medium.onnx.json`. Whisper gebruikt CPU/int8, Nederlands en
`local_files_only=True`; Piper gebruikt CPU en controleert de Nederlandse stemcode.
Neem WAV-audio op met de Streamlit-microfoon, maximaal 60 seconden / 8 MB.
Ontbrekende modellen geven een foutmelding; typen blijft mogelijk. Tekstchat
bewijst geen werkende spraakherkenning of hoorbare TTS.

## Configuratie en data

`config.py` bevat alle defaults; `.env.example` beschrijft de omgevingsvariabelen.
`.env` wordt niet automatisch geladen. Ondersteund: `OLLAMA_URL`, `OLLAMA_MODEL`,
`WHISPER_MODEL_PATH`, `PIPER_MODEL_PATH`, `MINORS_PATH`, `SCRAPE_REPORT_PATH`,
`RUNTIME_DIR`. Standaardpaden zijn relatief aan de repository, niet aan de werkmap.

```python
from scraper.pipeline import load_minors
from core.controller import run_turn
from config import Settings

settings = Settings()
minors = load_minors(settings.dataset_path)
turn = run_turn("Ik studeer ICT en wil ondernemen", [], minors, settings)
print(turn.result)  # response, recommended_minor_ids, needs_more_info
```

Een minor heeft `id`, `title`, `institution`, `description`, `url`. Optionele
`language`, `credits`, `study_format`, `location`, `period`, `requirements` zijn
tekst of null. De loader controleert schema, unieke ID's, productie-URL's,
stabiele URL-hash en bruikbare beschrijvingen. Lees [de scraperhandleiding](scraper/README.md)
voor het exacte contract. Geen fictieve fallbackcatalogus in de functionele app.

De bestaande `chat_with_agent(message, history, minors)` blijft beschikbaar.
Met `provider=OllamaProvider(...)` gebruikt die lokale AI. Zonder expliciete provider
blijft uitsluitend voor bestaande callers/tests de legacy Gemini-route behouden;
**de Streamlit-app roept die route nooit aan**. Zie [legacy-documentatie](docs/LEGACY_AI.md).

## Diagnostics en tests

Het dashboard toont per stap PASS / FAIL / BLOCKED / NOT_TESTED, afhankelijkheden,
foutdetails en oplossingen. Modelvindbaarheid is alleen readiness. Live lokale
proeven, mocks en handmatige relevantiebeoordeling worden afzonderlijk benoemd.
Ruwe modeloutput is alleen in Diagnostics te inspecteren; ongeldige aanbevelingen
worden nooit getoond als kaart of uitgesproken. De testworker start alleen na
klikken, gebruikt een vaste pytest-opdracht, timeout en begrensde uitvoer.

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe scripts/check_local_ai.py
.\.venv\Scripts\python.exe -m pytest -q
```

In de beperkte Codex-Windows-sandbox vereisen Streamlit-sockets een uitvoering
buiten die sandbox en een schrijfbare testmap, bijvoorbeeld
`--basetemp=.venv/pytest-local`. Dat is een omgevingsbeperking, geen modeldownload.

De kleine live scraperknop vereist expliciete bevestiging van toegestane toegang,
controleert robots, stopt op 401/403/429 en begrenst tot 5 records / 12 requests.
De bronparser is nog onvoltooid: de knop kan geen succesvolle scrape suggereren.

## Privacy en grenzen

Gesprekken, transcripties, ruwe modeluitvoer en gegenereerde audio blijven alleen
in de huidige Streamlit Session State. Herstart een gesprek of wis diagnostische
resultaten om die te verwijderen. Geen chat-/audio-opslag op schijf, geen externe
AI en geen logging van gespreksinhoud. Modellen en testartefacten staan buiten Git.
De browser moet microfoontoegang toestaan. Tekst- en spraakaanroepen zijn synchroon;
pytest draait apart op de achtergrond. Modelkwaliteit en hoorbaarheid blijven
handmatig te beoordelen, ook als alle technische validaties slagen.
