from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Agenda
from app.exceptions.exceptions import ResourceNotFoundException


async def get_agenda(
    company_id: int,
    agenda_id: int,
    db: Session = Depends(obter_sessao),
) -> Agenda:
    agenda = db.query(Agenda).filter_by(id=agenda_id, id_empresa=company_id).first()
    if not agenda:
        raise ResourceNotFoundException(
            resource_type="Agenda",
            resource_id=id,
            detail="Agenda not found for the specified company and ID.",
            user_friendly_detail="Agenda not found.",
            http_status_code=404,
        )

    return agenda
