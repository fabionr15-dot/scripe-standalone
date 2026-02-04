"""Export utilities for lead data."""

import csv
import json
from pathlib import Path
from typing import Any

from app.logging_config import get_logger
from app.storage.models import Company

logger = get_logger(__name__)


def export_to_csv(companies: list[Company], output_path: Path) -> None:
    """Export companies to CSV format.

    Args:
        companies: List of company records
        output_path: Output file path
    """
    if not companies:
        logger.warning("no_companies_to_export")
        return

    fieldnames = [
        "company_name",
        "website",
        "phone",
        "address_line",
        "postal_code",
        "city",
        "region",
        "country",
        "category",
        "keywords_matched",
        "match_score",
        "confidence_score",
        "created_at",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for company in companies:
            row = {
                "company_name": company.company_name,
                "website": company.website or "",
                "phone": company.phone or "",
                "address_line": company.address_line or "",
                "postal_code": company.postal_code or "",
                "city": company.city or "",
                "region": company.region or "",
                "country": company.country or "",
                "category": company.category or "",
                "keywords_matched": company.keywords_matched or "",
                "match_score": f"{company.match_score:.3f}",
                "confidence_score": f"{company.confidence_score:.3f}",
                "created_at": company.created_at.isoformat(),
            }
            writer.writerow(row)

    logger.info("csv_export_completed", path=str(output_path), count=len(companies))


def export_to_jsonl(companies: list[Company], output_path: Path) -> None:
    """Export companies to JSONL format (one JSON object per line).

    Args:
        companies: List of company records
        output_path: Output file path
    """
    if not companies:
        logger.warning("no_companies_to_export")
        return

    with open(output_path, "w", encoding="utf-8") as jsonlfile:
        for company in companies:
            record = {
                "id": company.id,
                "company_name": company.company_name,
                "website": company.website,
                "phone": company.phone,
                "address_line": company.address_line,
                "postal_code": company.postal_code,
                "city": company.city,
                "region": company.region,
                "country": company.country,
                "category": company.category,
                "keywords_matched": company.keywords_matched,
                "match_score": company.match_score,
                "confidence_score": company.confidence_score,
                "created_at": company.created_at.isoformat(),
            }
            jsonlfile.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("jsonl_export_completed", path=str(output_path), count=len(companies))


def export_with_sources(companies: list[Company], output_path: Path) -> None:
    """Export companies with full source attribution to JSON.

    Args:
        companies: List of company records
        output_path: Output file path
    """
    if not companies:
        logger.warning("no_companies_to_export")
        return

    export_data = []

    for company in companies:
        record: dict[str, Any] = {
            "id": company.id,
            "company_name": company.company_name,
            "website": company.website,
            "phone": company.phone,
            "address": {
                "address_line": company.address_line,
                "postal_code": company.postal_code,
                "city": company.city,
                "region": company.region,
                "country": company.country,
            },
            "category": company.category,
            "keywords_matched": company.keywords_matched,
            "scores": {
                "match_score": company.match_score,
                "confidence_score": company.confidence_score,
            },
            "created_at": company.created_at.isoformat(),
            "sources": [],
        }

        # Add source evidence
        for source in company.sources:
            record["sources"].append(
                {
                    "source_name": source.source_name,
                    "source_url": source.source_url,
                    "field_name": source.field_name,
                    "evidence_snippet": source.evidence_snippet,
                    "retrieved_at": source.retrieved_at.isoformat(),
                }
            )

        export_data.append(record)

    with open(output_path, "w", encoding="utf-8") as jsonfile:
        json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)

    logger.info("json_with_sources_export_completed", path=str(output_path), count=len(companies))
