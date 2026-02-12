"""Team accounts API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.middleware import require_auth
from app.auth.models import UserAccount
from app.logging_config import get_logger
from app.teams.models import TeamRole
from app.teams.service import team_service, TeamError

router = APIRouter(prefix="/teams", tags=["teams"])
logger = get_logger(__name__)


# ─── Request/Response Models ─────────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    """Request to create a new team."""
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class TeamResponse(BaseModel):
    """Team information response."""
    id: int
    name: str
    slug: str
    description: str | None
    credits_balance: float
    member_count: int
    max_members: int
    subscription_tier: str
    is_owner: bool
    role: str


class TeamListResponse(BaseModel):
    """List of teams user belongs to."""
    teams: list[dict]


class InviteMemberRequest(BaseModel):
    """Request to invite a team member."""
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")


class TeamMemberResponse(BaseModel):
    """Team member information."""
    id: int
    user_id: int | None
    email: str | None
    name: str | None
    role: str
    accepted: bool
    created_at: str


class UpdateMemberRoleRequest(BaseModel):
    """Request to update member role."""
    role: str = Field(..., pattern="^(admin|member)$")


class AddCreditsRequest(BaseModel):
    """Request to add credits to team."""
    amount: float = Field(..., gt=0)
    description: str | None = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("", response_model=TeamResponse)
async def create_team(
    request: CreateTeamRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Create a new team.

    The current user becomes the team owner.
    """
    try:
        team = team_service.create_team(
            owner_id=current_user.id,
            name=request.name,
            description=request.description,
        )

        return TeamResponse(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            credits_balance=team.credits_balance,
            member_count=1,
            max_members=team.max_members,
            subscription_tier=team.subscription_tier,
            is_owner=True,
            role="owner",
        )

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TeamListResponse)
async def get_my_teams(
    current_user: UserAccount = Depends(require_auth),
):
    """Get all teams the current user belongs to."""
    teams = team_service.get_user_teams(current_user.id)
    return TeamListResponse(teams=teams)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_user: UserAccount = Depends(require_auth),
):
    """Get team details.

    User must be a member of the team.
    """
    # Verify membership
    user_teams = team_service.get_user_teams(current_user.id)
    team_info = next((t for t in user_teams if t["id"] == team_id), None)

    if not team_info:
        raise HTTPException(status_code=404, detail="Team not found or you are not a member")

    team = team_service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        credits_balance=team.credits_balance,
        member_count=team_info["member_count"],
        max_members=team.max_members,
        subscription_tier=team.subscription_tier,
        is_owner=team_info["is_owner"],
        role=team_info["role"],
    )


@router.get("/{team_id}/members")
async def get_team_members(
    team_id: int,
    current_user: UserAccount = Depends(require_auth),
):
    """Get all members of a team.

    User must be a member of the team.
    """
    # Verify membership
    user_teams = team_service.get_user_teams(current_user.id)
    if not any(t["id"] == team_id for t in user_teams):
        raise HTTPException(status_code=404, detail="Team not found or you are not a member")

    team = team_service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = []
    for member in team.members:
        if member.is_active or member.invitation_token:  # Show active and pending
            user = member.user
            members.append({
                "id": member.id,
                "user_id": member.user_id,
                "email": user.email if user else member.invitation_email,
                "name": user.name if user else None,
                "role": member.role.value,
                "accepted": member.accepted_at is not None,
                "created_at": member.created_at.isoformat(),
            })

    return {"members": members}


@router.post("/{team_id}/members")
async def invite_team_member(
    team_id: int,
    request: InviteMemberRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Invite a new member to the team.

    Only owners and admins can invite members.
    """
    try:
        role = TeamRole.ADMIN if request.role == "admin" else TeamRole.MEMBER

        member = team_service.invite_member(
            team_id=team_id,
            inviter_id=current_user.id,
            email=request.email,
            role=role,
        )

        return {
            "success": True,
            "message": f"Invitation sent to {request.email}",
            "invitation_token": member.invitation_token,
        }

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{team_id}/members/{user_id}/role")
async def update_member_role(
    team_id: int,
    user_id: int,
    request: UpdateMemberRoleRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Update a member's role.

    Only the team owner can change roles.
    """
    try:
        role = TeamRole.ADMIN if request.role == "admin" else TeamRole.MEMBER

        member = team_service.update_member_role(
            team_id=team_id,
            updater_id=current_user.id,
            member_user_id=user_id,
            new_role=role,
        )

        return {
            "success": True,
            "message": f"Role updated to {request.role}",
            "role": member.role.value,
        }

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: UserAccount = Depends(require_auth),
):
    """Remove a member from the team.

    Owners and admins can remove members. Members can remove themselves.
    """
    try:
        team_service.remove_member(
            team_id=team_id,
            remover_id=current_user.id,
            member_user_id=user_id,
        )

        return {"success": True, "message": "Member removed"}

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{team_id}/credits")
async def add_team_credits(
    team_id: int,
    request: AddCreditsRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Add credits to team account.

    Only owners can add credits (typically after purchase).
    """
    # Verify ownership
    user_teams = team_service.get_user_teams(current_user.id)
    team_info = next((t for t in user_teams if t["id"] == team_id), None)

    if not team_info:
        raise HTTPException(status_code=404, detail="Team not found or you are not a member")

    if not team_info["is_owner"]:
        raise HTTPException(status_code=403, detail="Only team owners can add credits")

    try:
        transaction = team_service.add_team_credits(
            team_id=team_id,
            amount=request.amount,
            operation="manual_add",
            user_id=current_user.id,
            description=request.description or "Credits added manually",
        )

        return {
            "success": True,
            "new_balance": transaction.balance_after,
            "transaction_id": transaction.id,
        }

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{team_id}/stats")
async def get_team_stats(
    team_id: int,
    current_user: UserAccount = Depends(require_auth),
):
    """Get team statistics.

    User must be a member of the team.
    """
    # Verify membership
    user_teams = team_service.get_user_teams(current_user.id)
    if not any(t["id"] == team_id for t in user_teams):
        raise HTTPException(status_code=404, detail="Team not found or you are not a member")

    stats = team_service.get_team_stats(team_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Team not found")

    return stats


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: UserAccount = Depends(require_auth),
):
    """Accept a team invitation.

    The invitation email must match the current user's email.
    """
    try:
        member = team_service.accept_invitation(token, current_user.id)

        return {
            "success": True,
            "message": "Invitation accepted",
            "team_id": member.team_id,
        }

    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))
