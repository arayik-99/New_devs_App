from decimal import Decimal
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import authenticate_request as get_current_user
from app.services.cache import get_revenue_summary
from app.services.reservations import (
    PropertyNotFoundError,
    list_properties,
)

router = APIRouter()


def _require_tenant(current_user) -> str:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant is associated with this account.",
        )
    return tenant_id


@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    tenant_id = _require_tenant(current_user)
    return {"properties": await list_properties(tenant_id)}


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = _require_tenant(current_user)

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id)
        total_revenue = float(Decimal(revenue_data['total']))
    except PropertyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property '{property_id}' not found.",
        )

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
