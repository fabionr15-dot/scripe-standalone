"""Lists API v1 endpoints for saved lead lists."""

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.middleware import require_auth
from app.auth.models import SavedList, UserAccount, UserSearch
from app.logging_config import get_logger
from app.storage.db import db
from app.storage.models import Company, Search

logger = get_logger(__name__)

router = APIRouter(prefix="/lists", tags=["lists"])


# ==================== MODELS ====================


class ListCreate(BaseModel):
    """Create list request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class AddLeadsRequest(BaseModel):
    """Add/remove leads request."""
    lead_ids: list[str]


# ==================== ENDPOINTS ====================


@router.get("")
async def list_saved_lists(user: UserAccount = Depends(require_auth)):
    """Get user's saved lists."""
    with db.session() as session:
        lists = (
            session.query(SavedList)
            .filter(
                SavedList.user_id == user.id,
                SavedList.is_archived == False,
            )
            .order_by(SavedList.updated_at.desc())
            .all()
        )

        return {
            "items": [
                {
                    "id": str(sl.id),
                    "name": sl.name,
                    "description": sl.description,
                    "leads_count": sl.company_count or 0,
                    "created_at": sl.created_at.isoformat() if sl.created_at else None,
                    "updated_at": sl.updated_at.isoformat() if sl.updated_at else None,
                }
                for sl in lists
            ]
        }


@router.post("", status_code=201)
async def create_list(body: ListCreate, user: UserAccount = Depends(require_auth)):
    """Create a new saved list."""
    with db.session() as session:
        saved_list = SavedList(
            user_id=user.id,
            name=body.name,
            description=body.description,
            companies_json="[]",
            company_count=0,
        )
        session.add(saved_list)
        session.commit()
        session.refresh(saved_list)

        return {
            "id": str(saved_list.id),
            "name": saved_list.name,
            "description": saved_list.description,
            "leads_count": 0,
            "created_at": saved_list.created_at.isoformat() if saved_list.created_at else None,
        }


@router.get("/{list_id}")
async def get_list(list_id: int, user: UserAccount = Depends(require_auth)):
    """Get list details with leads."""
    with db.session() as session:
        saved_list = (
            session.query(SavedList)
            .filter(SavedList.id == list_id, SavedList.user_id == user.id)
            .first()
        )

        if not saved_list:
            raise HTTPException(status_code=404, detail="List not found")

        # Parse company IDs from JSON — only return companies from user's own searches
        company_ids = json.loads(saved_list.companies_json or "[]")

        companies = []
        if company_ids:
            user_search_ids = [
                us.search_id for us in
                session.query(UserSearch.search_id)
                .filter(UserSearch.user_id == user.id)
                .all()
            ]
            int_ids = [int(cid) for cid in company_ids]
            companies = (
                session.query(Company)
                .filter(
                    Company.id.in_(int_ids),
                    Company.search_id.in_(user_search_ids) if user_search_ids else False,
                )
                .all()
            )

        return {
            "id": str(saved_list.id),
            "name": saved_list.name,
            "description": saved_list.description,
            "leads_count": len(companies),
            "leads": [
                {
                    "id": str(c.id),
                    "company_name": c.company_name,
                    "phone": c.phone,
                    "email": c.email,
                    "website": c.website,
                    "city": c.city,
                    "category": c.category,
                    "quality_score": c.quality_score,
                }
                for c in companies
            ],
        }


@router.delete("/{list_id}")
async def delete_list(list_id: int, user: UserAccount = Depends(require_auth)):
    """Delete a saved list."""
    with db.session() as session:
        saved_list = (
            session.query(SavedList)
            .filter(SavedList.id == list_id, SavedList.user_id == user.id)
            .first()
        )

        if not saved_list:
            raise HTTPException(status_code=404, detail="List not found")

        session.delete(saved_list)
        session.commit()

        return {"success": True}


@router.post("/{list_id}/leads")
async def add_leads_to_list(
    list_id: int,
    body: AddLeadsRequest,
    user: UserAccount = Depends(require_auth),
):
    """Add leads to a saved list."""
    with db.session() as session:
        saved_list = (
            session.query(SavedList)
            .filter(SavedList.id == list_id, SavedList.user_id == user.id)
            .first()
        )

        if not saved_list:
            raise HTTPException(status_code=404, detail="List not found")

        # Verify that the requested company IDs belong to user's own searches
        int_lead_ids = [int(lid) for lid in body.lead_ids]
        if int_lead_ids:
            user_search_ids = [
                us.search_id for us in
                session.query(UserSearch.search_id)
                .filter(UserSearch.user_id == user.id)
                .all()
            ]
            owned_company_count = (
                session.query(Company)
                .filter(
                    Company.id.in_(int_lead_ids),
                    Company.search_id.in_(user_search_ids) if user_search_ids else False,
                )
                .count()
            )
            if owned_company_count != len(int_lead_ids):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: some leads do not belong to your searches",
                )

        existing_ids = json.loads(saved_list.companies_json or "[]")
        new_ids = list(set(existing_ids + body.lead_ids))
        saved_list.companies_json = json.dumps(new_ids)
        saved_list.company_count = len(new_ids)
        saved_list.updated_at = datetime.utcnow()
        session.commit()

        return {"success": True, "leads_count": len(new_ids)}


@router.delete("/{list_id}/leads")
async def remove_leads_from_list(
    list_id: int,
    body: AddLeadsRequest,
    user: UserAccount = Depends(require_auth),
):
    """Remove leads from a saved list."""
    with db.session() as session:
        saved_list = (
            session.query(SavedList)
            .filter(SavedList.id == list_id, SavedList.user_id == user.id)
            .first()
        )

        if not saved_list:
            raise HTTPException(status_code=404, detail="List not found")

        existing_ids = json.loads(saved_list.companies_json or "[]")
        new_ids = [cid for cid in existing_ids if cid not in body.lead_ids]
        saved_list.companies_json = json.dumps(new_ids)
        saved_list.company_count = len(new_ids)
        saved_list.updated_at = datetime.utcnow()
        session.commit()

        return {"success": True, "leads_count": len(new_ids)}


@router.get("/{list_id}/export")
async def export_list(
    list_id: int,
    format: str = Query(default="csv", pattern="^(csv|excel)$"),
    user: UserAccount = Depends(require_auth),
):
    """Export list as CSV or Excel."""
    with db.session() as session:
        saved_list = (
            session.query(SavedList)
            .filter(SavedList.id == list_id, SavedList.user_id == user.id)
            .first()
        )

        if not saved_list:
            raise HTTPException(status_code=404, detail="List not found")

        company_ids = json.loads(saved_list.companies_json or "[]")
        companies = []
        if company_ids:
            int_ids = [int(cid) for cid in company_ids]

            # SECURITY: Get user's search IDs to verify ownership
            # This prevents IDOR - user can only export companies from their own searches
            user_search_ids = [
                us.search_id for us in
                session.query(UserSearch.search_id)
                .filter(UserSearch.user_id == user.id)
                .all()
            ]

            # Only fetch companies that belong to user's searches
            if user_search_ids:
                companies = (
                    session.query(Company)
                    .filter(
                        Company.id.in_(int_ids),
                        Company.search_id.in_(user_search_ids)
                    )
                    .all()
                )

        fieldnames = [
            "company_name", "website", "phone", "email",
            "city", "region", "country", "category",
        ]

        if format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for c in companies:
                writer.writerow({
                    "company_name": c.company_name or "",
                    "website": c.website or "",
                    "phone": c.phone or "",
                    "email": c.email or "",
                    "city": c.city or "",
                    "region": c.region or "",
                    "country": c.country or "",
                    "category": c.category or "",
                })
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=lista-{list_id}.csv"
                },
            )

        # Excel export
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = saved_list.name[:30]

        # Header row
        ws.append(fieldnames)

        # Data rows
        for c in companies:
            ws.append([
                c.company_name or "",
                c.website or "",
                c.phone or "",
                c.email or "",
                c.city or "",
                c.region or "",
                c.country or "",
                c.category or "",
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=lista-{list_id}.xlsx"
            },
        )
