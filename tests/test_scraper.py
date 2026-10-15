"""Offline tests. Synthetische Minor-objecten zijn uitsluitend testdata.

Er is GEEN geslaagde parsefixture van productie: de bron blokkeert toegang.
Daarom testen we geen verzonnen site-layout alsof die daadwerkelijk werkt.
"""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from pydantic import ValidationError

from scraper.fetcher import FetchError, Fetcher
from scraper.models import Minor, SOURCE, canonical_url, stable_id
from scraper.parser import Listing, SourceStructureUnavailable, absolute_url, clean_text, parse_detail, parse_listing
from scraper.pipeline import _write_json, deduplicate, load_minors, main, run_scrape

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests mogen geen netwerkrequests doen.")
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)


@pytest.fixture
def minor_data():
    # Een fictief modelobject om het contract te testen, geen gescrapete minor.
    url = "https://www.kiesopmaat.nl/modules/fixture/fixture/123/"
    return {
        "id": stable_id(url), "title": "UITSLUITEND TESTDATA",
        "institution": "Fictieve testinstelling",
        "description": "Dit is uitsluitend een synthetische beschrijving voor een offline contracttest.",
        "url": url,
    }


def response(status=200, text="", headers=None):
    return SimpleNamespace(status_code=status, text=text, headers=headers or {}, close=Mock())


def fake_get(monkeypatch, responses):
    get = Mock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "get", get)
    return get


def robots_response():
    return response(text=(FIXTURES / "robots.txt").read_text(encoding="utf-8"))


def test_missing_optional_fields_are_null(minor_data):
    minor = Minor.model_validate(minor_data)
    for field in ("language", "credits", "study_format", "location", "period", "requirements"):
        assert minor.model_dump()[field] is None


@pytest.mark.parametrize("field", ["id", "title", "institution", "description", "url"])
def test_missing_required_fields_rejected(minor_data, field):
    minor_data.pop(field)
    with pytest.raises(ValidationError):
        Minor.model_validate(minor_data)


@pytest.mark.parametrize("description", ["", "-", "Onbekend", "Kort."])
def test_unusable_descriptions_rejected(minor_data, description):
    with pytest.raises(ValidationError):
        Minor.model_validate({**minor_data, "description": description})


@pytest.mark.parametrize("url", ["", "https://www.kiesopmaat.nl/modules/", "http://www.kiesopmaat.nl/modules/a/b/1/",
                                  "https://acceptatie.kiesopmaat.nl/modules/a/b/1/", "https://example.org/modules/a/",
                                  "https://user:pass@www.kiesopmaat.nl/modules/a/", "https://["])
def test_invalid_or_nonproduction_urls_rejected(url):
    with pytest.raises(ValueError):
        canonical_url(url)


def test_stable_ids_and_canonical_relative_urls():
    url = "https://www.kiesopmaat.nl/modules/fixture/unit/123/"
    assert stable_id(url) == stable_id(url + "?utm_source=test#description")
    assert canonical_url("/modules/fixture/unit/123") == url
    assert absolute_url("../123/", "https://www.kiesopmaat.nl/modules/fixture/unit/456/") == url


def test_deduplication_by_id_and_canonical_url(minor_data):
    first = Minor.model_validate(minor_data)
    second = Minor.model_validate({**minor_data, "url": minor_data["url"] + "?ref=test"})
    unique, removed = deduplicate([first, second, first])
    assert unique == [first]
    assert removed == 2


def test_html_cleanup():
    assert clean_text("<p>Een&nbsp; minor</p><script>tracking()</script><p>over\u200b data.</p>") == "Een minor over data."


@pytest.mark.parametrize("parser", [parse_listing, parse_detail])
def test_actual_browser_challenge_is_never_parsed_as_a_minor(parser):
    html = (FIXTURES / "blocked_excerpt.html").read_text(encoding="utf-8")
    with pytest.raises(SourceStructureUnavailable, match="browser_challenge"):
        parser(html, SOURCE)


def test_unverified_source_layout_fails_explicitly():
    with pytest.raises(SourceStructureUnavailable, match="not_verified"):
        parse_listing("<html><h1>Geen bevestigde modulestructuur</h1></html>", SOURCE)


@pytest.mark.parametrize("failure", [requests.Timeout, requests.ConnectionError])
def test_network_errors_retry_only_within_limit(monkeypatch, failure):
    get = fake_get(monkeypatch, [failure(), failure(), failure()])
    fetcher = Fetcher(delay=0, retries=2)
    with pytest.raises(FetchError, match="network_error_or_timeout"):
        fetcher.load_robots()
    assert get.call_count == fetcher.stats.pages_requested == 3
    assert fetcher.stats.pages_succeeded == 0
    fetcher.close()


@pytest.mark.parametrize("status", [401, 403, 429])
def test_restricted_responses_stop_without_retry(monkeypatch, status):
    blocked = response(status=status)
    get = fake_get(monkeypatch, [robots_response(), blocked])
    fetcher = Fetcher(delay=0)
    fetcher.load_robots()
    with pytest.raises(FetchError, match="access_restricted"):
        fetcher.get(SOURCE)
    assert get.call_count == 2
    blocked.close.assert_called_once()
    assert fetcher.stats.pages_succeeded == 1
    fetcher.close()


def test_robots_disallow_prevents_module_request(monkeypatch):
    get = fake_get(monkeypatch, [response(text="User-agent: *\nDisallow: /modules/\n")])
    fetcher = Fetcher(delay=0)
    fetcher.load_robots()
    with pytest.raises(FetchError, match="robots_denied"):
        fetcher.get(SOURCE)
    assert get.call_count == 1
    fetcher.close()


def test_redirect_to_acceptance_is_not_followed(monkeypatch):
    get = fake_get(monkeypatch, [robots_response(), response(302, headers={"Location": "https://acceptatie.kiesopmaat.nl/modules/"})])
    fetcher = Fetcher(delay=0)
    fetcher.load_robots()
    with pytest.raises(FetchError, match="disallowed_origin"):
        fetcher.get(SOURCE)
    assert get.call_count == 2
    fetcher.close()


def test_configured_delay_is_respected(monkeypatch):
    fake_get(monkeypatch, [robots_response(), response(text="page")])
    sleeps = Mock()
    monkeypatch.setattr("scraper.fetcher.time.sleep", sleeps)
    monkeypatch.setattr("scraper.fetcher.time.monotonic", lambda: 10)
    fetcher = Fetcher(delay=2)
    fetcher.load_robots()
    fetcher.get(SOURCE)
    sleeps.assert_called_once_with(2)
    fetcher.close()


def test_failed_scrape_preserves_existing_data_and_counts_requests(monkeypatch, tmp_path):
    fake_get(monkeypatch, [robots_response(), response(401)])
    previous = b'[{"previous":"untouched"}]\n'
    (tmp_path / "minors.json").write_bytes(previous)
    report = run_scrape(5, tmp_path, delay=0)
    assert (tmp_path / "minors.json").read_bytes() == previous
    assert report["status"] == "blocked"
    assert report["pages_requested"] == 2
    assert report["pages_succeeded"] == 1
    assert report["records_valid"] == report["records_extracted"] == 0
    assert report["dataset_updated"] is False
    assert json.loads((tmp_path / "scrape_report.json").read_text()) == report


def test_first_failed_run_creates_only_empty_dataset(monkeypatch, tmp_path):
    fake_get(monkeypatch, [robots_response(), response(401)])
    report = run_scrape(100, tmp_path, delay=0)
    assert load_minors(tmp_path / "minors.json") == []
    assert report["empty_dataset_initialized"] is True
    assert report["records_valid"] == 0


def test_json_output_is_compatible_with_ai_contract(minor_data, tmp_path):
    from ai.validation import normalize_minors
    path = tmp_path / "minors.json"
    _write_json(path, [Minor.model_validate(minor_data).model_dump()])
    loaded = load_minors(path)
    normalized = normalize_minors(loaded)
    assert normalized[0]["id"] == minor_data["id"]
    assert normalized[0]["description"] == minor_data["description"]


@pytest.mark.parametrize("content", ['{}', 'null', '[{"title":"incomplete"}]', 'not json'])
def test_invalid_json_structure_rejected(tmp_path, content):
    path = tmp_path / "minors.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_minors(path)


def test_duplicate_records_in_loaded_json_are_rejected(minor_data, tmp_path):
    path = tmp_path / "minors.json"
    _write_json(path, [minor_data, minor_data])
    with pytest.raises(ValueError, match="dubbele"):
        load_minors(path)


def test_atomic_write_failure_preserves_old_file(monkeypatch, tmp_path):
    path = tmp_path / "minors.json"
    path.write_text("[]\n")
    monkeypatch.setattr("scraper.pipeline.os.replace", Mock(side_effect=OSError("disk error")))
    with pytest.raises(OSError):
        _write_json(path, [{"new": "data"}])
    assert path.read_text() == "[]\n"
    assert list(tmp_path.iterdir()) == [path]


def test_cli_returns_nonzero_on_blocked_access(monkeypatch, tmp_path, capsys):
    fake_get(monkeypatch, [robots_response(), response(401)])
    assert main(["--limit", "5", "--output-dir", str(tmp_path), "--delay", "0"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"


def test_import_starts_no_scraping(monkeypatch):
    get = fake_get(monkeypatch, [])
    import scraper.pipeline
    importlib.reload(scraper.pipeline)
    get.assert_not_called()


def test_pagination_and_record_limit_with_mocked_source_adapter(monkeypatch, tmp_path, minor_data):
    # Alleen pipeline-orchestratie: dit bevestigt GEEN echte site-paginering.
    import scraper.pipeline as pipeline
    second_url = minor_data["url"].replace("/123/", "/456/")
    first = Minor.model_validate(minor_data)
    second = Minor.model_validate({**minor_data, "id": stable_id(second_url), "url": second_url})
    fake_get(monkeypatch, [robots_response(), response(text="list1"), response(text="detail1"),
                           response(text="list2"), response(text="detail2")])
    monkeypatch.setattr(pipeline, "parse_listing", Mock(side_effect=[Listing([first.url], SOURCE + "?page=2"), Listing([second.url])]))
    monkeypatch.setattr(pipeline, "parse_detail", Mock(side_effect=[first, second]))
    report = run_scrape(2, tmp_path, delay=0)
    assert report["records_valid"] == 2
    assert report["pages_requested"] == report["pages_succeeded"] == 5
    assert len(load_minors(tmp_path / "minors.json")) == 2


def test_invalid_extracted_record_is_counted_and_partial_data_validated(monkeypatch, tmp_path, minor_data):
    import scraper.pipeline as pipeline
    second_url = minor_data["url"].replace("/123/", "/456/")
    fake_get(monkeypatch, [robots_response(), response(text="listing"), response(text="detail1"), response(text="detail2")])
    monkeypatch.setattr(pipeline, "parse_listing", Mock(return_value=Listing([minor_data["url"], second_url])))
    monkeypatch.setattr(pipeline, "parse_detail", Mock(side_effect=[minor_data, {"title": "incomplete"}]))
    report = run_scrape(5, tmp_path, delay=0)
    assert report["status"] == "partial"
    assert report["records_extracted"] == 2
    assert report["records_rejected"] == report["records_valid"] == 1
    assert len(load_minors(tmp_path / "minors.json")) == 1
