# Roadmap — 15 oktober 2026

Bestaande ID's behouden, bijgewerkt voor de lokale Streamlit-opdracht.
P0 is nodig voor betrouwbare kernwerking of de verplichte live demonstratie.

| ID | Prioriteit | Taak | Status / acceptatie |
| --- | --- | --- | --- |
| P0-001 | P0 | Echte productiegegevens en parser | BLOCKED: laatst vastgelegde HTTP 401. Toegestane toegang regelen; echte detail-/overzichtfixtures, minorfilter en paginering. Eerst 5 records controleren, dan 50+ proberen. Geen omzeiling. |
| P0-002 | P0 | Unieke records tellen voor scrape-limiet | Afgerond, regressietests behouden. |
| P0-003 | P0 | Offline integratie van bronbestand tot gecontroleerd AI-antwoord | Gerealiseerd met gemockte bronadapter, loader, lokale provider en controller; inclusief gesimuleerde audioketen en foutpaden. Geen bewijs van echte bron of echte spraak. |
| P0-004 | P0 | Live lokale advieskwaliteit | Open: standaardmodel en echte brondata nodig. De technische JSON-proef met bestaand 1.5B-model bewijst alleen providerwerking. Vier scenario's en correcties inhoudelijk beoordelen. |
| P0-005 | P0 | Streamlit/STT/TTS integreren | Code en offline tests gerealiseerd. Live spraak BLOCKED door ontbrekende modellen; microfoon → Nederlandse transcriptie → echt advies → hoorbare Nederlandse audio nog demonstreren. |
| P0-006 | P0 | Lokale modelomgeving afronden | Open: qwen2.5:3b, Whisper-small en Nederlandse Piper-stem handmatig installeren, of expliciet een reeds lokaal LLM configureren. Geen automatische downloads. |
| P1-001 | P1 | CI-kwaliteitschecks | Open; dezelfde offline pytest-suite gebruiken zonder secrets, bronrequests of modeldownloads. |
| P1-002 | P1 | Bronactualiteit voor gebruiker | Historische scrape-tijd nu zichtbaar in Diagnostics; dataset zelf nog leeg. |

## Volgende hoogste prioriteit

P0-001 blijft de productblokkade voor echte aanbevelingen. Zonder bron kan wel
P0-006 worden afgerond en kunnen de losse STT/TTS-proeven worden uitgevoerd.
De app is reeds lokaal te starten zonder die modellen. Een complete demo mag
pas worden geclaimd na P0-001, P0-004 en de live toets van P0-005.
