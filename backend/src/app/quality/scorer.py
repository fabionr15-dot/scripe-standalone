"""Quality scoring engine for lead data."""

from dataclasses import dataclass, field
from typing import Any

from app.logging_config import get_logger
from app.quality.tiers import QualityTier, TIER_CONFIG

logger = get_logger(__name__)


@dataclass
class QualityScore:
    """Detailed quality score breakdown."""

    # Overall scores (0-1)
    quality_score: float = 0.0
    match_score: float = 0.0
    confidence_score: float = 0.0

    # Component scores
    completeness_score: float = 0.0
    validation_score: float = 0.0
    source_score: float = 0.0

    # Individual field scores
    field_scores: dict[str, float] = field(default_factory=dict)

    # Validation results
    phone_validated: bool = False
    email_validated: bool = False
    website_validated: bool = False

    # Metadata
    sources_count: int = 0
    enriched: bool = False
    tier: QualityTier = QualityTier.BASIC

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "quality_score": round(self.quality_score, 3),
            "match_score": round(self.match_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "completeness_score": round(self.completeness_score, 3),
            "validation_score": round(self.validation_score, 3),
            "source_score": round(self.source_score, 3),
            "field_scores": {k: round(v, 3) for k, v in self.field_scores.items()},
            "phone_validated": self.phone_validated,
            "email_validated": self.email_validated,
            "website_validated": self.website_validated,
            "sources_count": self.sources_count,
            "enriched": self.enriched,
            "tier": self.tier.value,
        }


# Field weights for scoring
FIELD_WEIGHTS = {
    "company_name": 0.15,
    "phone": 0.20,
    "email": 0.15,
    "website": 0.15,
    "address": 0.10,
    "city": 0.10,
    "category": 0.10,
    "description": 0.05,
}

# Validation weights
VALIDATION_WEIGHTS = {
    "phone": 0.4,
    "email": 0.3,
    "website": 0.3,
}


class QualityScorer:
    """Calculates quality scores for lead data.

    Scoring factors:
    1. Completeness: How many fields are filled
    2. Validation: How many fields are validated (format, existence)
    3. Source confidence: Reliability of data sources
    4. Match: How well the lead matches search criteria
    """

    def __init__(self):
        """Initialize scorer."""
        self.logger = get_logger(__name__)

    def score(
        self,
        data: dict[str, Any],
        search_criteria: dict[str, Any] | None = None,
        source_confidence: float = 0.7,
        validation_results: dict[str, bool] | None = None,
    ) -> QualityScore:
        """Calculate quality score for lead data.

        Args:
            data: Lead data dictionary
            search_criteria: Optional search criteria for match scoring
            source_confidence: Base confidence from data source (0-1)
            validation_results: Optional validation results

        Returns:
            Detailed quality score
        """
        result = QualityScore()
        validation_results = validation_results or {}

        # 1. Calculate completeness score
        result.completeness_score, result.field_scores = self._calc_completeness(data)

        # 2. Calculate validation score
        result.validation_score = self._calc_validation_score(
            data, validation_results
        )
        result.phone_validated = validation_results.get("phone", False)
        result.email_validated = validation_results.get("email", False)
        result.website_validated = validation_results.get("website", False)

        # 3. Calculate source score
        result.source_score = source_confidence
        result.sources_count = data.get("sources_count", 1)

        # 4. Calculate match score (if criteria provided)
        if search_criteria:
            result.match_score = self._calc_match_score(data, search_criteria)
        else:
            result.match_score = 0.5  # Neutral if no criteria

        # 5. Calculate overall quality score
        # Weighted combination
        result.quality_score = (
            result.completeness_score * 0.35 +
            result.validation_score * 0.30 +
            result.source_score * 0.20 +
            result.match_score * 0.15
        )

        # 6. Calculate confidence score
        # Confidence is affected by validation and source reliability
        result.confidence_score = (
            result.source_score * 0.5 +
            result.validation_score * 0.5
        )

        # 7. Determine tier
        result.tier = QualityTier.from_score(result.quality_score)

        # 8. Check if enriched
        result.enriched = data.get("enriched", False) or data.get("sources_count", 1) > 1

        return result

    def _calc_completeness(self, data: dict[str, Any]) -> tuple[float, dict[str, float]]:
        """Calculate completeness score.

        Args:
            data: Lead data

        Returns:
            Tuple of (overall_score, field_scores)
        """
        field_scores = {}
        total_weight = 0
        weighted_sum = 0

        # Check each field
        field_mappings = {
            "company_name": ["company_name", "name"],
            "phone": ["phone", "telephone", "tel"],
            "email": ["email", "mail"],
            "website": ["website", "url", "web"],
            "address": ["address_line", "address", "street"],
            "city": ["city", "locality"],
            "category": ["category", "business_type", "type"],
            "description": ["description", "about", "notes"],
        }

        for field_name, possible_keys in field_mappings.items():
            weight = FIELD_WEIGHTS.get(field_name, 0.1)
            total_weight += weight

            # Check if any key has a value
            value = None
            for key in possible_keys:
                if key in data and data[key]:
                    value = data[key]
                    break

            if value:
                # Score based on value quality
                score = self._score_field_value(field_name, value)
                field_scores[field_name] = score
                weighted_sum += weight * score
            else:
                field_scores[field_name] = 0.0

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        return overall, field_scores

    def _score_field_value(self, field_name: str, value: Any) -> float:
        """Score a field value based on quality.

        Args:
            field_name: Field name
            value: Field value

        Returns:
            Score (0-1)
        """
        if not value:
            return 0.0

        value_str = str(value).strip()

        if not value_str:
            return 0.0

        # Base score for having a value
        score = 0.5

        # Field-specific scoring
        if field_name == "company_name":
            # Longer names are usually more complete
            if len(value_str) >= 5:
                score += 0.3
            if len(value_str) >= 15:
                score += 0.2

        elif field_name == "phone":
            # Check for reasonable length
            digits = "".join(c for c in value_str if c.isdigit())
            if 8 <= len(digits) <= 15:
                score += 0.5

        elif field_name == "email":
            # Basic email format check
            if "@" in value_str and "." in value_str.split("@")[-1]:
                score += 0.5

        elif field_name == "website":
            # Check for reasonable URL
            if "." in value_str:
                score += 0.3
            if value_str.startswith(("http://", "https://")):
                score += 0.2

        elif field_name == "address":
            # Longer addresses are usually more complete
            if len(value_str) >= 10:
                score += 0.3
            if len(value_str) >= 30:
                score += 0.2

        elif field_name == "city":
            if len(value_str) >= 3:
                score += 0.5

        elif field_name == "category":
            if len(value_str) >= 3:
                score += 0.5

        elif field_name == "description":
            if len(value_str) >= 20:
                score += 0.3
            if len(value_str) >= 100:
                score += 0.2

        return min(1.0, score)

    def _calc_validation_score(
        self,
        data: dict[str, Any],
        validation_results: dict[str, bool],
    ) -> float:
        """Calculate validation score.

        Args:
            data: Lead data
            validation_results: Validation results

        Returns:
            Validation score (0-1)
        """
        total_weight = 0
        weighted_sum = 0

        for field, weight in VALIDATION_WEIGHTS.items():
            # Check if field has a value
            has_value = bool(data.get(field))

            if has_value:
                total_weight += weight
                # If validated, full weight; if not validated but has value, half weight
                if validation_results.get(field, False):
                    weighted_sum += weight
                else:
                    weighted_sum += weight * 0.5  # Partial credit for having value

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calc_match_score(
        self,
        data: dict[str, Any],
        criteria: dict[str, Any],
    ) -> float:
        """Calculate how well data matches search criteria.

        Args:
            data: Lead data
            criteria: Search criteria

        Returns:
            Match score (0-1)
        """
        scores = []

        # Category match
        if "categories" in criteria and criteria["categories"]:
            data_category = str(data.get("category", "")).lower()
            for cat in criteria["categories"]:
                if cat.lower() in data_category:
                    scores.append(1.0)
                    break
            else:
                scores.append(0.3)

        # Location match
        if "cities" in criteria and criteria["cities"]:
            data_city = str(data.get("city", "")).lower()
            for city in criteria["cities"]:
                if city.lower() in data_city or data_city in city.lower():
                    scores.append(1.0)
                    break
            else:
                scores.append(0.3)

        elif "regions" in criteria and criteria["regions"]:
            data_region = str(data.get("region", "")).lower()
            for region in criteria["regions"]:
                if region.lower() in data_region:
                    scores.append(1.0)
                    break
            else:
                scores.append(0.5)

        # Keyword include match
        if "keywords_include" in criteria and criteria["keywords_include"]:
            data_text = " ".join(str(v) for v in data.values() if v).lower()
            match_count = sum(1 for kw in criteria["keywords_include"] if kw.lower() in data_text)
            scores.append(match_count / len(criteria["keywords_include"]))

        # Keyword exclude check
        if "keywords_exclude" in criteria and criteria["keywords_exclude"]:
            data_text = " ".join(str(v) for v in data.values() if v).lower()
            exclude_match = any(kw.lower() in data_text for kw in criteria["keywords_exclude"])
            if exclude_match:
                scores.append(0.0)  # Penalize if excluded keyword found
            else:
                scores.append(1.0)

        return sum(scores) / len(scores) if scores else 0.5

    def meets_tier_requirements(
        self,
        score: QualityScore,
        tier: QualityTier,
    ) -> bool:
        """Check if score meets tier requirements.

        Args:
            score: Quality score
            tier: Target tier

        Returns:
            True if meets requirements
        """
        config = TIER_CONFIG[tier]
        return score.quality_score >= config.min_score

    def get_improvement_suggestions(
        self,
        score: QualityScore,
        target_tier: QualityTier | None = None,
    ) -> list[str]:
        """Get suggestions to improve quality score.

        Args:
            score: Current quality score
            target_tier: Optional target tier

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Low field scores
        for field, field_score in score.field_scores.items():
            if field_score < 0.5:
                suggestions.append(f"Aggiungi o completa il campo '{field}'")

        # Validation suggestions
        if not score.phone_validated and score.field_scores.get("phone", 0) > 0:
            suggestions.append("Valida il numero di telefono")

        if not score.email_validated and score.field_scores.get("email", 0) > 0:
            suggestions.append("Valida l'indirizzo email")

        if not score.website_validated and score.field_scores.get("website", 0) > 0:
            suggestions.append("Verifica il sito web")

        # Source suggestions
        if score.sources_count < 2:
            suggestions.append("Arricchisci i dati da fonti aggiuntive")

        # Target tier suggestions
        if target_tier:
            config = TIER_CONFIG[target_tier]
            score_gap = config.min_score - score.quality_score
            if score_gap > 0:
                suggestions.append(
                    f"Aumenta il punteggio di {score_gap:.1%} per raggiungere il tier {target_tier.value}"
                )

        return suggestions[:5]  # Max 5 suggestions
