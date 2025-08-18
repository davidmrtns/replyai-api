from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Midia
from app.exceptions.exceptions import ResourceNotFoundException


async def get_media(
    company_id: int,
    media_id: int,
    db: Session = Depends(obter_sessao),
) -> Midia:
    media = db.query(Midia).filter_by(id=media_id, id_empresa=company_id).first()
    if not media:
        raise ResourceNotFoundException(
            resource_type="Media",
            resource_id=id,
            detail="Media not found for the specified company and ID.",
            user_friendly_detail="Media not found.",
            http_status_code=404
        )
    
    return media
