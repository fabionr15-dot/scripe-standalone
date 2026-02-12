"""Technology stack detection.

Detects technologies used by a website by analyzing:
- HTML meta tags
- Script sources
- Common framework signatures
- Cookie patterns

This is a lightweight implementation. For comprehensive detection,
integrate with BuiltWith or Wappalyzer APIs.
"""

import httpx
import re
from typing import Any
from urllib.parse import urlparse

from app.logging_config import get_logger

logger = get_logger(__name__)


# Technology detection patterns
TECH_PATTERNS = {
    # E-commerce platforms
    "shopify": [
        r"cdn\.shopify\.com",
        r"\.myshopify\.com",
        r"Shopify\.theme",
    ],
    "woocommerce": [
        r"woocommerce",
        r"wc-ajax",
        r"/wp-content/plugins/woocommerce",
    ],
    "magento": [
        r"Mage\.",
        r"/skin/frontend/",
        r"magento",
    ],
    "prestashop": [
        r"prestashop",
        r"/modules/",
    ],

    # CMS
    "wordpress": [
        r"/wp-content/",
        r"/wp-includes/",
        r"wordpress",
    ],
    "drupal": [
        r"drupal",
        r"/sites/default/",
    ],
    "joomla": [
        r"/components/com_",
        r"joomla",
    ],

    # Analytics
    "google_analytics": [
        r"google-analytics\.com",
        r"googletagmanager\.com",
        r"gtag\(",
        r"UA-\d+-\d+",
        r"G-[A-Z0-9]+",
    ],
    "hotjar": [
        r"hotjar\.com",
        r"hj\(",
    ],
    "mixpanel": [
        r"mixpanel\.com",
        r"mixpanel\.",
    ],

    # Marketing
    "hubspot": [
        r"hubspot\.com",
        r"hs-scripts\.com",
        r"hsforms\.com",
    ],
    "mailchimp": [
        r"mailchimp\.com",
        r"mc\.us\d+\.list-manage\.com",
    ],
    "intercom": [
        r"intercom\.io",
        r"intercomcdn\.com",
    ],
    "drift": [
        r"drift\.com",
        r"driftt\.com",
    ],

    # Frameworks
    "react": [
        r"react",
        r"__REACT",
        r"_reactRootContainer",
    ],
    "vue": [
        r"vue\.js",
        r"__VUE__",
        r"vue-",
    ],
    "angular": [
        r"angular",
        r"ng-version",
        r"ng-app",
    ],
    "next_js": [
        r"__NEXT_DATA__",
        r"/_next/",
    ],

    # Infrastructure
    "cloudflare": [
        r"cloudflare",
        r"cf-ray",
    ],
    "aws": [
        r"\.amazonaws\.com",
        r"aws-",
    ],
    "stripe": [
        r"stripe\.com",
        r"js\.stripe\.com",
    ],
    "paypal": [
        r"paypal\.com",
        r"paypalobjects\.com",
    ],
}

# Technology categories
TECH_CATEGORIES = {
    "ecommerce": ["shopify", "woocommerce", "magento", "prestashop"],
    "cms": ["wordpress", "drupal", "joomla"],
    "analytics": ["google_analytics", "hotjar", "mixpanel"],
    "marketing": ["hubspot", "mailchimp", "intercom", "drift"],
    "framework": ["react", "vue", "angular", "next_js"],
    "infrastructure": ["cloudflare", "aws"],
    "payments": ["stripe", "paypal"],
}


class TechDetector:
    """Detect technologies used by websites."""

    def __init__(self):
        """Initialize tech detector."""
        self.logger = get_logger(__name__)

    async def detect_technologies(self, website: str) -> dict:
        """Detect technologies used by a website.

        Args:
            website: Website URL

        Returns:
            Detection result:
            {
                "technologies": ["shopify", "google_analytics", "hubspot"],
                "categories": {"ecommerce": ["shopify"], "analytics": ["google_analytics"]},
                "signals": {
                    "is_ecommerce": True,
                    "uses_crm": True,
                    "tech_savvy": True
                }
            }
        """
        if not website:
            return {"technologies": [], "categories": {}, "signals": {}}

        # Normalize URL
        if not website.startswith("http"):
            website = f"https://{website}"

        detected_techs = []

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ScripeBot/1.0)"}
            ) as client:
                response = await client.get(website)

                if response.status_code == 200:
                    content = response.text
                    headers = dict(response.headers)

                    # Check each technology pattern
                    for tech_name, patterns in TECH_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                if tech_name not in detected_techs:
                                    detected_techs.append(tech_name)
                                break

                    # Also check headers for some technologies
                    header_str = str(headers).lower()
                    if "cloudflare" in header_str:
                        if "cloudflare" not in detected_techs:
                            detected_techs.append("cloudflare")

        except Exception as e:
            self.logger.debug(f"Tech detection failed for {website}: {e}")

        # Categorize technologies
        categories = {}
        for category, techs in TECH_CATEGORIES.items():
            found = [t for t in detected_techs if t in techs]
            if found:
                categories[category] = found

        # Generate business signals
        signals = {
            "is_ecommerce": bool(categories.get("ecommerce")),
            "uses_crm": bool(categories.get("marketing")),
            "uses_analytics": bool(categories.get("analytics")),
            "modern_framework": bool(categories.get("framework")),
            "accepts_payments": bool(categories.get("payments")),
            "tech_savvy": len(detected_techs) >= 3,
        }

        result = {
            "technologies": detected_techs,
            "categories": categories,
            "signals": signals,
        }

        self.logger.info(
            "tech_detection_complete",
            website=website,
            technologies_found=len(detected_techs),
        )

        return result

    def get_tech_score(self, technologies: list[str]) -> int:
        """Calculate a tech sophistication score.

        Args:
            technologies: List of detected technologies

        Returns:
            Score from 0-100
        """
        score = 0

        # Base score for having any tech
        if technologies:
            score += 20

        # Points for different categories
        for tech in technologies:
            if tech in TECH_CATEGORIES.get("ecommerce", []):
                score += 15
            elif tech in TECH_CATEGORIES.get("marketing", []):
                score += 10
            elif tech in TECH_CATEGORIES.get("analytics", []):
                score += 5
            elif tech in TECH_CATEGORIES.get("framework", []):
                score += 10
            elif tech in TECH_CATEGORIES.get("payments", []):
                score += 15

        return min(score, 100)


# Singleton instance
tech_detector = TechDetector()
