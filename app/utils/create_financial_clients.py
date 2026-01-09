from sqlalchemy.orm import Session
from typing import List

from app.clients.asaas_client import AsaasClient
from app.db.models import Company, AsaasClient as AsaasClientDB


def create_financial_clients(
    company: Company, db: Session, client_number: int | None = None
) -> List[AsaasClient]:
    if company.financial_client_type != "asaas":
        return []

    query = db.query(AsaasClientDB).filter_by(id_empresa=company.id)

    if client_number is not None:
        query = query.filter_by(client_number=client_number)

    clients = [AsaasClient(token=c.token) for c in query.all()]
    return clients
