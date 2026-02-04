"""Data normalization utilities."""

import re
from typing import Any

from slugify import slugify


class Normalizer:
    """Normalize company data for deduplication."""

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Normalize company name for comparison."""
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove legal entity suffixes
        legal_suffixes = [
            r"\bs\.r\.l\.?\b",
            r"\bs\.p\.a\.?\b",
            r"\bs\.a\.s\.?\b",
            r"\bs\.n\.c\.?\b",
            r"\bs\.s\.?\b",
            r"\bsrl\b",
            r"\bspa\b",
            r"\bsas\b",
            r"\bsnc\b",
            r"\bltd\.?\b",
            r"\bllc\.?\b",
            r"\binc\.?\b",
            r"\bcorp\.?\b",
        ]

        for suffix in legal_suffixes:
            normalized = re.sub(suffix, "", normalized)

        # Remove special characters
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized.strip()

    @staticmethod
    def normalize_for_matching(text: str) -> str:
        """Normalize text for keyword matching."""
        if not text:
            return ""

        # Slugify for consistent matching
        return slugify(text, separator=" ")

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate simple similarity score between texts."""
        if not text1 or not text2:
            return 0.0

        norm1 = set(Normalizer.normalize_for_matching(text1).split())
        norm2 = set(Normalizer.normalize_for_matching(text2).split())

        if not norm1 or not norm2:
            return 0.0

        # Jaccard similarity
        intersection = len(norm1 & norm2)
        union = len(norm1 | norm2)

        return intersection / union if union > 0 else 0.0
