"""Lead quality scoring system (0-100)."""

from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


class LeadQualityScorer:
    """Calculate comprehensive lead quality score (0-100).

    Scoring components:
    - Data completeness: 30 points
    - Data validation: 25 points
    - Source reliability: 20 points
    - Match quality: 15 points
    - Freshness: 10 points
    """

    def calculate_quality_score(
        self,
        company_data: dict[str, Any],
        validation_results: dict[str, Any] | None = None,
        match_score: float = 0.0,
        confidence_score: float = 0.0,
    ) -> int:
        """Calculate overall lead quality score.

        Args:
            company_data: Company information
            validation_results: Optional validation results
            match_score: Match score from matcher (0-1)
            confidence_score: Confidence score from matcher (0-1)

        Returns:
            Quality score 0-100
        """
        score = 0

        # 1. DATA COMPLETENESS (30 points)
        score += self._score_completeness(company_data)

        # 2. DATA VALIDATION (25 points)
        if validation_results:
            score += self._score_validation(validation_results)
        else:
            # If no validation, give partial credit based on format
            score += self._score_format_validation(company_data)

        # 3. SOURCE RELIABILITY (20 points)
        score += self._score_source_reliability(company_data, confidence_score)

        # 4. MATCH QUALITY (15 points)
        score += self._score_match_quality(match_score)

        # 5. FRESHNESS (10 points)
        score += self._score_freshness(company_data)

        # Ensure 0-100 range
        final_score = max(0, min(100, score))

        logger.debug(
            "quality_score_calculated",
            company=company_data.get("company_name"),
            score=final_score,
        )

        return final_score

    def _score_completeness(self, data: dict[str, Any]) -> int:
        """Score data completeness (0-30 points).

        Required fields:
        - Company name: 5 points
        - Phone: 8 points
        - Email: 8 points
        - Website: 5 points
        - Address: 4 points
        """
        score = 0

        # Company name (required)
        if data.get("company_name"):
            score += 5

        # Phone (high value for cold calling)
        if data.get("phone"):
            score += 8

        # Email (high value for email outreach)
        if data.get("email"):
            score += 8

        # Website (good for research)
        if data.get("website"):
            score += 5

        # Address components
        if data.get("address_line"):
            score += 2
        if data.get("city"):
            score += 1
        if data.get("postal_code"):
            score += 1

        return score

    def _score_validation(self, validation: dict[str, Any]) -> int:
        """Score based on validation results (0-25 points).

        Args:
            validation: Dict with phone_valid, email_valid, website_valid

        Returns:
            Validation score
        """
        score = 0

        # Phone validation (10 points)
        phone_validation = validation.get("phone", {})
        if phone_validation.get("valid"):
            score += 7
            if phone_validation.get("type") == "mobile":
                score += 3  # Mobile preferred

        # Email validation (10 points)
        email_validation = validation.get("email", {})
        if email_validation.get("valid"):
            score += 5
            if email_validation.get("deliverable"):
                score += 3
            if not email_validation.get("disposable"):
                score += 2

        # Website validation (5 points)
        website_validation = validation.get("website", {})
        if website_validation.get("accessible"):
            score += 3
        if website_validation.get("ssl_valid"):
            score += 2

        return score

    def _score_format_validation(self, data: dict[str, Any]) -> int:
        """Basic format validation without external checks (0-15 points).

        Args:
            data: Company data

        Returns:
            Format score
        """
        score = 0

        # Phone format check
        phone = data.get("phone")
        if phone and phone.startswith("+") and len(phone) >= 10:
            score += 5

        # Email format check
        email = data.get("email")
        if email and "@" in email and "." in email.split("@")[1]:
            score += 5

        # Website format check
        website = data.get("website")
        if website and (website.startswith("http://") or website.startswith("https://")):
            score += 5

        return score

    def _score_source_reliability(
        self, data: dict[str, Any], confidence_score: float
    ) -> int:
        """Score based on data source reliability (0-20 points).

        Args:
            data: Company data
            confidence_score: Confidence score from matcher (0-1)

        Returns:
            Source reliability score
        """
        # Use confidence score from matcher
        base_score = int(confidence_score * 15)

        # Bonus for multiple sources
        source_count = data.get("source_count", 1)
        if source_count > 1:
            base_score += 5

        return min(20, base_score)

    def _score_match_quality(self, match_score: float) -> int:
        """Score based on match quality (0-15 points).

        Args:
            match_score: Match score from matcher (0-1)

        Returns:
            Match quality score
        """
        return int(match_score * 15)

    def _score_freshness(self, data: dict[str, Any]) -> int:
        """Score based on data freshness (0-10 points).

        Args:
            data: Company data with potential created_at

        Returns:
            Freshness score
        """
        # If data just collected, give full points
        # This is a placeholder - in production, check created_at timestamp

        # For now, give full points as all data is fresh
        return 10

    def get_quality_category(self, score: int) -> str:
        """Get quality category from score.

        Args:
            score: Quality score (0-100)

        Returns:
            Category name
        """
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"

    def get_quality_color(self, score: int) -> str:
        """Get color for quality score visualization.

        Args:
            score: Quality score (0-100)

        Returns:
            Color code
        """
        if score >= 80:
            return "#28a745"  # Green
        elif score >= 60:
            return "#ffc107"  # Yellow
        elif score >= 40:
            return "#fd7e14"  # Orange
        else:
            return "#dc3545"  # Red

    def explain_score(self, score: int, breakdown: dict[str, int]) -> str:
        """Generate human-readable score explanation.

        Args:
            score: Total score
            breakdown: Dict with component scores

        Returns:
            Explanation text
        """
        category = self.get_quality_category(score)

        explanation = f"Quality Score: {score}/100 ({category.upper()})\n\n"
        explanation += "Breakdown:\n"

        if "completeness" in breakdown:
            explanation += f"- Data Completeness: {breakdown['completeness']}/30\n"
        if "validation" in breakdown:
            explanation += f"- Validation: {breakdown['validation']}/25\n"
        if "source" in breakdown:
            explanation += f"- Source Reliability: {breakdown['source']}/20\n"
        if "match" in breakdown:
            explanation += f"- Match Quality: {breakdown['match']}/15\n"
        if "freshness" in breakdown:
            explanation += f"- Data Freshness: {breakdown['freshness']}/10\n"

        return explanation
