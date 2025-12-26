import os
from fastapi import HTTPException
import requests
from sqlalchemy.orm import Session

from app.db.new_models import Company, GoogleCalendarClient as GoogleCalendarClientDB
from app.exceptions.exceptions import IntegrationAuthException


INTEGRATION_NAME = "Google"
USER_FRIENDLY_ERROR_DETAIL = (
    "Failed to authenticate with Google. Please try again later."
)


async def get_google_calendar_client_from_db(
    company: Company, db: Session, raise_error_if_not_found: bool = True
) -> GoogleCalendarClientDB | None:
    google_calendar_client_db = (
        db.query(GoogleCalendarClientDB).filter_by(company_id=company.id).first()
    )
    if not google_calendar_client_db and raise_error_if_not_found:
        raise HTTPException(
            status_code=404, detail="No Google Calendar client found for this company"
        )
    else:
        return google_calendar_client_db


def generate_google_auth_credentials(code: str, company_slug: str):
    payload = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
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
    access_token = token_data.get("access_token")
    refresh_token = str(token_data.get("refresh_token"))
    expires_in = token_data.get("expires_in")

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
    user_email = user_data.get("email")

    if not user_email:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail="Email not available in user info.",
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    return access_token, refresh_token, expires_in, user_email  # TODO: add typing
