import os
from fastapi.responses import RedirectResponse
import requests
from sqlalchemy.orm import Session
import urllib.parse

from app.db.models import Company, GoogleCalendarClient
from app.exceptions.exceptions import IntegrationAuthException
from app.schemas.agenda_schema import UpdateTimezoneSchema
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


INTEGRATION_NAME = "Google"
USER_FRIENDLY_ERROR_DETAIL = (
    "Failed to authenticate with Google. Please try again later."
)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SUCCESS_AUTH_URL = os.getenv("SUCCESS_AUTH_URL")
FAILED_AUTH_URL = os.getenv("FAILED_AUTH_URL")


def _generate_google_auth_credentials(code: str, company_slug: str):
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    tokens_response = requests.post(
        "https://oauth2.googleapis.com/token", data=payload, headers=headers
    )

    if tokens_response.status_code != 200:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f"An error occurred while fetching authorization tokens from {INTEGRATION_NAME}: {tokens_response.json()}",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=tokens_response.status_code,
        )

    token_data: dict = tokens_response.json()
    access_token: str = token_data.get("access_token")
    refresh_token: str = str(token_data.get("refresh_token"))
    expires_in: int = token_data.get("expires_in")

    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if user_info_response.status_code != 200:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f"An error occurred while fetching user info from {INTEGRATION_NAME}: {user_info_response.json()}",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    user_data: dict = user_info_response.json()
    user_email: str = user_data.get("email")

    if not user_email:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail="Email not available in user info.",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    return access_token, refresh_token, expires_in, user_email


async def generate_auth_callback(company_slug: str, code: str, db: Session):
    if not code:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail="Code not available in the request.",
            user_friendly_detail="An error occurred while trying to authenticate. Please try again later.",
            status_code=400,
        )

    company = db.query(Company).filter_by(slug=company_slug).first()
    if company:
        access_token, refresh_token, expires_in, user_email = (
            _generate_google_auth_credentials(code, company_slug)
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
        return RedirectResponse(url=SUCCESS_AUTH_URL)
    return RedirectResponse(url=FAILED_AUTH_URL)


async def generate_auth_link(company_slug: str):
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


async def update_google_calendar_timezone(
    google_calendar_client_id: int,
    payload: UpdateTimezoneSchema,
    company_id: int | None,
    db: Session,
):
    google_calendar_client_db = await get_resource_from_db(
        GoogleCalendarClient, google_calendar_client_id, db, company_id
    )

    apply_model_update(google_calendar_client_db, payload)
    db.commit()
    return google_calendar_client_db
