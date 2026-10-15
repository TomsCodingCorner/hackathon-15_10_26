"""CLI, validatie en veilige opslag. Bronparsing is expliciet nog geblokkeerd."""

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .fetcher import FetchError, Fetcher
from .models import Minor, SOURCE
from .parser import SourceStructureUnavailable, parse_detail, parse_listing


def load_minors(path: str | Path = "data/minors.json") -> list[dict]:
    """Lees en valideer data, zonder scraping of imports uit de AI-module."""
    with Path(path).open(encoding="utf-8") as file:
        rows = json.load(file)
    if not isinstance(rows, list):
        raise ValueError("Minorbestand moet een JSON-array zijn.")
    minors = [Minor.model_validate(row) for row in rows]
    unique, duplicates = deduplicate(minors)
    if duplicates:
        raise ValueError("Minorbestand bevat dubbele ID's of canonieke URL's.")
    return [minor.model_dump() for minor in unique]


def deduplicate(minors: list[Minor]) -> tuple[list[Minor], int]:
    unique, seen_ids, seen_urls = [], set(), set()
    for minor in minors:
        if minor.id in seen_ids or minor.url in seen_urls:
            continue
        seen_ids.add(minor.id)
        seen_urls.add(minor.url)
        unique.append(minor)
    return unique, len(minors) - len(unique)


def _write_json(path: Path, value: object) -> None:
    """Atomair vervangen; een schrijffout laat de vorige dataset intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_scrape(limit: int = 100, output_dir: str | Path = "data", *, delay: float = 1.5,
               timeout: float = 20, retries: int = 2) -> dict:
    if not 1 <= limit <= 10_000:
        raise ValueError("Limit moet tussen 1 en 10000 liggen.")
    folder = Path(output_dir)
    report = {
        "source": SOURCE, "scraped_at": datetime.now(timezone.utc).isoformat(),
        "requested_limit": limit, "status": "failed", "pages_requested": 0,
        "pages_succeeded": 0, "records_extracted": 0, "records_valid": 0,
        "duplicates_removed": 0, "records_rejected": 0, "errors": [],
        "duplicate_urls_skipped": 0,
        "dataset_updated": False, "empty_dataset_initialized": False,
        "parser_verified_on_production": False,
    }
    fetcher = Fetcher(delay=delay, timeout=timeout, retries=retries)
    candidates: list[Minor] = []
    visited_pages, visited_details = set(), set()

    def error(code: str, url: str, status: int | None = None) -> None:
        report["errors"].append({"code": code, "url": url, "http_status": status})

    try:
        fetcher.load_robots()
        next_url: str | None = SOURCE
        while next_url and len(candidates) < limit:
            if next_url in visited_pages:
                error("pagination_loop", next_url)
                break
            visited_pages.add(next_url)
            listing = parse_listing(fetcher.get(next_url), next_url)
            for url in listing.detail_urls:
                if url in visited_details:
                    report["duplicate_urls_skipped"] += 1
                    continue
                visited_details.add(url)
                try:
                    html = fetcher.get(url)
                    raw_record = parse_detail(html, url)
                    report["records_extracted"] += 1
                    candidates.append(Minor.model_validate(raw_record))
                except ValidationError:
                    report["records_rejected"] += 1
                    error("invalid_minor_record", url)
                except SourceStructureUnavailable as exc:
                    error(str(exc), url)
                    raise
                except FetchError as exc:
                    error(exc.code, exc.url, exc.status)
                    if exc.code in {"access_restricted", "browser_challenge"}:
                        raise
                if len(candidates) >= limit:
                    break
            next_url = listing.next_url
    except FetchError as exc:
        if not report["errors"] or report["errors"][-1]["code"] != exc.code:
            error(exc.code, exc.url, exc.status)
        if exc.code in {"access_restricted", "browser_challenge", "robots_denied_or_unavailable"}:
            report["status"] = "blocked"
    except SourceStructureUnavailable as exc:
        if not report["errors"] or report["errors"][-1]["code"] != str(exc):
            error(str(exc), SOURCE)
        report["status"] = "blocked"
    finally:
        fetcher.close()
        report["pages_requested"] = fetcher.stats.pages_requested
        report["pages_succeeded"] = fetcher.stats.pages_succeeded

    unique, duplicates = deduplicate(candidates)
    report["duplicates_removed"] += duplicates
    report["records_valid"] = len(unique)
    dataset_path = folder / "minors.json"
    if unique:
        _write_json(dataset_path, [minor.model_dump() for minor in unique])
        report["dataset_updated"] = True
        report["status"] = "partial" if report["errors"] else "success"
    elif not dataset_path.exists():
        # [] betekent letterlijk nul bronrecords; het is geen fallbackcatalogus.
        _write_json(dataset_path, [])
        report["empty_dataset_initialized"] = True
    _write_json(folder / "scrape_report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kies op Maat: veilige ingestion (productieparser nog geblokkeerd).")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        report = run_scrape(args.limit, args.output_dir, delay=args.delay, timeout=args.timeout, retries=args.retries)
    except (OSError, ValueError):
        parser.exit(2, "Ongeldige configuratie of uitvoerbestanden niet schrijfbaar.\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
