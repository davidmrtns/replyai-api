from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company
from app.schemas.agenda_schema import UpdateTimezoneSchema
from ...routers_helpers import check_company_access, get_company_id_from_logged_in_user
from app.schemas.integrations.outlook_schema import OutlookClientSchema
from app.services.microsoft_service import (
    generate_auth_callback,
    generate_auth_link,
    get_timezones as get_timezones_service,
    update_outlook_timezone as update_outlook_timezone_service,
)


router = APIRouter()


@router.get("/callback", include_in_schema=False)
async def auth_callback(code: str, state: str, db: Session = Depends(get_db_session)):
    return await generate_auth_callback(state, code, db)


@router.get("/{company_slug}/auth-link", include_in_schema=False)
async def get_auth_link(company_slug: str, _: Company = Depends(check_company_access)):
    return await generate_auth_link(company_slug)


@router.get("/{outlook_client_id}/timezones")
async def get_timezones(
    outlook_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await get_timezones_service(outlook_client_id, company_id, db)


@router.patch("/{outlook_client_id}/timezone", response_model=OutlookClientSchema)
async def update_outlook_timezone(
    outlook_client_id: int,
    request: UpdateTimezoneSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_outlook_timezone_service(
        outlook_client_id, request, company_id, db
    )
