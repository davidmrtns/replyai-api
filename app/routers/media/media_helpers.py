from sqlalchemy.orm import Session

from app.db.models import Media
from app.exceptions.exceptions import ResourceNotFoundException


async def get_media_from_db(company_id: int, media_id: int, db: Session) -> Media:
    media_db = db.query(Media).filter_by(id=media_id, company_id=company_id).first()
    if not media_db:
        raise ResourceNotFoundException(
            resource_type="Media",
            resource_id=media_id,
            detail="Media not found for the specified company and ID.",
            user_friendly_detail="Media not found.",
            http_status_code=404,
        )

    return media_db
