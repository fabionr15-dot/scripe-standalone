"""Dashboard API v1 endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func

from app.auth.middleware import require_auth
from app.auth.models import UserAccount, UserSearch
from app.storage.db import db
from app.storage.models import Company, Search

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user: UserAccount = Depends(require_auth)):
    """Get dashboard statistics for the current user."""
    with db.session() as session:
        # Get user's search IDs
        user_searches = (
            session.query(UserSearch)
            .filter(UserSearch.user_id == user.id)
            .all()
        )
        user_search_ids = [us.search_id for us in user_searches]

        total_searches = len(user_search_ids)

        if not user_search_ids:
            return {
                "totalSearches": 0,
                "totalLeads": 0,
                "creditsUsed": round(user.credits_used_total or 0, 2),
                "avgQuality": 0,
            }

        # Count total leads across all user's searches
        total_leads = (
            session.query(func.count(Company.id))
            .filter(Company.search_id.in_(user_search_ids))
            .scalar()
            or 0
        )

        # Average quality score (0-100 int in DB, frontend expects 0-1 float)
        avg_quality_raw = (
            session.query(func.avg(Company.quality_score))
            .filter(Company.search_id.in_(user_search_ids))
            .scalar()
            or 0
        )

        return {
            "totalSearches": total_searches,
            "totalLeads": total_leads,
            "creditsUsed": round(user.credits_used_total or 0, 2),
            "avgQuality": float(avg_quality_raw) / 100 if avg_quality_raw else 0,
        }
