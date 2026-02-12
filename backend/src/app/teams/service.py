"""Team service for managing team accounts."""

import secrets
import re
from datetime import datetime
from typing import Any

from sqlalchemy import and_

from app.auth.models import UserAccount
from app.logging_config import get_logger
from app.storage.db import db
from app.teams.models import Team, TeamMember, TeamRole, TeamCreditTransaction

logger = get_logger(__name__)


class TeamError(Exception):
    """Team operation error."""
    pass


class TeamService:
    """Service for managing team accounts."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from team name."""
        # Convert to lowercase, replace spaces with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')

        # Add random suffix to ensure uniqueness
        suffix = secrets.token_hex(4)
        return f"{slug}-{suffix}"

    def create_team(
        self,
        owner_id: int,
        name: str,
        description: str | None = None,
    ) -> Team:
        """Create a new team.

        Args:
            owner_id: User ID of the team owner
            name: Team name
            description: Optional team description

        Returns:
            Created team
        """
        with db.session() as session:
            # Verify owner exists
            owner = session.query(UserAccount).filter(
                UserAccount.id == owner_id
            ).first()

            if not owner:
                raise TeamError(f"User {owner_id} not found")

            # Generate unique slug
            slug = self._generate_slug(name)

            # Create team
            team = Team(
                name=name,
                slug=slug,
                description=description,
                owner_id=owner_id,
                credits_balance=0.0,
            )
            session.add(team)
            session.flush()  # Get team ID

            # Add owner as member
            member = TeamMember(
                team_id=team.id,
                user_id=owner_id,
                role=TeamRole.OWNER,
                accepted_at=datetime.utcnow(),
            )
            session.add(member)
            session.commit()
            session.refresh(team)

            self.logger.info(
                "team_created",
                team_id=team.id,
                owner_id=owner_id,
                name=name,
            )

            return team

    def get_team(self, team_id: int) -> Team | None:
        """Get team by ID."""
        with db.session() as session:
            return session.query(Team).filter(
                Team.id == team_id,
                Team.is_active == True,
            ).first()

    def get_team_by_slug(self, slug: str) -> Team | None:
        """Get team by slug."""
        with db.session() as session:
            return session.query(Team).filter(
                Team.slug == slug,
                Team.is_active == True,
            ).first()

    def get_user_teams(self, user_id: int) -> list[dict]:
        """Get all teams a user belongs to.

        Returns:
            List of team info with user's role
        """
        with db.session() as session:
            memberships = session.query(TeamMember).filter(
                TeamMember.user_id == user_id,
                TeamMember.is_active == True,
            ).all()

            teams = []
            for membership in memberships:
                team = session.query(Team).filter(
                    Team.id == membership.team_id,
                    Team.is_active == True,
                ).first()

                if team:
                    teams.append({
                        "id": team.id,
                        "name": team.name,
                        "slug": team.slug,
                        "role": membership.role.value,
                        "credits_balance": team.credits_balance,
                        "member_count": len([m for m in team.members if m.is_active]),
                        "is_owner": team.owner_id == user_id,
                    })

            return teams

    def invite_member(
        self,
        team_id: int,
        inviter_id: int,
        email: str,
        role: TeamRole = TeamRole.MEMBER,
    ) -> TeamMember:
        """Invite a new member to the team.

        Args:
            team_id: Team ID
            inviter_id: User ID of the person inviting
            email: Email of the person to invite
            role: Role to assign (default: member)

        Returns:
            TeamMember invitation record
        """
        with db.session() as session:
            # Verify team exists and inviter has permission
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise TeamError("Team not found")

            inviter_membership = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == inviter_id,
                TeamMember.is_active == True,
            ).first()

            if not inviter_membership:
                raise TeamError("You are not a member of this team")

            if inviter_membership.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                raise TeamError("Only owners and admins can invite members")

            # Check team member limit
            active_members = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.is_active == True,
            ).count()

            if active_members >= team.max_members:
                raise TeamError(f"Team has reached maximum of {team.max_members} members")

            # Check if user with this email exists
            existing_user = session.query(UserAccount).filter(
                UserAccount.email == email
            ).first()

            # Check if already a member
            if existing_user:
                existing_membership = session.query(TeamMember).filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == existing_user.id,
                ).first()

                if existing_membership:
                    if existing_membership.is_active:
                        raise TeamError("User is already a member of this team")
                    else:
                        # Reactivate membership
                        existing_membership.is_active = True
                        existing_membership.role = role
                        existing_membership.accepted_at = datetime.utcnow()
                        session.commit()
                        return existing_membership

            # Create invitation
            invitation_token = secrets.token_urlsafe(32)
            member = TeamMember(
                team_id=team_id,
                user_id=existing_user.id if existing_user else None,
                role=role,
                invited_by_id=inviter_id,
                invitation_token=invitation_token,
                invitation_email=email,
                accepted_at=datetime.utcnow() if existing_user else None,
            )
            session.add(member)
            session.commit()
            session.refresh(member)

            self.logger.info(
                "team_member_invited",
                team_id=team_id,
                email=email,
                role=role.value,
            )

            return member

    def accept_invitation(self, token: str, user_id: int) -> TeamMember:
        """Accept a team invitation.

        Args:
            token: Invitation token
            user_id: User ID accepting the invitation

        Returns:
            Updated TeamMember
        """
        with db.session() as session:
            invitation = session.query(TeamMember).filter(
                TeamMember.invitation_token == token,
            ).first()

            if not invitation:
                raise TeamError("Invalid invitation token")

            if invitation.accepted_at:
                raise TeamError("Invitation already accepted")

            # Verify email matches
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                raise TeamError("User not found")

            if invitation.invitation_email and user.email.lower() != invitation.invitation_email.lower():
                raise TeamError("Invitation was sent to a different email address")

            # Accept invitation
            invitation.user_id = user_id
            invitation.accepted_at = datetime.utcnow()
            invitation.invitation_token = None  # Clear token
            session.commit()
            session.refresh(invitation)

            self.logger.info(
                "team_invitation_accepted",
                team_id=invitation.team_id,
                user_id=user_id,
            )

            return invitation

    def remove_member(
        self,
        team_id: int,
        remover_id: int,
        member_user_id: int,
    ) -> bool:
        """Remove a member from the team.

        Args:
            team_id: Team ID
            remover_id: User ID performing the removal
            member_user_id: User ID to remove

        Returns:
            True if removed
        """
        with db.session() as session:
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise TeamError("Team not found")

            # Can't remove the owner
            if team.owner_id == member_user_id:
                raise TeamError("Cannot remove team owner")

            # Check permissions
            remover_membership = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == remover_id,
                TeamMember.is_active == True,
            ).first()

            if not remover_membership:
                raise TeamError("You are not a member of this team")

            if remover_membership.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                if remover_id != member_user_id:  # Allow self-removal
                    raise TeamError("Only owners and admins can remove members")

            # Remove member
            member = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == member_user_id,
            ).first()

            if not member:
                raise TeamError("Member not found")

            member.is_active = False
            member.updated_at = datetime.utcnow()
            session.commit()

            self.logger.info(
                "team_member_removed",
                team_id=team_id,
                user_id=member_user_id,
                removed_by=remover_id,
            )

            return True

    def update_member_role(
        self,
        team_id: int,
        updater_id: int,
        member_user_id: int,
        new_role: TeamRole,
    ) -> TeamMember:
        """Update a member's role.

        Args:
            team_id: Team ID
            updater_id: User ID performing the update
            member_user_id: User ID to update
            new_role: New role

        Returns:
            Updated TeamMember
        """
        with db.session() as session:
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise TeamError("Team not found")

            # Only owner can change roles
            if team.owner_id != updater_id:
                raise TeamError("Only the team owner can change member roles")

            # Can't change owner's role
            if team.owner_id == member_user_id:
                raise TeamError("Cannot change owner's role")

            # Can't make someone else owner (use transfer_ownership instead)
            if new_role == TeamRole.OWNER:
                raise TeamError("Cannot assign owner role. Use transfer ownership instead.")

            member = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == member_user_id,
                TeamMember.is_active == True,
            ).first()

            if not member:
                raise TeamError("Member not found")

            member.role = new_role
            member.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(member)

            self.logger.info(
                "team_member_role_updated",
                team_id=team_id,
                user_id=member_user_id,
                new_role=new_role.value,
            )

            return member

    def add_team_credits(
        self,
        team_id: int,
        amount: float,
        operation: str,
        user_id: int | None = None,
        description: str | None = None,
    ) -> TeamCreditTransaction:
        """Add credits to team account.

        Args:
            team_id: Team ID
            amount: Amount to add
            operation: Operation type
            user_id: User who made the transaction
            description: Transaction description

        Returns:
            Transaction record
        """
        with db.session() as session:
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                raise TeamError("Team not found")

            new_balance = team.credits_balance + amount
            team.credits_balance = new_balance
            team.updated_at = datetime.utcnow()

            transaction = TeamCreditTransaction(
                team_id=team_id,
                user_id=user_id,
                amount=amount,
                balance_after=new_balance,
                operation=operation,
                description=description,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            return transaction

    def spend_team_credits(
        self,
        team_id: int,
        amount: float,
        user_id: int,
        search_id: int | None = None,
        description: str | None = None,
    ) -> TeamCreditTransaction:
        """Spend credits from team account.

        Args:
            team_id: Team ID
            amount: Amount to spend
            user_id: User spending the credits
            search_id: Related search ID
            description: Transaction description

        Returns:
            Transaction record
        """
        with db.session() as session:
            team = session.query(Team).filter(
                Team.id == team_id
            ).with_for_update().first()

            if not team:
                raise TeamError("Team not found")

            if team.credits_balance < amount:
                raise TeamError(f"Insufficient team credits: {team.credits_balance} available, {amount} required")

            # Verify user is a member
            membership = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
                TeamMember.is_active == True,
            ).first()

            if not membership:
                raise TeamError("User is not a member of this team")

            new_balance = team.credits_balance - amount
            team.credits_balance = new_balance
            team.credits_used_total += amount
            team.updated_at = datetime.utcnow()

            transaction = TeamCreditTransaction(
                team_id=team_id,
                user_id=user_id,
                amount=-amount,
                balance_after=new_balance,
                operation="search",
                search_id=search_id,
                description=description,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            return transaction

    def get_team_stats(self, team_id: int) -> dict[str, Any]:
        """Get team statistics.

        Args:
            team_id: Team ID

        Returns:
            Team stats
        """
        with db.session() as session:
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                return {}

            active_members = session.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.is_active == True,
            ).count()

            return {
                "team_id": team.id,
                "name": team.name,
                "credits_balance": team.credits_balance,
                "credits_used_total": team.credits_used_total,
                "member_count": active_members,
                "max_members": team.max_members,
                "subscription_tier": team.subscription_tier,
                "created_at": team.created_at.isoformat(),
            }


# Singleton instance
team_service = TeamService()
