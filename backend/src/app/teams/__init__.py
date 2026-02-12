"""Team accounts module for Scripe.

Enables team collaboration:
- Shared credit pools
- Team member management
- Role-based access (owner, admin, member)
- Shared searches and lists
"""

from app.teams.models import Team, TeamMember, TeamRole
from app.teams.service import TeamService, team_service

__all__ = ["Team", "TeamMember", "TeamRole", "TeamService", "team_service"]
