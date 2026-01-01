import os
import urllib.parse

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company
from app.db.models import OutlookClient
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.create_agenda_client import build_outlook_client
from app.utils.model_utils import apply_model_update, get_resource_from_db
from ...routers_helpers import check_company_access, get_company_id_from_logged_in_user
from .microsoft_helpers import generate_microsoft_auth_credentials
from app.schemas.integrations.outlook_schema import OutlookClientSchema


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
        access_token, refresh_token, expires_in, expires_at, user_email = (
            generate_microsoft_auth_credentials(code, company_slug)
        )

        outlook_client_db = (
            db.query(OutlookClient).filter_by(company_id=company.id).first()
        )

        if outlook_client_db:
            update_data = {
                "access_token": encrypt_api_key(access_token),
                "refresh_token": encrypt_api_key(refresh_token),
                "expires_at": expires_at,
                "default_user": user_email,
            }
            apply_model_update(outlook_client_db, update_data)
        else:
            outlook_client = OutlookClient(
                access_token=encrypt_api_key(access_token),
                refresh_token=encrypt_api_key(refresh_token),
                expires_in=expires_in,
                expires_at=expires_at,
                default_user=user_email,
                timezone="",  # TODO: make it optional or set a default value
                company_id=company.id,
            )
            db.add(outlook_client)
        db.commit()
        return RedirectResponse(url=os.getenv("SUCCESS_AUTH_URL"))
    return RedirectResponse(url=os.getenv("FAILED_AUTH_URL"))


@router.get("/{company_slug}/auth-link", include_in_schema=False)
async def get_auth_link(company_slug: str, _: Company = Depends(check_company_access)):
    CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
    REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI")

    scopes = ["User.Read", "Calendars.ReadWrite", "offline_access"]

    query_parameters = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": company_slug,
            "prompt": "select_account",
        }
    )

    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query_parameters}"


@router.get("/{outlook_client_id}/timezones")
async def get_timezones(
    outlook_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    outlook_client_db = await get_resource_from_db(
        OutlookClient, outlook_client_id, db, company_id
    )
    outlook_client = build_outlook_client(outlook_client_db, db)

    timezones = await outlook_client.get_timezones()
    return timezones


@router.patch("/{outlook_client_id}/timezone", response_model=OutlookClientSchema)
async def update_outlook_timezone(
    outlook_client_id: int,
    request: UpdateTimezoneSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    outlook_client_db = await get_resource_from_db(
        OutlookClient, outlook_client_id, db, company_id
    )

    apply_model_update(outlook_client_db, request)
    db.commit()
    return outlook_client_db
