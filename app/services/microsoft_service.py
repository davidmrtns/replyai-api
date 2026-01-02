from datetime import datetime, timezone
import os
from fastapi.responses import RedirectResponse
import requests
from sqlalchemy.orm import Session
import urllib.parse

from app.db.models import Company, OutlookClient
from app.exceptions.exceptions import IntegrationException
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.create_agenda_client import build_outlook_client
from app.utils.model_utils import apply_model_update, get_resource_from_db


INTEGRATION_NAME = "Microsoft"
USER_FRIENDLY_ERROR_DETAIL = (
    "Failed to authenticate with Microsoft. Please try again later."
)

SUCCESS_AUTH_URL = os.getenv("SUCCESS_AUTH_URL")
FAILED_AUTH_URL = os.getenv("FAILED_AUTH_URL")
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI")


def _generate_microsoft_auth_credentials(code: str, company_slug: str):
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    tokens_response = requests.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data=payload,
        headers=headers,
    )

    if tokens_response.status_code != 200:
        raise IntegrationException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f"An error occurred while fetching authorization tokens from {INTEGRATION_NAME}: {tokens_response.json()}",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=tokens_response.status_code,
        )

    token_data: dict = tokens_response.json()
    access_token: str = token_data.get("access_token")
    refresh_token: str = token_data.get("refresh_token")
    expires_in: int = token_data.get("expires_in")
    expires_at: int = int(datetime.now(timezone.utc).timestamp() + expires_in)

    graph_headers = {"Authorization": f"Bearer {access_token}"}
    user_info_response = requests.get(
        "https://graph.microsoft.com/v1.0/me", headers=graph_headers
    )

    if user_info_response.status_code != 200:
        raise IntegrationException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f"An error occurred while fetching user info from {INTEGRATION_NAME}: {user_info_response.json()}",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    user_data: dict = user_info_response.json()
    user_email: str = user_data.get("mail") or user_data.get("userPrincipalName")

    if not user_email:
        raise IntegrationException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail="Email not available in user info.",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    return (
        access_token,
        refresh_token,
        expires_in,
        expires_at,
        user_email,
    )


async def generate_auth_callback(company_slug: str, code: str, db: Session):
    if not code:
        raise IntegrationException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail="Code not available in the request.",
            user_friendly_detail="An error occurred while trying to authenticate. Please try again later.",
            status_code=400,
        )

    company = db.query(Company).filter_by(slug=company_slug).first()
    if company:
        access_token, refresh_token, expires_in, expires_at, user_email = (
            _generate_microsoft_auth_credentials(code, company_slug)
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
        return RedirectResponse(url=SUCCESS_AUTH_URL)
    return RedirectResponse(url=FAILED_AUTH_URL)


async def generate_auth_link(company_slug: str) -> str:
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


async def get_timezones(outlook_client_id: int, company_id: int | None, db: Session):
    outlook_client_db = await get_resource_from_db(
        OutlookClient, outlook_client_id, db, company_id
    )
    outlook_client = build_outlook_client(outlook_client_db, db)

    timezones = await outlook_client.get_timezones()
    return timezones


async def update_outlook_timezone(
    outlook_client_id: int,
    payload: UpdateTimezoneSchema,
    company_id: int | None,
    db: Session,
):
    outlook_client_db = await get_resource_from_db(
        OutlookClient, outlook_client_id, db, company_id
    )

    apply_model_update(outlook_client_db, payload)
    db.commit()
    return outlook_client_db
