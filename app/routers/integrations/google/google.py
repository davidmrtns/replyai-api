import os
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company
from app.db.models import GoogleCalendarClient
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db
from ...routers_helpers import check_company_access, get_company_id_from_logged_in_user
from .google_helpers import generate_google_auth_credentials
from app.schemas.integrations.google_calendar_schema import GoogleCalendarSchema


router = APIRouter()


@router.get("/callback", include_in_schema=False)
async def auth_callback(code: str, state: str, db: Session = Depends(get_db_session)):
    company_slug = state

    if not code:
        raise HTTPException(
            status_code=400, detail="Code not available in the request."
        )

    company = db.query(Company).filter_by(slug=company_slug).first()
    if company:
        access_token, refresh_token, expires_in, user_email = (
            generate_google_auth_credentials(code, company_slug)
        )

        google_calendar_client_db = (
            db.query(GoogleCalendarClient).filter_by(company_id=company.id).first()
        )

        if google_calendar_client_db:
            update_data = {
                "access_token": encrypt_api_key(access_token),
                "refresh_token": encrypt_api_key(refresh_token),
                "expires_in": str(expires_in),
                "client_email": user_email,
            }
            apply_model_update(google_calendar_client_db, update_data)
        else:
            google_calendar_client = GoogleCalendarClient(
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


@router.get("/{company_slug}/auth-link", include_in_schema=False)
async def get_auth_link(company_slug: str, _: Company = Depends(check_company_access)):
    CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar",
    ]

    query_parameters = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(scopes),
            "access_type": "offline",
            "state": company_slug,
            "prompt": "consent",
        }
    )

    return f"https://accounts.google.com/o/oauth2/auth?{query_parameters}"


@router.patch(
    "/{google_calendar_client_id}/timezone", response_model=GoogleCalendarSchema
)
async def update_google_calendar_timezone(
    google_calendar_client_id: int,
    request: UpdateTimezoneSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    google_calendar_client_db = await get_resource_from_db(
        GoogleCalendarClient, google_calendar_client_id, db, company_id
    )

    apply_model_update(google_calendar_client_db, request)
    db.commit()
    return google_calendar_client_db
