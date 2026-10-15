# Legacy Gemini-interface (historische documentatie)

Deze eerdere modulehandleiding blijft als referentie behouden. De Streamlit-app gebruikt uitsluitend expliciet Ollama en heeft geen API-key nodig. De oude status- en testaantallen hieronder zijn historisch; raadpleeg PROJECT_STATUS.md en TEST_REPORT.md voor de actuele stand.

# Nederlandstalige AI-minoradviseur

Zelfstandige Python-module voor het HBO-ICT-hackathonprototype. Spraakherkenning
levert tekst aan; Streamlit toont `response` en TTS kan diezelfde tekst uitspreken.
De AI-module bewaart geen gesprekken en bevat geen interface of server.

De onafhankelijke scraper staat in `scraper/`. **De laatste productierun op
15 oktober 2026 stopte op HTTP 401 bij `/modules/`: er zijn nul minoren verzameld en de bronparser is nog
niet geïmplementeerd.** De fetcher, validatie, CLI en rapportage zijn wel getest.
Zie [scraper/README.md](../scraper/README.md) voor onderzoek, uitvoering en beperkingen.

Het [technische projectdossier](PROJECT_STATUS.md) bevat de gecontroleerde
status, [roadmap](ROADMAP.md) en [requirementsmatrix](REQUIREMENTS_TRACEABILITY.md).
Laatste volledige controle: **74 tests en 37 subtests geslaagd**, zonder echte netwerkcalls.

## Installeren en starten

Python 3.10 of nieuwer, vanuit de repositoryroot (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GEMINI_API_KEY = "jouw-eigen-key"
$env:GEMINI_MODEL = "gemini-flash-latest"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Alle AI- en scrapertests:
.\.venv\Scripts\python.exe -m pytest -q
```

`.env.example` beschrijft de configuratie; `.env` wordt **niet automatisch
ingelezen**. Laat de gezamenlijke applicatie eventuele `.env`-configuratie laden,
of zet de variabelen zoals hierboven. Commit nooit een key. `GEMINI_API_KEY`
gaat in deze module voor `GOOGLE_API_KEY` (fallback). `GEMINI_MODEL` is vrij
instelbaar; het gekozen model moet JSON-schema-output ondersteunen. Zonder
modelinstelling wordt `gemini-flash-latest` gebruikt.

## Interface en integratie

```python
import json
from ai.agent import chat_with_agent

with open("minors.json", encoding="utf-8") as file:
    minors = json.load(file)  # Data van jullie scraper, geen ingebouwde catalogus.

# Per student/sessie beheren, bijvoorbeeld in st.session_state.
history = []
message = "Ik studeer HBO-ICT en ben geïnteresseerd in ondernemerschap."
result = chat_with_agent(message, history, minors)

print(result["response"])                # Naar Streamlit en/of TTS.
print(result["recommended_minor_ids"])  # Maximaal drie genormaliseerde string-ID's.
print(result["needs_more_info"])        # True: wacht op een volgend studentantwoord.

# Pas NA de aanroep toevoegen: message mag niet dubbel in de invoer staan.
history.extend([
    {"role": "user", "content": message},
    {"role": "assistant", "content": result["response"]},
])
# Geef bij de volgende aanroep dezelfde history en actuele minors mee.
```

Input: `message: str`, `history: list[{role, content}]`, `minors: list[dict]`.
Ook een JSON-string of wrapper met één van `minors`, `results`, `data` mag als
dataset worden meegegeven. Rollen: `user`, `assistant` (ook `model` als alias).
Alleen eerdere berichten meesturen, maximaal 40; berichttekst maximaal 8000
tekens. Langere gesprekken geven een gecontroleerde fout; start dan een nieuwe
sessie. `history` en `minors` worden niet gewijzigd.

Output is altijd een dictionary met precies:

```json
{
  "response": "Je praat met een AI-minoradviseur. ...",
  "recommended_minor_ids": ["bron-id"],
  "needs_more_info": false
}
```

`needs_more_info` is alleen `true` als de student nog iets moet antwoorden.
Bij technische fouten of doorverwijzing is het `false`, met een lege ID-lijst
en uitleg in `response`. De functie is synchroon; houd daar rekening mee in
de interface. De SDK heeft een HTTP-timeout van 30 seconden per verzoek;
eventuele SDK-retries kunnen de totale wachttijd verlengen.

## Minorformaat en scraper-normalisatie

Dit JSON-schema beschrijft **één genormaliseerde minor**. De dataset is een
JSON-array van deze objecten. ID's moeten uniek en stabiel zijn.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["id", "title", "description", "institution", "url"],
  "properties": {
    "id": {"type": "string", "minLength": 1},
    "title": {"type": "string", "minLength": 1},
    "description": {"type": "string", "minLength": 1},
    "institution": {"type": "string", "minLength": 1},
    "url": {"type": "string", "format": "uri", "pattern": "^https?://"}
  }
}
```

| Canoniek veld | Ondersteunde scraperaliassen |
| --- | --- |
| `id` | `minor_id`, `code` |
| `title` | `titel`, `name`, `naam` |
| `description` | `beschrijving`, `summary` |
| `institution` | `institution_name`, `instelling`, `aanbieder`, `hogeschool` |
| `url` | `link`, `detail_url` |

`normalize_minors` in `ai/validation.py` zet gehele numerieke ID's om naar
strings, verwijdert HTML-tags, decodeert HTML-entiteiten en normaliseert
witruimte in teksten. Relatieve links worden opgelost tegen
`https://www.kiesopmaat.nl/`; alleen HTTP(S)-links zonder gebruikerscredentials
worden geaccepteerd. Onbekende velden worden verwijderd voordat Gemini data
ontvangt. Er worden geen ontbrekende ID's, instellingen of beschrijvingen bedacht.
Eén ongeldige rij, conflicterende aliassen of dubbel ID wijst de hele dataset af.
Een lege dataset geeft direct een doorverwijzing zonder API-call.

Afwijkende geneste scraperobjecten moeten vooraf naar deze velden worden
omgezet. Gebruik `normalize_minors(raw)` ook voor kaarten in de UI, zodat de
string-ID's en getoonde brongegevens overeenkomen met de aanbevelingen. Deze
helper geeft bij foutieve invoer een `ValidationError`; `chat_with_agent` vangt
die af en geeft het vaste outputformaat terug.

## Advies en betrouwbaarheid

Gemini krijgt de Nederlandse systeemprompt, de huidige dataset en de volledige
meegegeven geschiedenis. Het kiest `ask`, `recommend` of `refer`. Het vraagt
gericht naar ontbrekende richting/interesse/voorkeuren; bij voldoende informatie
hoeft niet eerst iedere voorkeur te worden uitgevraagd. Vervolgvragen stoppen
na drie eerdere assistant-beurten, of als dezelfde vaste vraag wordt herhaald.
Aanbevelingen blijven daarna mogelijk; anders volgt een studieadviseur.

De officiële SDK gebruikt `response_mime_type="application/json"` en
`response_json_schema`, zoals beschreven in de
[Google Gen AI SDK-documentatie](https://googleapis.github.io/python-genai/).
De interne JSON bevat actie, vraagcategorie en maximaal drie aanbevelingen met
`minor_id`, `student_quote` en `description_quote`. ID's zijn ook in het schema
beperkt tot de huidige dataset. Python valideert onafhankelijk structuur,
unieke/bestaande ID's, aantallen en letterlijke bronfragmenten. Elke fout wijst
het hele antwoord af; ook gedeeltelijk foutieve adviezen worden niet getoond.

De uiteindelijke Nederlandse tekst wordt met vaste zinnen opgebouwd uit
gecontroleerde studentfragmenten en minorbeschrijvingen. Titels, instellingen en
links komen rechtstreeks uit de dataset. Vrije modeltekst met bijvoorbeeld
verzonnen kosten of toelatingseisen wordt nooit weergegeven. De tekst benoemt
de AI en verwijst voor toelating, kosten en actuele beschikbaarheid naar de
aanbieder en bij twijfel naar een studieadviseur.

De inhoudelijke match blijft een modelinschatting: letterlijke broncontrole
bewijst geen semantische relevantie of actualiteit van scraperdata. De tests
met mocks controleren het modulecontract en de afhandeling, niet de kwaliteit
van Gemini zelf. Loop voor de demo ook de vier scenario's met echte, actuele
scraperdata handmatig door: ICT/ondernemen, zorg/psychologie, onbeslist en geen match.

Getest met `google-genai` 1.75.0: 27 tests geslaagd, inclusief een echte
SDK-aanroep met nagebootst HTTP-antwoord. De AI-module gebruikt alleen
`google-genai` als directe dependency; `requirements.txt` bevat daarnaast de
scraper- en testdependencies. De AI-tests gebruiken `unittest` en maken geen echte API-calls.
De module logt uitsluitend vaste foutcodes, geen
keys, gesprekken of exceptioninhoud. De meegegeven tekst en geschiedenis worden
wel naar Gemini gestuurd: vraag geen onnodige persoonsgegevens en zet geen
HTTP-debuglogging aan in de gezamenlijke app.
