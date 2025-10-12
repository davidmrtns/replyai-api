from sqlalchemy.orm import Session

from app.db.models import Midia
from app.exceptions.exceptions import ResourceNotFoundException


async def get_media_from_db(
    company_id: int,
    media_id: int,
    db: Session
) -> Midia:
    media_db = db.query(Midia).filter_by(id=media_id, id_empresa=company_id).first()
    if not media_db:
        raise ResourceNotFoundException(
            resource_type="Media",
            resource_id=media_id,
            detail="Media not found for the specified company and ID.",
            user_friendly_detail="Media not found.",
            http_status_code=404
        )
    
    return media_db
