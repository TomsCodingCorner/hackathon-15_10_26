# Technical audit â€” 15 oktober 2026

## Inspectie en scope

Branch main, commitbasis 7e89024 (Streamlit UI). Bestaande code/interfaces en
geschiedenis behouden. Geen AGENTS.md aangetroffen. Projectstatus, roadmap en
requirements gecontroleerd; hun beschrijving van uitsluitend lokale Ollama-AI
paste niet meer bij de nieuwste gebruikerskeuze en is bijgewerkt.

De bestaande UI, controller, zoekmodule, validator en lokale speechadapters
bleken herbruikbaar. De defaultcontroller gebruikte Ollama en .env werd niet
geladen. De oude Gemini-route stond dubbel in de agent. Dit is vervangen door
Ã©Ã©n gedeelde officiÃ«le Gemini-provider voor controller Ã©n standalone-interface.
Geen nieuwe backend, database of scrapingframework.

## Implementatiekeuzes

- GEMINI_API_KEY/GEMINI_MODEL via Settings en automatisch geladen root-.env;
  bestaande omgevingsvariabelen winnen. UTF-8/BOM ondersteund, interpolatie uit.
- De key is geen repr-veld; checks/UI tonen alleen aanwezigheid. Geen key,
  prompt, brondata, gesprekken of SDK-exceptions in logs.
- google-genai gebruikt expliciet Developer API en het officiÃ«le endpoint;
  response_json_schema en application/json. EÃ©n poging, begrensde timeout.
- HTTP400/401/403/404/429/503, lege output, netwerk en timeout krijgen vaste
  Nederlandstalige meldingen. Auth/quota/model/serviceproblemen worden BLOCKED;
  geen gedeeltelijke kaarten of TTS uit ongeldige output.
- Bestaande bronvalidatie en vaste renderer behouden. TF-IDF selecteert
  kandidaten; relevantie blijft een inhoudelijke modelinschatting.
- UI vermeldt Google-verwerking. Geen claim meer dat gesprekken lokaal blijven.
  STT/TTS blijven lokaal; transcriptietekst wordt wel naar Gemini gestuurd.
- Readiness voert geen modelcalls/downloads uit. Een echte Gemini-proef vraagt
  expliciete UI/CLI-actie. Pytest blokkeert echte requests/httpx-transports.
- start.ps1 bewaart bestaande .env en installeert geen modellen. Pip installeert
  alleen aangevraagde Python-packages; spraakmodellen blijven handmatig.
- Oude Ollama-adapter en zijn regressietests behouden voor compatibiliteit,
  zonder actieve appimports. check_local_ai.py verwijst voortaan naar Gemini.

SDK-interface gecontroleerd aan [officiÃ«le documentatie](https://googleapis.github.io/python-genai/)
en geÃ¯nstalleerde google-genai1.75.0. Onafhankelijke tests gebruiken zowel mocks
als de echte SDK met MockTransport; die laatste bewijst het HTTP-contract offline.

## Werkelijk geverifieerd en grenzen

156 tests + 37 subtests slagen, pip check vindt geen conflicten. AppTest
controleert beide pagina's, keyverberging, expliciete Gemini-knop, chat, kaarten,
reruns en reset. Het Windows-script start met -SkipInstall op 127.0.0.1:8502.
Geen nieuwe browsermicrofoonproef uitgevoerd.

Een kleine echte Gemini JSON-proef slaagde in 10.152 ms. Een eerdere poging faalde;
de volledige schemaproef met herkenbare fictieve fixtures kreeg daarna HTTP503.
Die testdata zijn nooit in de functionele dataset gezet. Live advieskwaliteit
of een volledige werkende Gemini-adviesketen wordt niet geclaimd.

Whisper-modelbestanden zijn nu aanwezig; alleen bestandscontrole, geen echte
transcriptie. Piper Nederlandse stem/configuratie ontbreekt of is ongeldig.
Productieparser blijft een expliciete stub, dataset [], historisch HTTP401.
Geen nieuwe bronrun, acceptatiegegevens, fictieve productiedata of modellen
toegevoegd. Geslaagde mocks bewijzen geen actualiteit, relevantie of hoorbaarheid.

De beperkte Codex-Windows-sandbox blokkeert lokale AppTest-socketpairs. Daarom
is de suite buiten die beperking uitgevoerd met een schrijfbare basetemp.
Dit is apart van normaal lokaal Windows-gebruik.

Zie [TEST_REPORT](TEST_REPORT.md) en [PROJECT_STATUS](PROJECT_STATUS.md).
