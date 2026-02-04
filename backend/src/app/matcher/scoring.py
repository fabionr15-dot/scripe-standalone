"""Company matching and scoring algorithms."""

import re
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


class CompanyScorer:
    """Calculate match and confidence scores for companies."""

    def __init__(self, criteria: dict[str, Any]):
        """Initialize scorer with search criteria.

        Args:
            criteria: Search criteria dict containing:
                - keywords_include: List of required keywords
                - keywords_exclude: List of excluded keywords
                - categories: List of target categories
                - regions: List of target regions
                - cities: List of target cities
        """
        self.criteria = criteria
        self.keywords_include = [k.lower() for k in criteria.get("keywords_include", [])]
        self.keywords_exclude = [k.lower() for k in criteria.get("keywords_exclude", [])]
        self.categories = [c.lower() for c in criteria.get("categories", [])]
        self.regions = [r.lower() for r in criteria.get("regions", [])]
        self.cities = [c.lower() for c in criteria.get("cities", [])]

    def calculate_match_score(
        self,
        company_name: str,
        category: str | None,
        region: str | None,
        city: str | None,
        website: str | None = None,
        description: str | None = None,
    ) -> float:
        """Calculate match score (0-1) based on criteria.

        Weights:
        - Category match: 0.4
        - Keyword match: 0.3
        - Region/city match: 0.2
        - Additional signals: 0.1

        Args:
            company_name: Company name
            category: Business category
            region: Region/state
            city: City
            website: Website URL
            description: Company description

        Returns:
            Match score between 0 and 1
        """
        score = 0.0

        # Prepare searchable text
        searchable_text = " ".join(
            filter(
                None,
                [
                    company_name.lower() if company_name else "",
                    category.lower() if category else "",
                    description.lower() if description else "",
                ],
            )
        )

        # 1. Category matching (weight: 0.4)
        category_score = 0.0
        if category and self.categories:
            category_lower = category.lower()
            for target_category in self.categories:
                if target_category in category_lower:
                    category_score = 1.0
                    break
        elif not self.categories:
            # No category filter, give neutral score
            category_score = 0.5

        score += category_score * 0.4

        # 2. Keyword matching (weight: 0.3)
        keyword_score = 0.0

        # Check included keywords
        if self.keywords_include:
            matched_keywords = []
            for keyword in self.keywords_include:
                if re.search(r"\b" + re.escape(keyword) + r"\b", searchable_text):
                    matched_keywords.append(keyword)

            keyword_score = len(matched_keywords) / len(self.keywords_include)
        else:
            keyword_score = 0.5  # Neutral if no keywords specified

        # Check excluded keywords (disqualifies)
        for keyword in self.keywords_exclude:
            if re.search(r"\b" + re.escape(keyword) + r"\b", searchable_text):
                logger.debug("excluded_keyword_found", keyword=keyword, company=company_name)
                return 0.0  # Immediate disqualification

        score += keyword_score * 0.3

        # 3. Geographic matching (weight: 0.2)
        geo_score = 0.0

        # Region match
        if region and self.regions:
            region_lower = region.lower()
            for target_region in self.regions:
                if target_region in region_lower:
                    geo_score += 0.6
                    break

        # City match
        if city and self.cities:
            city_lower = city.lower()
            for target_city in self.cities:
                if target_city in city_lower:
                    geo_score += 0.4
                    break

        if not self.regions and not self.cities:
            geo_score = 0.5  # Neutral if no geo filter

        score += min(geo_score, 1.0) * 0.2

        # 4. Additional signals (weight: 0.1)
        signal_score = 0.0
        if website:
            signal_score += 0.5
        if description:
            signal_score += 0.5

        score += min(signal_score, 1.0) * 0.1

        return min(score, 1.0)

    def calculate_confidence_score(
        self,
        source_name: str,
        has_phone: bool,
        has_website: bool,
        has_address: bool,
        phone_source: str | None = None,
        multiple_sources: bool = False,
    ) -> float:
        """Calculate confidence score (0-1) based on data quality.

        Args:
            source_name: Primary data source
            has_phone: Whether phone is present
            has_website: Whether website is present
            has_address: Whether address is present
            phone_source: Specific source of phone data
            multiple_sources: Whether data is confirmed by multiple sources

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0

        # Base score by source quality
        source_quality = {
            "google_places": 0.9,
            "official_website": 0.85,
            "business_directory": 0.7,
            "nominatim": 0.6,
        }
        score += source_quality.get(source_name, 0.5)

        # Adjust for data completeness
        if has_phone:
            score += 0.05
        if has_website:
            score += 0.05
        if has_address:
            score += 0.05

        # Boost for high-quality phone source
        if phone_source == "official_website":
            score += 0.1
        elif phone_source == "google_places":
            score += 0.08

        # Boost for multiple source confirmation
        if multiple_sources:
            score += 0.1

        return min(score, 1.0)

    def passes_quality_requirements(
        self,
        match_score: float,
        confidence_score: float,
        has_phone: bool,
        has_website: bool,
    ) -> bool:
        """Check if company passes minimum quality requirements.

        Args:
            match_score: Calculated match score
            confidence_score: Calculated confidence score
            has_phone: Whether phone is present
            has_website: Whether website is present

        Returns:
            True if passes requirements
        """
        min_match = self.criteria.get("min_match_score", 0.4)
        min_confidence = self.criteria.get("min_confidence_score", 0.5)
        require_phone = self.criteria.get("require_phone", True)
        require_website = self.criteria.get("require_website", True)

        if match_score < min_match:
            return False

        if confidence_score < min_confidence:
            return False

        if require_phone and not has_phone:
            return False

        if require_website and not has_website:
            return False

        return True
