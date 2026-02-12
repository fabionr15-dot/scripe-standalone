"""Billing API endpoints for addresses and invoices."""

import json
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.middleware import require_auth
from app.auth.models import UserAccount
from app.billing.models import (
    BillingAddress,
    BillingAddressCreate,
    BillingAddressResponse,
    Invoice,
    InvoiceItemResponse,
    InvoiceListResponse,
    InvoiceResponse,
)
from app.billing.invoice_service import get_invoice_service
from app.storage.db import get_db

router = APIRouter(prefix="/billing", tags=["billing"])


# =============================================================================
# BILLING ADDRESS ENDPOINTS
# =============================================================================

@router.get("/address", response_model=BillingAddressResponse | None)
async def get_billing_address(
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the primary billing address for the current user."""
    address = (
        db.query(BillingAddress)
        .filter(
            BillingAddress.user_id == user.id,
            BillingAddress.is_primary == True,
        )
        .first()
    )

    if not address:
        return None

    return address


@router.post("/address", response_model=BillingAddressResponse)
async def create_or_update_billing_address(
    data: BillingAddressCreate,
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create or update the billing address for the current user.

    If an address already exists, it will be updated.
    """
    # Check for existing address
    existing = (
        db.query(BillingAddress)
        .filter(
            BillingAddress.user_id == user.id,
            BillingAddress.is_primary == True,
        )
        .first()
    )

    if existing:
        # Update existing address
        existing.street_address = data.street_address
        existing.street_address_2 = data.street_address_2
        existing.city = data.city
        existing.state_province = data.state_province
        existing.postal_code = data.postal_code
        existing.country = data.country
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new address
        address = BillingAddress(
            user_id=user.id,
            street_address=data.street_address,
            street_address_2=data.street_address_2,
            city=data.city,
            state_province=data.state_province,
            postal_code=data.postal_code,
            country=data.country,
            is_primary=True,
        )
        db.add(address)
        db.commit()
        db.refresh(address)
        return address


@router.delete("/address/{address_id}")
async def delete_billing_address(
    address_id: int,
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a billing address.

    IDOR Protection: Only the owner can delete their address.
    """
    address = (
        db.query(BillingAddress)
        .filter(
            BillingAddress.id == address_id,
            BillingAddress.user_id == user.id,  # IDOR protection
        )
        .first()
    )

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()

    return {"status": "deleted"}


# =============================================================================
# INVOICE ENDPOINTS
# =============================================================================

@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all invoices for the current user.

    IDOR Protection: Only returns invoices for the authenticated user.
    """
    service = get_invoice_service(db)
    invoices, total = service.get_user_invoices(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )

    # Convert to response models
    items = []
    for inv in invoices:
        # Parse items JSON
        invoice_items = []
        if inv.items_json:
            try:
                raw_items = json.loads(inv.items_json)
                invoice_items = [InvoiceItemResponse(**item) for item in raw_items]
            except (json.JSONDecodeError, KeyError):
                pass

        items.append(
            InvoiceResponse(
                id=inv.id,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                subtotal=float(inv.subtotal),
                tax_rate=float(inv.tax_rate),
                tax_amount=float(inv.tax_amount),
                total=float(inv.total),
                currency=inv.currency,
                status=inv.status,
                items=invoice_items,
                created_at=inv.created_at,
            )
        )

    return InvoiceListResponse(items=items, total=total)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a specific invoice by ID.

    IDOR Protection: Only the owner can access their invoice.
    """
    service = get_invoice_service(db)
    invoice = service.get_invoice_by_id(invoice_id, user.id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Parse items JSON
    invoice_items = []
    if invoice.items_json:
        try:
            raw_items = json.loads(invoice.items_json)
            invoice_items = [InvoiceItemResponse(**item) for item in raw_items]
        except (json.JSONDecodeError, KeyError):
            pass

    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        subtotal=float(invoice.subtotal),
        tax_rate=float(invoice.tax_rate),
        tax_amount=float(invoice.tax_amount),
        total=float(invoice.total),
        currency=invoice.currency,
        status=invoice.status,
        items=invoice_items,
        created_at=invoice.created_at,
    )


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    user: UserAccount = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Download invoice as PDF.

    IDOR Protection: Only the owner can download their invoice.

    Note: This returns a simple text representation.
    For production, integrate a proper PDF library like ReportLab or weasyprint.
    """
    service = get_invoice_service(db)
    invoice = service.get_invoice_by_id(invoice_id, user.id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Parse customer info
    customer = {}
    if invoice.customer_snapshot:
        try:
            customer = json.loads(invoice.customer_snapshot)
        except json.JSONDecodeError:
            pass

    # Parse billing address
    address = {}
    if invoice.billing_address_snapshot:
        try:
            address = json.loads(invoice.billing_address_snapshot)
        except json.JSONDecodeError:
            pass

    # Parse items
    items = []
    if invoice.items_json:
        try:
            items = json.loads(invoice.items_json)
        except json.JSONDecodeError:
            pass

    # Generate simple text invoice (replace with proper PDF in production)
    invoice_text = f"""
================================================================================
                                RECHNUNG / INVOICE
================================================================================

Rechnungsnummer / Invoice #:  {invoice.invoice_number}
Datum / Date:                 {invoice.invoice_date.strftime("%d.%m.%Y")}
Status:                       {invoice.status.upper()}

--------------------------------------------------------------------------------
RECHNUNGSEMPFÄNGER / BILL TO:
--------------------------------------------------------------------------------
{customer.get('name', 'N/A')}
{customer.get('company_name', '') or ''}
{address.get('street_address', '')}
{address.get('street_address_2', '') or ''}
{address.get('postal_code', '')} {address.get('city', '')}
{address.get('country', '')}

{f"USt-IdNr. / VAT ID: {customer.get('vat_id')}" if customer.get('vat_id') else ''}

--------------------------------------------------------------------------------
POSITIONEN / ITEMS:
--------------------------------------------------------------------------------
"""
    for item in items:
        invoice_text += f"""
{item.get('description', 'N/A')}
  Menge / Qty:     {item.get('quantity', 1)}
  Einzelpreis:     {item.get('unit_price', 0):.2f} {invoice.currency}
  Betrag:          {item.get('amount', 0):.2f} {invoice.currency}
"""

    invoice_text += f"""
--------------------------------------------------------------------------------
ZUSAMMENFASSUNG / SUMMARY:
--------------------------------------------------------------------------------
Zwischensumme / Subtotal:     {float(invoice.subtotal):.2f} {invoice.currency}
MwSt. / VAT ({float(invoice.tax_rate):.0f}%):          {float(invoice.tax_amount):.2f} {invoice.currency}
--------------------------------------------------------------------------------
GESAMTBETRAG / TOTAL:         {float(invoice.total):.2f} {invoice.currency}
================================================================================

{invoice.notes or ''}

Vielen Dank für Ihren Einkauf! / Thank you for your purchase!

Scripe - B2B Lead Generation Platform
https://scripe.io
"""

    # Return as downloadable text file (PDF generation can be added later)
    content = BytesIO(invoice_text.encode("utf-8"))

    return StreamingResponse(
        content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="invoice_{invoice.invoice_number}.txt"'
        },
    )
