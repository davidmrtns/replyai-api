from sqlalchemy.orm import Session

from app.clients.message_client import MessageClient
from app.db.models import (
    Company,
    DigisacClient as DigisacClientDB,
    EvolutionAPIClient as EvolutionAPIClientDB,
)
from app.clients.digisac_client import DigisacClient
from app.clients.evolutionapi_client import EvolutionAPIClient


def create_message_client(company: Company, db: Session) -> MessageClient | None:
    if company.message_client_type == "digisac":
        digisac_client = (
            db.query(DigisacClientDB).filter_by(company_id=company.id).first()
        )
        if digisac_client:
            return DigisacClient(
                message_client_id=digisac_client.id,
                digisac_slug=digisac_client.digisac_slug,
                service_id=digisac_client.service_id,
                default_user_id=digisac_client.default_user_id,
                digisac_token=digisac_client.digisac_token,
            )
    else:
        evolutionapi_client = (
            db.query(EvolutionAPIClientDB).filter_by(company_id=company.id).first()
        )
        if evolutionapi_client:
            return EvolutionAPIClient(
                message_client_id=evolutionapi_client.id,
                api_key=evolutionapi_client.api_key,
                instance_name=evolutionapi_client.instance_name,
                delay_amount=80000,
            )
    return None
