# Roadmap â€” 15 oktober 2026

Bestaande taak-IDs behouden. De gebruiker heeft Gemini gekozen; Ollama installeren
of downloaden is geen vereiste meer.

| ID | Prioriteit | Taak | Status / acceptatie |
| --- | --- | --- | --- |
| P0-001 | P0 | Echte productiegegevens en parser | BLOCKED: historisch HTTP 401, parser onvoltooid. Toegestane toegang, echte fixtures, minorfilter en paginering. Eerst vijf records controleren, daarna 50+ proberen. Geen omzeiling. |
| P0-002 | P0 | Unieke records tellen voor scrape-limiet | Afgerond, regressietests behouden. |
| P0-003 | P0 | Offline bronbestand tot gecontroleerd antwoord | Afgerond met mocks, loader/controller en gesimuleerde audioketen; geen bewijs van live bron of spraak. |
| P0-004 | P0 | Live Gemini-advieskwaliteit | Open: technische JSON-proef geslaagd; volledig schemaproef extern HTTP 503. Bij beschikbare API en echte data context, correcties, scenario's en relevantie beoordelen. |
| P0-005 | P0 | Streamlit/STT/TTS integreren | Code en offline tests gerealiseerd. Echte microfoon â†’ transcriptie â†’ gecontroleerd advies â†’ hoorbare audio nog demonstreren. |
| P0-006 | P0 | Gemini en lokale spraakomgeving afronden | Gemini-provider/configuratie gerealiseerd, technische live proef geslaagd. Whisper-bestanden aanwezig, transcriptie NOT_TESTED. Nederlandse Piper-stem installeren en testen. |
| P1-001 | P1 | CI-kwaliteitschecks | Open; offline suite zonder secrets, bronrequests of modeldownloads. |
| P1-002 | P1 | Bronactualiteit | Historische scrape-tijd zichtbaar; dataset nog leeg. Nieuwe bronrun blijft expliciet. |

## Volgende hoogste prioriteit

P0-001 blijft de blokkade voor echte aanbevelingen. Los daarvan kunnen Piper
installatie en live STT/TTS-proeven worden afgerond. De app kan met Gemini
starten; een volledige live demo vraagt echte data, API-beschikbaarheid en een
gecontroleerde spraakketen. HTTP 503 wordt als externe blokkade getoond.
