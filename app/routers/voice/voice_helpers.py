from sqlalchemy.orm import Session

from app.clients.elevenlabs_client import ElevenLabsClient
from app.db.models import Company


def get_elevenlabs_client(company_id: int, db: Session) -> ElevenLabsClient:
    company = db.query(Company).filter_by(id=company_id).first()
    return ElevenLabsClient(company.elevenlabs_api_key)
