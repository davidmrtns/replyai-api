from sqlalchemy.orm import Session

from app.clients.evolutionapi_client import EvolutionAPIClient
from app.schemas.evolutionapi_client_schema import (
    CreateEvolutionAPIInstanceSchema,
    CreateEvolutionAPIWebhookSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.db.models import EvolutionAPIClient as EvolutionAPIClientDB
from app.utils.model_utils import get_resource_from_db


async def _get_evolutionapi_client(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client_db = await get_resource_from_db(
        EvolutionAPIClientDB, evolutionapi_client_id, db, company_id
    )

    return EvolutionAPIClient(
        evolutionapi_client_db.api_key, evolutionapi_client_db.instance_name, 80000
    )


async def create_instance(
    payload: CreateEvolutionAPIInstanceSchema, company_id: int, db: Session
):
    response = EvolutionAPIClient.create_instance(payload.instance_name)
    response_json: dict = response.json()

    api_key = response_json.get("hash")
    instance_name = response_json.get("instance", {}).get("instanceName")

    evolutionapi_client = EvolutionAPIClientDB(
        api_key=encrypt_api_key(api_key),
        instance_name=instance_name,
        company_id=company_id,
    )

    db.add(evolutionapi_client)
    db.commit()
    db.refresh(evolutionapi_client)

    return evolutionapi_client


async def fetch_instance(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.fetch_instance()
    return response.json()


async def connect_instance(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.connect_instance()
    return response.json()


async def restart_instance(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.restart_instance()
    return response.json()


async def shut_down_instance(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.logout_instance()
    return response.json()


async def check_instance_connection_state(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.check_instance_connection_state()
    return response.json()


async def add_webhook(
    evolutionapi_client_id: int,
    payload: CreateEvolutionAPIWebhookSchema,
    company_id: int | None,
    db: Session,
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.add_webhook(payload.webhook_url, payload.is_enabled)
    return response.json()


async def list_webhooks(
    evolutionapi_client_id: int, company_id: int | None, db: Session
):
    evolutionapi_client = await _get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.list_webhooks()
    return response.json()
