import os
import urllib.parse

from fastapi import APIRouter, Request, HTTPException
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.clients.microsoft.outlook_client import OutlookClient
from app.db.database import obter_sessao
from app.db.models import Company
from app.db.models import OutlookClient as OutlookClientDB
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from ...routers_helpers import check_company_access
from .microsoft_helpers import (
    generate_microsoft_auth_credentials,
    get_outlook_client_from_db,
)
from app.schemas.empresa_schema import OutlookClientSchema as OutlookClientSchemaEmpresa
from app.utils.create_agenda_client import create_agenda_client


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
        (access_token, refresh_token, expires_in, expires_at, user_email) = (
            generate_microsoft_auth_credentials(code, company_slug)
        )

        outlook_client_db = await get_outlook_client_from_db(
            company, db, raise_error_if_not_found=False
        )

        if outlook_client_db:
            outlook_client_db.access_token = encrypt_api_key(access_token)
            outlook_client_db.refresh_token = encrypt_api_key(refresh_token)
            outlook_client_db.expires_at = expires_at
            outlook_client_db.default_user = user_email
        else:
            outlook_client = OutlookClientDB(
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


@router.get("/{company_slug}/auth-link")
async def get_auth_link(
    company_slug: str, company: Company = Depends(check_company_access)
):
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI")

    scopes = ["User.Read", "Calendars.ReadWrite", "offline_access"]

    query_parameters = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": company.slug,
            "prompt": "select_account",
        }
    )

    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{query_parameters}"


@router.get("/{company_slug}/timezones")
async def get_timezones(
    company_slug: str,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    outlook_client = create_agenda_client(company, db)
    if isinstance(outlook_client, OutlookClient):
        timezones = await outlook_client.get_timezones()
        return timezones
    # TODO: raise exception if the client is not Outlook
    return None


@router.put("/{company_slug}/timezone", response_model=OutlookClientSchemaEmpresa)
async def update_outlook_timezone(
    company_slug: str,
    request: UpdateTimezoneSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    outlook_client_db = await get_outlook_client_from_db(company, db)

    outlook_client_db.timezone = request.timezone
    db.commit()

    return outlook_client_db
