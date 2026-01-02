from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company
from app.schemas.agenda_schema import UpdateTimezoneSchema
from ...routers_helpers import check_company_access, get_company_id_from_logged_in_user
from app.schemas.integrations.google_calendar_schema import GoogleCalendarSchema
from app.services.google_service import (
    generate_auth_callback,
    generate_auth_link,
    update_google_calendar_timezone as update_google_calendar_timezone_service,
)


router = APIRouter()


@router.get("/callback", include_in_schema=False)
async def auth_callback(code: str, state: str, db: Session = Depends(get_db_session)):
    return await generate_auth_callback(state, code, db)


@router.get("/{company_slug}/auth-link", include_in_schema=False)
async def get_auth_link(company_slug: str, _: Company = Depends(check_company_access)):
    return await generate_auth_link(company_slug)


@router.patch(
    "/{google_calendar_client_id}/timezone", response_model=GoogleCalendarSchema
)
async def update_google_calendar_timezone(
    google_calendar_client_id: int,
    request: UpdateTimezoneSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_google_calendar_timezone_service(
        google_calendar_client_id, request, company_id, db
    )
