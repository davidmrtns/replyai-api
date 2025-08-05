from sqlalchemy.orm import Session

from app.db.new_models import Company, DigisacClient, EvolutionAPIClient
from app.utils.digisac import Digisac
from app.utils.evolutionapi import EvolutionAPI
from app.utils.message_client import MessageClient


def create_message_client(company: Company, db: Session) -> MessageClient | None:
    if company.message_client_type == 'digisac':
        digisac_client = db.query(DigisacClient).filter_by(company_id=company.id).first()
        if digisac_client:
            return Digisac(
                slug=digisac_client.digisac_slug,
                service_id=digisac_client.service_id,
                defaultUserId=digisac_client.digisac_default_user,
                token=digisac_client.digisac_token,
                defaultAssistantName=company.default_assistant.assistant_name,
            )
    else:
        evolutionapi_client = db.query(EvolutionAPIClient).filter_by(company_id=company.id).first()
        if evolutionapi_client:
            return EvolutionAPI(
                api_key=evolutionapi_client.api_key,
                instance=evolutionapi_client.instance_name,
                defaultAssistantName=company.default_assistant.assistant_name
            )
    return None
