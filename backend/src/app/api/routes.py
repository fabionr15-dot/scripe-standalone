"""API routes for the extended Scripe platform."""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.logging_config import get_logger
from app.pipeline.runner import PipelineRunner
from app.storage.db import db
from app.storage.models_v2 import APIKey, Campaign, Client, Company, Run, Search

logger = get_logger(__name__)

# Create routers
clients_router = APIRouter(prefix="/clients", tags=["clients"])
campaigns_router = APIRouter(prefix="/campaigns", tags=["campaigns"])
searches_router = APIRouter(prefix="/searches", tags=["searches"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


# ==================== MODELS ====================

class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class CampaignCreate(BaseModel):
    client_id: int
    name: str
    description: str | None = None
    config: dict[str, Any]


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    status: str | None = None


class SearchCreate(BaseModel):
    campaign_id: int
    name: str
    criteria: dict[str, Any]
    target_count: int
    require_phone: bool = True
    require_email: bool = True
    require_website: bool = True
    validate_phone: bool = False
    validate_email: bool = False
    validate_website: bool = True


class APIKeyCreate(BaseModel):
    service_name: str
    api_key: str
    api_secret: str | None = None
    config: dict[str, Any] | None = None


# ==================== CLIENTS ====================

@clients_router.get("")
async def list_clients():
    """Get all clients."""
    with db.session() as session:
        clients = session.query(Client).filter(Client.is_active == True).all()
        return {
            "clients": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "company": c.company,
                    "campaign_count": len(c.campaigns),
                    "created_at": c.created_at.isoformat(),
                }
                for c in clients
            ]
        }


@clients_router.post("")
async def create_client(client_data: ClientCreate):
    """Create a new client."""
    with db.session() as session:
        client = Client(
            name=client_data.name,
            email=client_data.email,
            company=client_data.company,
            notes=client_data.notes,
        )
        session.add(client)
        session.commit()

        logger.info("client_created", client_id=client.id, name=client.name)

        return {
            "id": client.id,
            "name": client.name,
            "created_at": client.created_at.isoformat(),
        }


@clients_router.get("/{client_id}")
async def get_client(client_id: int):
    """Get client details."""
    with db.session() as session:
        client = session.query(Client).filter(Client.id == client_id).first()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        return {
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "company": client.company,
            "notes": client.notes,
            "is_active": client.is_active,
            "created_at": client.created_at.isoformat(),
            "updated_at": client.updated_at.isoformat(),
            "campaigns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                }
                for c in client.campaigns
            ],
        }


@clients_router.patch("/{client_id}")
async def update_client(client_id: int, update_data: ClientUpdate):
    """Update client."""
    with db.session() as session:
        client = session.query(Client).filter(Client.id == client_id).first()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if update_data.name is not None:
            client.name = update_data.name
        if update_data.email is not None:
            client.email = update_data.email
        if update_data.company is not None:
            client.company = update_data.company
        if update_data.notes is not None:
            client.notes = update_data.notes
        if update_data.is_active is not None:
            client.is_active = update_data.is_active

        client.updated_at = datetime.utcnow()
        session.commit()

        return {"success": True, "id": client.id}


# ==================== CAMPAIGNS ====================

@campaigns_router.get("")
async def list_campaigns(client_id: int | None = None):
    """Get all campaigns, optionally filtered by client."""
    with db.session() as session:
        query = session.query(Campaign)

        if client_id:
            query = query.filter(Campaign.client_id == client_id)

        campaigns = query.all()

        return {
            "campaigns": [
                {
                    "id": c.id,
                    "client_id": c.client_id,
                    "client_name": c.client.name,
                    "name": c.name,
                    "description": c.description,
                    "status": c.status,
                    "search_count": len(c.searches),
                    "created_at": c.created_at.isoformat(),
                }
                for c in campaigns
            ]
        }


@campaigns_router.post("")
async def create_campaign(campaign_data: CampaignCreate):
    """Create a new campaign."""
    with db.session() as session:
        # Verify client exists
        client = session.query(Client).filter(Client.id == campaign_data.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        campaign = Campaign(
            client_id=campaign_data.client_id,
            name=campaign_data.name,
            description=campaign_data.description,
            config_json=campaign_data.config,
            status="draft",
        )
        session.add(campaign)
        session.commit()

        logger.info(
            "campaign_created",
            campaign_id=campaign.id,
            client_id=campaign_data.client_id,
            name=campaign.name,
        )

        return {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat(),
        }


@campaigns_router.get("/{campaign_id}")
async def get_campaign(campaign_id: int):
    """Get campaign details."""
    with db.session() as session:
        campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return {
            "id": campaign.id,
            "client_id": campaign.client_id,
            "client_name": campaign.client.name,
            "name": campaign.name,
            "description": campaign.description,
            "config": campaign.config_json,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
            "searches": [
                {
                    "id": s.id,
                    "name": s.name,
                    "target_count": s.target_count,
                    "created_at": s.created_at.isoformat(),
                }
                for s in campaign.searches
            ],
        }


@campaigns_router.post("/{campaign_id}/duplicate")
async def duplicate_campaign(campaign_id: int, new_name: str | None = None):
    """Duplicate an existing campaign."""
    with db.session() as session:
        original = session.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not original:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Create duplicate
        duplicate = Campaign(
            client_id=original.client_id,
            name=new_name or f"{original.name} (Copy)",
            description=original.description,
            config_json=original.config_json.copy(),
            status="draft",
        )
        session.add(duplicate)
        session.commit()

        logger.info(
            "campaign_duplicated",
            original_id=campaign_id,
            duplicate_id=duplicate.id,
        )

        return {
            "id": duplicate.id,
            "name": duplicate.name,
            "original_id": campaign_id,
        }


@campaigns_router.patch("/{campaign_id}")
async def update_campaign(campaign_id: int, update_data: CampaignUpdate):
    """Update campaign."""
    with db.session() as session:
        campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        if update_data.name is not None:
            campaign.name = update_data.name
        if update_data.description is not None:
            campaign.description = update_data.description
        if update_data.config is not None:
            campaign.config_json = update_data.config
        if update_data.status is not None:
            campaign.status = update_data.status

        campaign.updated_at = datetime.utcnow()
        session.commit()

        return {"success": True, "id": campaign.id}


# ==================== SEARCHES ====================

@searches_router.post("")
async def create_search(search_data: SearchCreate):
    """Create a new search."""
    with db.session() as session:
        # Verify campaign exists
        campaign = session.query(Campaign).filter(Campaign.id == search_data.campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        search = Search(
            campaign_id=search_data.campaign_id,
            name=search_data.name,
            criteria_json=search_data.criteria,
            target_count=search_data.target_count,
            require_phone=search_data.require_phone,
            require_email=search_data.require_email,
            require_website=search_data.require_website,
            validate_phone=search_data.validate_phone,
            validate_email=search_data.validate_email,
            validate_website=search_data.validate_website,
        )
        session.add(search)
        session.commit()

        logger.info(
            "search_created",
            search_id=search.id,
            campaign_id=search_data.campaign_id,
        )

        return {
            "id": search.id,
            "name": search.name,
            "target_count": search.target_count,
        }


async def _execute_pipeline(search_id: int):
    """Execute pipeline in background.

    Args:
        search_id: Search ID to execute
    """
    try:
        runner = PipelineRunner(db)
        result = await runner.run_search(search_id)
        logger.info("pipeline_background_completed", search_id=search_id, result=result)
    except Exception as e:
        logger.error("pipeline_background_failed", search_id=search_id, error=str(e))


@searches_router.post("/{search_id}/run")
async def start_search_run(search_id: int, background_tasks: BackgroundTasks):
    """Start a search run."""
    with db.session() as session:
        search = session.query(Search).filter(Search.id == search_id).first()

        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        # Validate search has campaign
        if not search.campaign_id:
            raise HTTPException(status_code=400, detail="Search has no associated campaign")

        logger.info("search_run_starting", search_id=search_id)

        # Add pipeline execution to background tasks
        background_tasks.add_task(_execute_pipeline, search_id)

        return {
            "run_id": None,  # Will be created by pipeline
            "status": "queued",
            "message": "Search run queued for execution",
            "search_id": search_id,
        }


@searches_router.get("/{search_id}/companies")
async def get_search_companies(search_id: int, limit: int = 1000):
    """Get companies (leads) collected by a search.

    Args:
        search_id: Search ID
        limit: Max number of results (default 1000)

    Returns:
        List of companies with all fields
    """
    with db.session() as session:
        search = session.query(Search).filter(Search.id == search_id).first()

        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        # Get companies for this search
        companies = session.query(Company).filter(
            Company.search_id == search_id
        ).order_by(
            Company.quality_score.desc(),
            Company.match_score.desc()
        ).limit(limit).all()

        return {
            "search_id": search_id,
            "search_name": search.name,
            "total_count": len(companies),
            "companies": [
                {
                    "id": c.id,
                    "company_name": c.company_name,
                    "website": c.website,
                    "phone": c.phone,
                    "email": c.email,
                    "address_line": c.address_line,
                    "postal_code": c.postal_code,
                    "city": c.city,
                    "region": c.region,
                    "country": c.country,
                    "category": c.category,
                    "company_size": c.company_size,
                    "employee_count": c.employee_count,
                    "quality_score": c.quality_score,
                    "match_score": c.match_score,
                    "confidence_score": c.confidence_score,
                    "phone_validated": c.phone_validated,
                    "email_validated": c.email_validated,
                    "website_validated": c.website_validated,
                    "created_at": c.created_at.isoformat(),
                }
                for c in companies
            ]
        }


@searches_router.get("/{search_id}/export")
async def export_search_companies_csv(search_id: int):
    """Export search companies as CSV.

    Args:
        search_id: Search ID

    Returns:
        CSV file download
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    with db.session() as session:
        search = session.query(Search).filter(Search.id == search_id).first()

        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        companies = session.query(Company).filter(
            Company.search_id == search_id
        ).order_by(
            Company.quality_score.desc()
        ).all()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'company_name', 'website', 'phone', 'email',
            'address_line', 'postal_code', 'city', 'region', 'country',
            'category', 'company_size', 'employee_count',
            'quality_score', 'match_score', 'confidence_score'
        ])
        writer.writeheader()

        for c in companies:
            writer.writerow({
                'company_name': c.company_name or '',
                'website': c.website or '',
                'phone': c.phone or '',
                'email': c.email or '',
                'address_line': c.address_line or '',
                'postal_code': c.postal_code or '',
                'city': c.city or '',
                'region': c.region or '',
                'country': c.country or '',
                'category': c.category or '',
                'company_size': c.company_size or '',
                'employee_count': c.employee_count or '',
                'quality_score': c.quality_score or 0,
                'match_score': c.match_score or 0,
                'confidence_score': c.confidence_score or 0,
            })

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=search_{search_id}_leads.csv"
            }
        )


# ==================== RUNS ====================

@runs_router.get("/{run_id}")
async def get_run_status(run_id: int):
    """Get real-time run status."""
    with db.session() as session:
        run = session.query(Run).filter(Run.id == run_id).first()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        return {
            "id": run.id,
            "search_id": run.search_id,
            "status": run.status,
            "progress_percent": run.progress_percent,
            "current_step": run.current_step,
            "estimated_time_remaining": run.estimated_time_remaining,
            "found_count": run.found_count,
            "discarded_count": run.discarded_count,
            "started_at": run.started_at.isoformat(),
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        }


# ==================== SETTINGS ====================

@settings_router.get("/api-keys")
async def list_api_keys():
    """Get all configured API keys (masked)."""
    with db.session() as session:
        keys = session.query(APIKey).all()

        return {
            "api_keys": [
                {
                    "id": k.id,
                    "service_name": k.service_name,
                    "api_key_masked": k.api_key[:8] + "..." if len(k.api_key) > 8 else "***",
                    "is_active": k.is_active,
                    "created_at": k.created_at.isoformat(),
                }
                for k in keys
            ]
        }


@settings_router.post("/api-keys")
async def create_api_key(key_data: APIKeyCreate):
    """Create or update API key."""
    with db.session() as session:
        # Check if exists
        existing = (
            session.query(APIKey)
            .filter(APIKey.service_name == key_data.service_name)
            .first()
        )

        if existing:
            # Update
            existing.api_key = key_data.api_key
            existing.api_secret = key_data.api_secret
            existing.config_json = key_data.config
            existing.updated_at = datetime.utcnow()
            session.commit()
            return {"success": True, "action": "updated", "id": existing.id}
        else:
            # Create
            api_key = APIKey(
                service_name=key_data.service_name,
                api_key=key_data.api_key,
                api_secret=key_data.api_secret,
                config_json=key_data.config,
            )
            session.add(api_key)
            session.commit()
            return {"success": True, "action": "created", "id": api_key.id}


@settings_router.patch("/api-keys/{key_id}/toggle")
async def toggle_api_key(key_id: int):
    """Toggle API key active status."""
    with db.session() as session:
        key = session.query(APIKey).filter(APIKey.id == key_id).first()

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        key.is_active = not key.is_active
        session.commit()

        return {"success": True, "is_active": key.is_active}


@settings_router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int):
    """Delete API key."""
    with db.session() as session:
        key = session.query(APIKey).filter(APIKey.id == key_id).first()

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        session.delete(key)
        session.commit()

        return {"success": True}


# Export all routers
def get_routers():
    """Get all API routers."""
    return [
        clients_router,
        campaigns_router,
        searches_router,
        runs_router,
        settings_router,
    ]
