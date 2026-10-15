# Technical audit — 15 oktober 2026

## Inspectie

Lokale repository en remote gecontroleerd, actieve branch main. Bestaande
werkmapwijzigingen zijn behouden. Geen AGENTS.md aangetroffen in de repository.
De drie bestaande dossierstukken zijn gelezen vóór implementatie. Baseline:
74 tests + 37 subtests geslaagd; geen UI, spraakadapters of lokale provider.

De scraperproductieparser is een expliciete stub. De dataset is leeg en de laatste
opgeslagen bronrun gaf HTTP 401. Dit is niet opnieuw onderzocht; geen acceptatie-
of fictieve data gebruikt. De module-interfaces en deduplicatiefix zijn behouden.

## Ontwerpbeslissingen en bevindingen

- Eén Streamlit-entrypoint en native chat/audio/widgets; geen eigen webbackend.
- requests naar Ollama volstaat; geen extra Ollama-SDK of betaald model nodig.
- Lokaal model configureerbaar, standaard qwen2.5:3b. Alleen loopback toegestaan,
  proxies en redirects uit, cloud-modelnamen geweigerd. Start Ollama zelf met
  OLLAMA_NO_CLOUD=1 als extra lokale instelling.
- Bestaande Gemini-route behouden via dezelfde functie, maar nooit bereikbaar
  vanuit de appcontroller. Geen API-key nodig voor lokale werking.
- STT/TTS lazy import en lokale paden. Packages geïnstalleerd en API-signatures
  gecontroleerd, geen weights gedownload. Nederlandse stemcode verplicht.
- TF-IDF is een shortlist, geen semantische waarheid. Negaties en correcties
  worden met alle meegegeven context aan het model aangeboden. Ranking kan
  relevante minoren missen bij meer dan twaalf kandidaten; menselijke toetsing nodig.
- ID-/bronvalidatie beschermt uitvoer; bewijst geen juistheid van scraperinhoud
  of subjectieve passendheid. Geen willekeurige vrije modeltekst naar TTS.
- Diagnostiek onderscheidt file readiness, uitgevoerde mocks, live lokale
  controles en menselijke beoordeling. Alleen daadwerkelijk doorlopen stappen PASS.
- Alleen de expliciete live scraperknop kan internet gebruiken. Die vraagt
  bevestiging van toegestane toegang, controleert robots en stopt op blokkades.
  De parser blijft onvoltooid; geen succesclaim mogelijk op basis van oude HTML.

## Werkelijk geverifieerd

Volledige offline suite, AppTest voor beide pagina's, sessieverloop en kaarten,
werkelijke Streamlit-start en browsernavigatie/tekstchat met lege data. Ollama
/api/tags is bereikbaar; qwen2.5:3b ontbreekt. Technische JSON-proef met het al
geïnstalleerde qwen2.5:1.5b-instruct is geslaagd (geen minoradvies of studentdata).
Zie TEST_REPORT.md voor de exacte aantallen en grenzen.

## Bekende beperkingen

Geen echte minoren of productieparser, geen aanwezige Whisper-/Piper-modelbestanden,
geen live audioketen of live minorrelevantie bewezen. Browsermicrofoon en hoorbare
uitvoer moeten op de demonstratiemachine getest worden. PoC bewaart gesprekken
alleen in sessiegeheugen; er is geen PII-redactie van vrijwillig ingevoerde tekst.
Vraag en voer daarom geen onnodige persoonsgegevens in. Configuratie staat lokaal;
geen auto-installatie of auto-downloads bij een health check.

De Codex-netwerksandbox blokkeerde lokale socketpairs, waardoor AppTest aanvankelijk
vastliep. De eigen testprocessen zijn gestopt en de suite is buiten die sandbox
uitgevoerd. Dit is een omgevingsprobleem; geen overgeslagen tests als PASS gemarkeerd.
Normale Windows-uitvoering gebruikt geen Codex-sandbox.
