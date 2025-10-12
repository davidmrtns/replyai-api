from sqlalchemy.orm import Session

from app.clients.elevenlabs_client import ElevenLabsClient
from app.db.new_models import Company, Voice
from app.exceptions.exceptions import ResourceNotFoundException


def get_voice_from_db(
        company_id: int,
        voice_id: int,
        db: Session
) -> Voice:
    voice_db = db.query(Voice).filter_by(id=voice_id, id_empresa=company_id).first()
    if not voice_db:
        raise ResourceNotFoundException(
            resource_type="Voice",
            resource_id=voice_id,
            detail="Voice not found for the specified company and ID.",
            user_friendly_detail="Voice not found.",
            http_status_code=404
        )
    
    return voice_db


def get_elevenlabs_client(company: Company) -> ElevenLabsClient:
    return ElevenLabsClient(company.elevenlabs_api_key)
