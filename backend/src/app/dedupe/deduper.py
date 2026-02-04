"""Deduplication and record merging."""

from typing import Any

from app.extractors.normalizers import CompanyNameNormalizer, WebsiteNormalizer
from app.logging_config import get_logger

logger = get_logger(__name__)


class CompanyDeduplicator:
    """Deduplicate and merge company records."""

    def __init__(self):
        """Initialize deduplicator."""
        self.name_normalizer = CompanyNameNormalizer()
        self.website_normalizer = WebsiteNormalizer()

    def are_duplicates(
        self,
        company1: dict[str, Any],
        company2: dict[str, Any],
    ) -> bool:
        """Check if two companies are duplicates.

        Matching criteria (any match = duplicate):
        1. Same normalized website domain
        2. Same normalized phone number
        3. Same normalized company name + same city

        Args:
            company1: First company data
            company2: Second company data

        Returns:
            True if duplicates
        """
        # 1. Website domain match
        website1 = company1.get("website")
        website2 = company2.get("website")

        if website1 and website2:
            domain1 = self.website_normalizer.extract_domain(website1)
            domain2 = self.website_normalizer.extract_domain(website2)

            if domain1 and domain2 and domain1 == domain2:
                logger.debug(
                    "duplicate_found_by_website",
                    domain=domain1,
                    name1=company1.get("company_name"),
                    name2=company2.get("company_name"),
                )
                return True

        # 2. Phone match
        phone1 = company1.get("phone")
        phone2 = company2.get("phone")

        if phone1 and phone2 and phone1 == phone2:
            logger.debug(
                "duplicate_found_by_phone",
                phone=phone1,
                name1=company1.get("company_name"),
                name2=company2.get("company_name"),
            )
            return True

        # 3. Name + city match
        name1 = company1.get("company_name", "")
        name2 = company2.get("company_name", "")
        city1 = company1.get("city", "")
        city2 = company2.get("city", "")

        if name1 and name2 and city1 and city2:
            norm_name1 = self.name_normalizer.normalize_for_deduplication(name1)
            norm_name2 = self.name_normalizer.normalize_for_deduplication(name2)

            if norm_name1 and norm_name2 and norm_name1 == norm_name2:
                if city1.lower() == city2.lower():
                    logger.debug(
                        "duplicate_found_by_name_city",
                        name=norm_name1,
                        city=city1,
                    )
                    return True

        return False

    def merge_companies(
        self,
        company1: dict[str, Any],
        company2: dict[str, Any],
        source_priority: list[str] | None = None,
    ) -> dict[str, Any]:
        """Merge two duplicate company records.

        Merge strategy:
        - Prefer non-null values
        - Use source_priority to resolve conflicts
        - Take highest match_score and confidence_score
        - Concatenate keywords_matched

        Args:
            company1: First company (base)
            company2: Second company (to merge in)
            source_priority: List of source names in priority order

        Returns:
            Merged company data
        """
        merged = company1.copy()

        # Default source priority
        if not source_priority:
            source_priority = [
                "google_places",
                "official_website",
                "business_directory",
                "nominatim",
            ]

        # Determine which source has priority
        source1 = company1.get("source_name", "")
        source2 = company2.get("source_name", "")

        try:
            priority1 = source_priority.index(source1) if source1 in source_priority else 999
            priority2 = source_priority.index(source2) if source2 in source_priority else 999
            use_source2 = priority2 < priority1
        except ValueError:
            use_source2 = False

        # Merge fields
        fields_to_merge = [
            "company_name",
            "website",
            "phone",
            "address_line",
            "postal_code",
            "city",
            "region",
            "country",
            "category",
        ]

        for field in fields_to_merge:
            value1 = merged.get(field)
            value2 = company2.get(field)

            if not value1 and value2:
                # Fill missing field
                merged[field] = value2
            elif value1 and value2 and use_source2:
                # Replace with higher priority source
                merged[field] = value2

        # Merge keywords (concatenate unique)
        keywords1 = set(merged.get("keywords_matched", "").split(","))
        keywords2 = set(company2.get("keywords_matched", "").split(","))
        all_keywords = keywords1.union(keywords2)
        merged["keywords_matched"] = ",".join(sorted(filter(None, all_keywords)))

        # Take maximum scores
        merged["match_score"] = max(
            merged.get("match_score", 0.0),
            company2.get("match_score", 0.0),
        )
        merged["confidence_score"] = max(
            merged.get("confidence_score", 0.0),
            company2.get("confidence_score", 0.0),
        )

        logger.debug(
            "companies_merged",
            name=merged.get("company_name"),
            source1=source1,
            source2=source2,
        )

        return merged

    def deduplicate_batch(
        self,
        companies: list[dict[str, Any]],
        source_priority: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Deduplicate a batch of companies.

        Args:
            companies: List of company dicts
            source_priority: Source priority for merging

        Returns:
            Deduplicated list
        """
        if not companies:
            return []

        deduplicated = []
        seen_indices = set()

        for i, company1 in enumerate(companies):
            if i in seen_indices:
                continue

            # Start with company1 as base
            merged = company1.copy()

            # Check all subsequent companies for duplicates
            for j in range(i + 1, len(companies)):
                if j in seen_indices:
                    continue

                company2 = companies[j]

                if self.are_duplicates(merged, company2):
                    # Merge company2 into merged
                    merged = self.merge_companies(merged, company2, source_priority)
                    seen_indices.add(j)

            deduplicated.append(merged)

        logger.info(
            "batch_deduplicated",
            original_count=len(companies),
            deduplicated_count=len(deduplicated),
            removed_count=len(companies) - len(deduplicated),
        )

        return deduplicated
