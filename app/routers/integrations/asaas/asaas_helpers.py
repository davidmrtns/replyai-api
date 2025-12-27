from sqlalchemy.orm import Session

from app.db.models import AsaasClient, User
from app.exceptions.exceptions import ResourceNotFoundException


async def get_asaas_client_from_db(
    asaas_client_id: int, logged_in_user: User, db: Session
):
    query = db.query(AsaasClient).filter_by(id=asaas_client_id)
    if logged_in_user.company_id:
        query = query.filter_by(company_id=logged_in_user.company_id)

    asaas_client = query.first()

    if not asaas_client:
        raise ResourceNotFoundException(
            resource_type="Asaas Client",
            resource_id=asaas_client_id,
            detail="Asaas Client not found for the specified company and ID.",
            user_friendly_detail="Asaas Client not found.",
            http_status_code=404,
        )
    return asaas_client
