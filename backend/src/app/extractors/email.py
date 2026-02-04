"""Email extraction from websites and text."""

import re
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


class EmailExtractor:
    """Extract and validate email addresses."""

    # Common business email patterns (priority order)
    PRIORITY_PATTERNS = [
        r"info@",
        r"contact@",
        r"contatto@",
        r"contatti@",
        r"vendite@",
        r"sales@",
        r"commercial[ei]?@",
        r"amministrazione@",
        r"admin@",
        r"support@",
        r"supporto@",
        r"hello@",
        r"hi@",
    ]

    # Generic email regex
    EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    def __init__(self):
        """Initialize email extractor."""
        pass

    def extract_from_text(self, text: str, domain: str | None = None) -> list[str]:
        """Extract all email addresses from text.

        Args:
            text: Text to search
            domain: Optional domain to filter emails (e.g., 'example.com')

        Returns:
            List of unique email addresses
        """
        if not text:
            return []

        # Find all emails
        emails = re.findall(self.EMAIL_REGEX, text, re.IGNORECASE)

        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)

                # Filter by domain if specified
                if domain:
                    if email_lower.endswith(f"@{domain.lower()}") or email_lower.endswith(f"@www.{domain.lower()}"):
                        unique_emails.append(email_lower)
                else:
                    unique_emails.append(email_lower)

        # Filter out common spam/placeholder emails
        unique_emails = self._filter_spam_emails(unique_emails)

        return unique_emails

    def extract_best_email(
        self, text: str, domain: str | None = None, company_name: str | None = None
    ) -> str | None:
        """Extract the most likely business email.

        Priority:
        1. Priority patterns (info@, contact@, etc.) matching domain
        2. Emails matching company name
        3. Any email matching domain
        4. First found email

        Args:
            text: Text to search
            domain: Company domain
            company_name: Company name for matching

        Returns:
            Best email or None
        """
        all_emails = self.extract_from_text(text, domain)

        if not all_emails:
            return None

        # Priority 1: Common business patterns
        for pattern in self.PRIORITY_PATTERNS:
            for email in all_emails:
                if re.match(pattern, email, re.IGNORECASE):
                    logger.debug("email_found_priority", email=email, pattern=pattern)
                    return email

        # Priority 2: Emails matching company name
        if company_name:
            company_slug = re.sub(r'[^a-z0-9]', '', company_name.lower())
            for email in all_emails:
                email_local = email.split('@')[0]
                if company_slug in email_local:
                    logger.debug("email_found_company_match", email=email)
                    return email

        # Priority 3: Any email (first one)
        logger.debug("email_found_generic", email=all_emails[0])
        return all_emails[0]

    def _filter_spam_emails(self, emails: list[str]) -> list[str]:
        """Filter out spam/placeholder emails.

        Args:
            emails: List of emails

        Returns:
            Filtered list
        """
        spam_patterns = [
            r'noreply@',
            r'no-reply@',
            r'donotreply@',
            r'example@',
            r'test@',
            r'demo@',
            r'sample@',
            r'webmaster@',
            r'postmaster@',
            r'abuse@',
            r'spam@',
            r'privacy@',
            r'gdpr@',
            r'dpo@',
            r'cookie@',
        ]

        filtered = []
        for email in emails:
            is_spam = False
            for pattern in spam_patterns:
                if re.match(pattern, email, re.IGNORECASE):
                    is_spam = True
                    break

            if not is_spam:
                filtered.append(email)

        return filtered

    def validate_format(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address

        Returns:
            True if valid format
        """
        if not email:
            return False

        # Check regex
        if not re.match(self.EMAIL_REGEX, email, re.IGNORECASE):
            return False

        # Additional checks
        if len(email) > 320:  # RFC 5321
            return False

        local, domain = email.rsplit('@', 1)

        if len(local) > 64 or len(domain) > 255:
            return False

        # Check for consecutive dots
        if '..' in email:
            return False

        return True

    def validate_deliverability(self, email: str) -> dict[str, Any]:
        """Validate email deliverability (basic checks).

        Note: Full SMTP validation would require actual connection,
        which can be slow and trigger spam filters. This does basic checks.

        Args:
            email: Email address

        Returns:
            Dict with validation results
        """
        result = {
            "valid_format": False,
            "disposable": False,
            "role_based": False,
            "score": 0,
        }

        # Format check
        if not self.validate_format(email):
            return result

        result["valid_format"] = True
        result["score"] += 40

        # Check for disposable email domains
        disposable_domains = [
            "tempmail.com", "guerrillamail.com", "10minutemail.com",
            "throwaway.email", "yopmail.com", "mailinator.com"
        ]
        domain = email.split('@')[1].lower()
        if domain in disposable_domains:
            result["disposable"] = True
            result["score"] -= 30

        # Check if role-based (info@, support@, etc.)
        local = email.split('@')[0].lower()
        role_accounts = ["info", "contact", "support", "admin", "sales", "hello"]
        if local in role_accounts:
            result["role_based"] = True
            result["score"] += 20  # Still good for business
        else:
            result["score"] += 40  # Personal email even better

        # Ensure score is 0-100
        result["score"] = max(0, min(100, result["score"]))

        return result

    def extract_from_html(self, html: str, domain: str | None = None) -> list[dict[str, str]]:
        """Extract emails from HTML with context.

        Args:
            html: HTML content
            domain: Optional domain filter

        Returns:
            List of dicts with email and context
        """
        # Extract mailto links
        mailto_pattern = r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
        mailto_emails = re.findall(mailto_pattern, html, re.IGNORECASE)

        # Extract from text
        text_emails = self.extract_from_text(html, domain)

        # Combine with priority to mailto (more reliable)
        all_emails = []
        seen = set()

        for email in mailto_emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                all_emails.append({
                    "email": email_lower,
                    "source": "mailto_link",
                    "priority": "high"
                })

        for email in text_emails:
            if email not in seen:
                seen.add(email)
                all_emails.append({
                    "email": email,
                    "source": "text",
                    "priority": "medium"
                })

        return all_emails
