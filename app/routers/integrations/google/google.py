import os
import urllib.parse

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Company
from app.db.models import GoogleCalendarClient as GoogleCalendarClientDB
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from ...routers_helpers import check_company_access
from .google_helpers import (
    generate_google_auth_credentials,
    get_google_calendar_client_from_db,
)
from app.schemas.empresa_schema import GoogleCalendarSchema


router = APIRouter()


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(obter_sessao)):
    code = request.query_params.get("code")
    company_slug = request.query_params.get("state")

    if not code:
        raise HTTPException(
            status_code=400, detail="Code not available in the request."
        )

    company = db.query(Company).filter_by(slug=company_slug).first()
    if company:
        access_token, refresh_token, expires_in, user_email = (
            generate_google_auth_credentials(code, company_slug)
        )
        google_calendar_client_db = await get_google_calendar_client_from_db(
            company, db, raise_error_if_not_found=False
        )

        if google_calendar_client_db:
            google_calendar_client_db.access_token = encrypt_api_key(access_token)
            google_calendar_client_db.refresh_token = encrypt_api_key(refresh_token)
            google_calendar_client_db.expires_in = str(expires_in)
            google_calendar_client_db.client_email = user_email
        else:
            google_calendar_client = GoogleCalendarClientDB(
                access_token=encrypt_api_key(access_token),
                refresh_token=encrypt_api_key(refresh_token),
                expires_in=expires_in,
                client_email=user_email,
                timezone="",  # TODO: make it optional or set a default value
                company_id=company.id,
            )
            db.add(google_calendar_client)

        db.commit()
        return RedirectResponse(url=os.getenv("SUCCESS_AUTH_URL"))
    return RedirectResponse(url=os.getenv("FAILED_AUTH_URL"))


@router.get("/{company_slug}/auth-link")
async def get_auth_link(
    company_slug: str, company: Company = Depends(check_company_access)
):

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar",
    ]

    query_parameters = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "access_type": "offline",
            "state": company.slug,
            "prompt": "consent",
        }
    )

    return f"https://accounts.google.com/o/oauth2/auth?{query_parameters}"


@router.put("/{company_slug}/timezone", response_model=GoogleCalendarSchema)
async def update_google_calendar_timezone(
    company_slug: str,
    request: UpdateTimezoneSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    googlecalendar_client_db = await get_google_calendar_client_from_db(company, db)

    googlecalendar_client_db.timezone = request.timezone
    db.commit()

    return googlecalendar_client_db
