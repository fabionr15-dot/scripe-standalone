"""Export utilities for companies data."""

import csv
import json
from pathlib import Path
from typing import Any, Literal

from scripe.logging_config import get_logger
from scripe.storage.models import Company

logger = get_logger(__name__)


class Exporter:
    """Export companies to various formats."""

    @staticmethod
    def to_csv(companies: list[Company], output_path: Path) -> None:
        """Export companies to CSV."""
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
            "match_score",
            "confidence_score",
            "sources",
            "created_at",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for company in companies:
                # Collect source info
                sources_info = "; ".join(
                    [f"{s.source_name} ({s.field_name})" for s in company.sources]
                )

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
                    "match_score": f"{company.match_score:.3f}",
                    "confidence_score": f"{company.confidence_score:.3f}",
                    "sources": sources_info,
                    "created_at": company.created_at.isoformat(),
                }
                writer.writerow(row)

        logger.info("csv_exported", path=str(output_path), count=len(companies))

    @staticmethod
    def to_jsonl(companies: list[Company], output_path: Path) -> None:
        """Export companies to JSONL."""
        if not companies:
            logger.warning("no_companies_to_export")
            return

        with open(output_path, "w", encoding="utf-8") as f:
            for company in companies:
                record: dict[str, Any] = {
                    "company_name": company.company_name,
                    "website": company.website,
                    "phone": company.phone,
                    "address_line": company.address_line,
                    "postal_code": company.postal_code,
                    "city": company.city,
                    "region": company.region,
                    "country": company.country,
                    "category": company.category,
                    "match_score": company.match_score,
                    "confidence_score": company.confidence_score,
                    "created_at": company.created_at.isoformat(),
                    "sources": [
                        {
                            "source_name": s.source_name,
                            "source_url": s.source_url,
                            "field_name": s.field_name,
                            "evidence_snippet": s.evidence_snippet,
                            "retrieved_at": s.retrieved_at.isoformat(),
                        }
                        for s in company.sources
                    ],
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info("jsonl_exported", path=str(output_path), count=len(companies))

    @staticmethod
    def export(
        companies: list[Company],
        output_path: Path,
        format: Literal["csv", "jsonl"] = "csv",
    ) -> None:
        """Export companies in specified format."""
        if format == "csv":
            Exporter.to_csv(companies, output_path)
        elif format == "jsonl":
            Exporter.to_jsonl(companies, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
