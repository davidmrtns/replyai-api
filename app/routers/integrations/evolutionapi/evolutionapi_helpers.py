from fastapi import HTTPException
from sqlalchemy.orm import Session
from requests import Response

from app.db.new_models import Company, EvolutionAPIClient as EvolutionAPIClientDB
from app.clients.evolutionapi_client import EvolutionAPIClient
from app.utils.api_key_encryption import encrypt_api_key


async def get_evolutionapi_client(
    company: Company, api_key: str, db: Session
) -> EvolutionAPIClient:  # TODO: maybe unify with the method in message_service
    evolutionapi_db = (
        db.query(EvolutionAPIClientDB)
        .filter_by(api_key=api_key, company_id=company.id)
        .first()
    )
    if evolutionapi_db:
        return EvolutionAPIClient(
            evolutionapi_db.api_key, evolutionapi_db.instance_name, 80000
        )
    else:
        raise HTTPException(
            status_code=404, detail="No EvolutionAPI client found for this company"
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
