"""Intent Signals module.

Provides detection of business signals that indicate buying intent:
- Hiring activity (job postings)
- Technology stack
- Website age/changes
- Growth indicators
"""

from app.signals.job_detector import JobDetector, job_detector
from app.signals.tech_detector import TechDetector, tech_detector

__all__ = ["JobDetector", "job_detector", "TechDetector", "tech_detector"]
