from sqlalchemy.orm import Session
from requests import Response

from app.db.models import EvolutionAPIClient as EvolutionAPIClientDB
from app.clients.evolutionapi_client import EvolutionAPIClient
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import get_resource_from_db


async def get_evolutionapi_client(
    evolutionapi_client_id: int, company_id: int | None, db: Session
) -> EvolutionAPIClient:
    evolutionapi_client_db = await get_resource_from_db(
        EvolutionAPIClientDB, evolutionapi_client_id, db, company_id
    )

    return EvolutionAPIClient(
        evolutionapi_client_db.api_key, evolutionapi_client_db.instance_name, 80000
    )


async def add_evolutionapi_client_to_db(
    response: Response, company_id: int, db: Session
) -> EvolutionAPIClientDB | None:
    response_json: dict = response.json()

    db_api_key = response_json.get("hash", {}).get("apikey")
    db_instance_name = response_json.get("instance", {}).get("instanceName")

    if not db_api_key or not db_instance_name:
        return None

    evolutionapi_client = EvolutionAPIClientDB(
        api_key=encrypt_api_key(db_api_key),
        instance_name=db_instance_name,
        company_id=company_id,
    )

    db.add(evolutionapi_client)
    db.commit()
    db.refresh(evolutionapi_client)

    return evolutionapi_client
