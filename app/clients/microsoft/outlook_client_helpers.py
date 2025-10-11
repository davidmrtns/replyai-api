from datetime import datetime, timezone
import msal
import os
from typing import NamedTuple
from sqlalchemy.orm import Session
from azure.core.credentials import TokenCredential, AccessToken

from app.db.new_models import OutlookClient as OutlookClientDB
from app.utils.api_key_encryption import decrypt_api_key


class CredentialData(NamedTuple):
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: float


class OutlookAccessTokenCredential(TokenCredential):
    def __init__(self, credential_data: CredentialData, client_db: OutlookClientDB, db: Session):
        client_id = os.getenv('MICROSOFT_CLIENT_ID')
        client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')

        decrypted_access_token = decrypt_api_key(credential_data.access_token)
        decrypted_refresh_token = decrypt_api_key(credential_data.refresh_token)

        self.access_token = decrypted_access_token
        self.refresh_token = decrypted_refresh_token
        self.expires_at = credential_data.expires_at
        self.expires_in = credential_data.expires_in
        self.client_db = client_db
        self.db_session = db

        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f'https://login.microsoftonline.com/common'
        )


    def is_token_expired(self):
        return datetime.now(timezone.utc).timestamp() >= self.client_db.expires_at - 60


    def get_token(self):
        if not self.is_token_expired():
            return AccessToken(self.access_token, self.expires_in)

        result = self.app.acquire_token_by_refresh_token(
            refresh_token=self.refresh_token,
            scopes=['https://graph.microsoft.com/.default']
        )

        if 'access_token' in result:
            access_token: str = result.get('access_token')
            refresh_token = result.get('refresh_token', self.refresh_token)
            expires_in = result.get('expires_in')

            self.client_db.access_token = access_token
            self.client_db.refresh_token = refresh_token
            self.client_db.expires_in = expires_in
            self.client_db.expires_at = datetime.now(timezone.utc).timestamp() + expires_in
            self.db_session.commit()

            return AccessToken(self.access_token, result['expires_in'])
        else:
            # TODO: raise custom exception
            raise Exception(f"Error while renewing token: {result.get('error_description', 'Unknown error')}")

