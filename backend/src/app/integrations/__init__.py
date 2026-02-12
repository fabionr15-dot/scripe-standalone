"""CRM Integrations module.

Provides integrations with external CRM systems:
- HubSpot
- Salesforce (future)
- Pipedrive (future)
"""

from app.integrations.hubspot_service import HubSpotService, hubspot_service

__all__ = ["HubSpotService", "hubspot_service"]
