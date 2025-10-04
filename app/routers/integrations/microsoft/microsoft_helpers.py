from datetime import datetime, timezone
import os
from fastapi import HTTPException
import requests
from sqlalchemy.orm import Session

from app.db.new_models import Company, OutlookClient as OutlookClientDB
from app.exceptions.exceptions import IntegrationAuthException


INTEGRATION_NAME = 'Microsoft'
USER_FRIENDLY_ERROR_DETAIL = 'Failed to authenticate with Microsoft. Please try again later.'


async def get_outlook_client_from_db(
        company: Company,
        db: Session,
        raise_error_if_not_found: bool = True
) -> OutlookClientDB | None:
    outlook_client_db = db.query(OutlookClientDB).filter_by(company_id=company.id).first()
    if not outlook_client_db and raise_error_if_not_found:
        raise HTTPException(status_code=404, detail='No Outlook client found for this company')
    else:
        return outlook_client_db


def generate_microsoft_auth_credentials(
        code: str,
        company_slug: str
):
    payload = {
        'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
        'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': os.getenv('MICROSOFT_REDIRECT_URI'),
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    tokens_response = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token', data=payload, headers=headers)

    if tokens_response.status_code != 200:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f'An error occurred while fetching authorization tokens from {INTEGRATION_NAME}: {tokens_response.json()}',
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=tokens_response.status_code,
        )

    token_data: dict = tokens_response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in')
    expires_at = datetime.now(timezone.utc).timestamp() + expires_in

    graph_headers = {'Authorization': f'Bearer {access_token}'}
    user_info_response = requests.get('https://graph.microsoft.com/v1.0/me', headers=graph_headers)

    if user_info_response.status_code != 200:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail=f'An error occurred while fetching user info from {INTEGRATION_NAME}: {user_info_response.json()}',
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )

    user_data: dict = user_info_response.json()
    user_email = user_data.get('mail') or user_data.get('userPrincipalName')

    if not user_email:
        raise IntegrationAuthException(
            integration_name=INTEGRATION_NAME,
            company_slug=company_slug,
            detail='Email not available in user info.',
            user_friendly_detail=USER_FRIENDLY_ERROR_DETAIL,
            status_code=user_info_response.status_code,
        )
    
    return access_token, refresh_token, expires_in, expires_at, user_email # TODO: add typing
