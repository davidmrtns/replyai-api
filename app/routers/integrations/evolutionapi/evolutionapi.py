from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.evolutionapi_client_schema import (
    CreateEvolutionAPIInstanceSchema,
    CreateEvolutionAPIWebhookSchema,
    EvolutionAPIInstanceSchema,
)
from .evolutionapi_helpers import add_evolutionapi_client_to_db, get_evolutionapi_client
from ...routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.clients.evolutionapi_client import EvolutionAPIClient


router = APIRouter()


@router.post("/", response_model=EvolutionAPIInstanceSchema)
async def create_instance(
    request: CreateEvolutionAPIInstanceSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    response = EvolutionAPIClient.create_instance(request.instance_name)

    if response.status_code == 201:
        db_register_response = await add_evolutionapi_client_to_db(
            response, company_id, db
        )
        return db_register_response
    return None


@router.get("/{evolutionapi_client_id}")
async def fetch_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.fetch_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.get("/{evolutionapi_client_id}/connect")
async def connect_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.connect_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.put("/{evolutionapi_client_id}/restart")
async def restart_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.restart_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.delete("/{evolutionapi_client_id}/logout")
async def shut_down_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.logout_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.get("/{evolutionapi_client_id}/check-instance-connection")
async def check_instance_connection_state(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.check_instance_connection_state()
    if response.status_code == 200:
        return response.json()
    return None


@router.get("/check-evolutionapi-connection")
async def check_evolutionapi_connection():
    try:
        response = EvolutionAPIClient.check_evolutionapi_connection()
        return response.status_code == 200
    except Exception:
        # TODO: log the exception
        return False


@router.post("/{evolutionapi_client_id}/webhook")
async def add_webhook(
    evolutionapi_client_id: int,
    request: CreateEvolutionAPIWebhookSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.add_webhook(request.webhook_url, request.is_enabled)
    if response.status_code == 201:
        return response.json()
    return None


@router.get("/{evolutionapi_client_id}/webhook")
async def list_webhooks(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    evolutionapi_client = await get_evolutionapi_client(
        evolutionapi_client_id, company_id, db
    )

    response = evolutionapi_client.list_webhooks()
    if response.status_code == 200:
        return response.json()
    return None
