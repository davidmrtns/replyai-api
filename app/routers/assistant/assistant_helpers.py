from openai import OpenAI
from sqlalchemy.orm import Session

from app.db.models import Company
from app.clients.assistants_client import CustomHTTPClient
from app.utils.api_key_encryption import decrypt_api_key


def get_openai_client(company_id: int, db: Session) -> OpenAI:
    company = db.query(Company).filter_by(id=company_id).first()

    return OpenAI(
        http_client=CustomHTTPClient(), api_key=decrypt_api_key(company.openai_api_key)
    )
