"""Job posting detection for hiring signals.

Detects if a company is actively hiring by checking:
- Google search for job postings
- Company career pages
- Job board presence

This is a lightweight implementation that doesn't scrape LinkedIn or other
restricted sources.
"""

import httpx
import re
from typing import Any
from urllib.parse import quote_plus

from app.logging_config import get_logger

logger = get_logger(__name__)


class JobDetector:
    """Detect hiring activity for companies."""

    # Common job-related keywords
    JOB_KEYWORDS = [
        "careers", "jobs", "hiring", "join us", "open positions",
        "karriere", "stellenangebote", "lavora con noi", "offerte di lavoro",
        "emploi", "recrutement", "trabajo", "empleo",
    ]

    # Department keywords for categorization
    DEPARTMENT_KEYWORDS = {
        "engineering": ["developer", "engineer", "software", "tech", "devops", "frontend", "backend"],
        "sales": ["sales", "account", "business development", "vertrieb", "vendite"],
        "marketing": ["marketing", "content", "seo", "growth", "social media"],
        "operations": ["operations", "logistics", "supply chain", "betrieb"],
        "hr": ["hr", "human resources", "recruiting", "talent", "personal"],
        "finance": ["finance", "accounting", "controller", "finanz"],
    }

    def __init__(self):
        """Initialize job detector."""
        self.logger = get_logger(__name__)

    async def check_career_page(self, website: str) -> dict:
        """Check company website for career page indicators.

        Args:
            website: Company website URL

        Returns:
            Detection result:
            {
                "has_career_page": True,
                "career_url": "https://example.com/careers",
                "job_indicators": ["careers", "join us"]
            }
        """
        if not website:
            return {"has_career_page": False, "career_url": None, "job_indicators": []}

        # Normalize URL
        if not website.startswith("http"):
            website = f"https://{website}"

        # Common career page paths
        career_paths = [
            "/careers", "/jobs", "/karriere", "/lavora-con-noi",
            "/join-us", "/work-with-us", "/employment",
        ]

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # First check main page for career links
            try:
                response = await client.get(website)
                if response.status_code == 200:
                    content = response.text.lower()
                    indicators = []

                    for keyword in self.JOB_KEYWORDS:
                        if keyword in content:
                            indicators.append(keyword)

                    if indicators:
                        # Try to find career page URL
                        career_url = None
                        for path in career_paths:
                            try:
                                test_url = website.rstrip("/") + path
                                test_response = await client.head(test_url)
                                if test_response.status_code == 200:
                                    career_url = test_url
                                    break
                            except:
                                continue

                        return {
                            "has_career_page": True,
                            "career_url": career_url,
                            "job_indicators": indicators[:5],
                        }

            except Exception as e:
                self.logger.debug(f"Career page check failed for {website}: {e}")

        return {"has_career_page": False, "career_url": None, "job_indicators": []}

    async def estimate_hiring_activity(self, company_name: str, website: str = None) -> dict:
        """Estimate hiring activity level for a company.

        This uses heuristics based on career page presence and indicators.
        For more accurate data, would need job board API integrations.

        Args:
            company_name: Company name
            website: Company website URL

        Returns:
            Hiring signal:
            {
                "is_hiring": True,
                "confidence": 0.7,  # 0-1
                "signal_strength": "medium",  # low, medium, high
                "indicators": ["has career page", "found job keywords"]
            }
        """
        indicators = []
        confidence = 0.0

        # Check career page
        if website:
            career_result = await self.check_career_page(website)
            if career_result["has_career_page"]:
                indicators.append("has_career_page")
                confidence += 0.3

                if career_result["job_indicators"]:
                    confidence += 0.1 * min(len(career_result["job_indicators"]), 3)
                    indicators.append(f"job_keywords: {', '.join(career_result['job_indicators'][:3])}")

        # Determine signal strength
        if confidence >= 0.6:
            signal_strength = "high"
        elif confidence >= 0.3:
            signal_strength = "medium"
        else:
            signal_strength = "low"

        result = {
            "is_hiring": confidence >= 0.3,
            "confidence": min(confidence, 1.0),
            "signal_strength": signal_strength,
            "indicators": indicators,
        }

        self.logger.info(
            "job_detection_complete",
            company=company_name,
            is_hiring=result["is_hiring"],
            confidence=result["confidence"],
        )

        return result


# Singleton instance
job_detector = JobDetector()
