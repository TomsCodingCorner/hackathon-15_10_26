# Scraperstatus: laatste productierun geblokkeerd

Onderzoek en runs uitgevoerd op **15 oktober 2026**. Er zijn **0 echte minoren**
verzameld. `data/minors.json` bevat daarom `[]`. Dit is geen werkende minorparser:
`parse_listing` en `parse_detail` stoppen expliciet met
`SourceStructureUnavailable` zolang de echte productie-HTML niet is onderzocht.
Er zijn geen minorselectoren, filters, paginaparameters of API-velden verzonnen.
De bron is in de laatste onderhoudssessie niet opnieuw opgevraagd; de
HTTP-status hieronder is de laatst opgeslagen waarneming.

## Wat is daadwerkelijk onderzocht?

Gewone HTTPS-GET-verzoeken met herkenbare User-Agent
`MinorHackathonScraper/0.1 (educational prototype)`:

| Productiebron | Resultaat |
| --- | --- |
| [robots.txt](https://www.kiesopmaat.nl/robots.txt) | HTTP 200; `User-Agent: *`, `Allow: /` |
| [Homepage](https://www.kiesopmaat.nl/) | HTTP 200; gewone HTML, link naar `/modules/` |
| [Modules](https://www.kiesopmaat.nl/modules/) | HTTP 401; titel “Verifying your browser. Please wait a moment.” |
| [Disclaimer](https://www.kiesopmaat.nl/disclaimer/) | HTTP 200; informatie kan wijzigen; geen expliciete scrapingtoestemming aangetroffen |
| [Voor instellingen](https://www.kiesopmaat.nl/voor-instellingen/) | HTTP 200; algemene informatie over minoren en vakken |

Robots.txt staat crawlen toe, maar heft de toegangsblokkade niet op en is geen
licentie voor hergebruik. In de geraadpleegde pagina's is geen afzonderlijke
toestemming voor scraping aangetroffen. De officiële
[API-handleiding](https://www.kiesopmaat.nl/media/filer_public/13/16/1316439d-85c3-4dfc-bfc8-d19ab0f57ef6/in-handleidinggebruikkiesopmaatapi-260219-1946.pdf)
beschrijft `/api/public/` en leestoegang waarvoor verstrekte toegangsgegevens
nodig zijn. Er is geen anonieme, toegestane JSON-route vastgesteld. De API is
niet aangeroepen en er zijn geen inlogpogingen gedaan.

De HTML van overzicht en details, minor/vak-markering, beschikbare bronvelden,
filters, paginering en eventueel door die pagina gebruikte JSON-endpoints zijn
**niet vast te stellen** door de blokkade. De homepage bewijst niet dat moduledata
zonder JavaScript beschikbaar is. Playwright is niet gebruikt: de browsercontrole
is geen aanleiding om toegangsbeperkingen te omzeilen. De acceptatieomgeving is
niet opgehaald of als gegevensbron gebruikt.

De fixtures bevatten alleen het echte robots.txt en een titel-fragment uit de
401-pagina, zonder challengeparameters. Er is geen succesvolle minor-HTML-fixture.

## Installeren en uitvoeren

Python 3.10+; vanuit de repositoryroot:

```powershell
python -m pip install -r requirements.txt
python -m scraper.pipeline --limit 5
python -m scraper.pipeline --limit 100
python -m pytest -q
```

Dependencies voor dit onderdeel: `requests`, `beautifulsoup4`, `pydantic`, `pytest`
(alleen tests). Geen Gemini-key nodig. Opties: `--output-dir data`, `--delay 1.5`,
`--timeout 20`, `--retries 2`. Geen parallelle requests. De vertraging geldt ook
voor retries; een eventuele robots crawl-delay krijgt voorrang.
401/403/429 en browserchallenges stoppen zonder retry of alternatieve route.
Redirects naar andere hosts, waaronder acceptatie, worden niet gevolgd.
Een ontbrekend/onleesbaar robotsbestand leidt tot stoppen.

`--limit` telt **unieke geldige minoren**. Een duplicaat, ook via een andere
URL met dezelfde canonieke identiteit, verbruikt geen plek; de pipeline zoekt
zo nodig op de volgende pagina verder. Bij minder werkelijk aanbod stopt de
run met het echte aantal. Dit is met gemockte bronadapters getest.

Bij blokkade eindigt de CLI met exitcode **1**, dus dit is geen geslaagde scrape.
Exitcode 0 betekent succes; 2 betekent ongeldige configuratie of een schrijffout.
Na toegestane toegang moeten de twee parserfuncties eerst op echte bronfixtures
worden geïmplementeerd. Alleen bronbevestigde minoren mogen dan worden doorgelaten;
die controle en de echte paginering zijn nu **nog niet geïmplementeerd**.

## Bestanden en output

- `fetcher.py`: robotsbeleid, vertraging, timeout, beperkte retries en tellers.
- `parser.py`: tekstopschoning en relatieve URL's; productieparsers zijn geblokkeerd.
- `models.py`: Pydantic-contract, canonieke bron-URL en stabiele SHA-256-ID.
- `pipeline.py`: orkestratie, deduplicatie, atomair schrijven, rapport, loader en CLI.
- `data/minors.json`: JSON-array; bij deze runs leeg.
- `data/scrape_report.json`: rapport van de laatste run, geen opgetelde historie.

Een Minor heeft verplichte `id`, `title`, `institution`, `description`, `url`.
Optionele `language`, `credits`, `study_format`, `location`, `period`, `requirements`
zijn tekst of `null`; er wordt geen ontbrekende broninformatie aangevuld. Ook
credits blijft brongetrouwe tekst. Een beschrijving moet minimaal 30 tekens en
vijf woorden bevatten; lege velden en placeholders worden afgewezen.
Alleen HTTPS-detail-URL's onder `www.kiesopmaat.nl/modules/` worden geaccepteerd.
Query en fragment worden voor identiteit verwijderd; een afsluitende slash
wordt genormaliseerd. ID = `kom-` plus 24 hextekens van de URL-hash.
Dubbele ID's en canonieke URL's worden herkend. Extra JSON-velden zijn verboden.

Bij een volledig mislukte run blijft een bestaande dataset byte voor byte intact.
Alleen als er nog geen bestand bestaat, wordt een lege array aangemaakt.
Een gedeeltelijke dataset zou de oude vervangen en krijgt status `partial`;
dat pad is alleen met mocks getest. Er wordt geen ruwe HTML, contactinformatie,
API-key of challenge-token in de output opgeslagen.

Rapporttellers gelden voor **de betreffende CLI-run**, inclusief robots en retries.
`pages_succeeded` telt HTTP 2xx-responses. `records_extracted` telt door de parser
opgeleverde records; `records_rejected` de daarvan ongeldige modelobjecten.
`records_valid` telt unieke geldige records. Herhaalde detail-links tellen apart
als `duplicate_urls_skipped`. Onderzoeksrequests en unittests tellen niet mee.

| Uitgevoerde run | Requests | HTTP 2xx | Geldige minoren | Status |
| --- | --- | --- | --- | --- |
| `--limit 5` | 2 | 1 (robots) | 0 | blocked, modules HTTP 401 |
| `--limit 100` | 2 | 1 (robots) | 0 | blocked, modules HTTP 401 |

Er zijn geen vijf of vijftig bronrecords beschikbaar voor handmatige
inhoudscontrole. De limiet vergroten heeft de toegangsblokkade niet opgeheven.

## Integratie en tests

```python
from scraper.pipeline import load_minors

minors = load_minors("data/minors.json")  # Geen scraping bij import of laden.
# Naar de afzonderlijke AI-module: chat_with_agent(message, history, minors).
```

De loader valideert de volledige JSON-array en weigert ongeldige records en
duplicaten. Een lege array is geldig; de AI-agent verwijst dan naar een
studieadviseur. Een ontbrekend bestand of ongeldige JSON geeft een fout aan de caller.

Offline getest: modelschema, ontbrekende velden, stabiele ID's, canonieke en
relatieve URL's, tekstopschoning, deduplicatie, timeouts/retries, robotsweigering,
vertraging, redirects, blokkades, veilige opslag, import zonder requests, CLI,
JSON-loader en compatibiliteit met het AI-invoercontract. Pipeline-paginering is
uitsluitend met een **gemockte bronadapter** getest. Testrecords zijn synthetisch,
worden nergens naar `data/minors.json` geschreven en zijn geen productiegegevens.

Laatste volledige projectcontrole na de lokale Streamlit-integratie:
**133 tests en 37 unittest-subtests geslaagd**. Dit omvat de eerdere 74 tests en
nieuwe controller-, lokale-provider-, speech-, diagnostiek-, UI- en integratiechecks.
De unittests gebruiken gemockte bron-/model-/spraakresponses, geen echte bronrequests.
Zie [het technische dossier](../docs/PROJECT_STATUS.md) voor opdrachten,
regressiebewijs en de [volgende prioriteiten](../docs/ROADMAP.md).

Niet getest of geïmplementeerd: succesvol parsen van een echte minorpagina,
echte filters/paginering, minor/vak-classificatie en een geslaagde scrape met
50+ records. Daarvoor is eerst toegestane productietoegang nodig. Een mogelijke
vervolgstap is via de beheerder toegestane toegang regelen; er worden geen
automatische berichten verstuurd. Broninformatie kan veranderen en wordt alleen
door een expliciete nieuwe run bijgewerkt, nooit automatisch actueel gehouden.

In de beperkte Codex-sandbox is de testsuite uitgevoerd met
`python -m pytest -q --basetemp=.venv/pytest-tmp`, omdat de standaard Windows-
tempdirectory daar niet schrijfbaar was.

De Streamlit-diagnostiekknop gebruikt aanvullend een hard budget van maximaal
12 HTTP-verzoeken (inclusief robots), maximaal 5 records en geen retries.
De CLI-default blijft ongewijzigd. De app kan ook zonder brondata starten;
zie [README](../README.md) en [TEST_REPORT](../docs/TEST_REPORT.md).
