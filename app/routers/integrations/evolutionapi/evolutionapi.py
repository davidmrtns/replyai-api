from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.evolutionapi_client_schema import (
    CreateEvolutionAPIInstanceSchema,
    CreateEvolutionAPIWebhookSchema,
    EvolutionAPIInstanceSchema,
)
from ...routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.services.evolutionapi_service import (
    create_instance as create_instance_service,
    fetch_instance as fetch_instance_service,
    connect_instance as connect_instance_service,
    restart_instance as restart_instance_service,
    shut_down_instance as shut_down_instance_service,
    check_instance_connection_state as check_instance_connection_state_service,
    add_webhook as add_webhook_service,
    list_webhooks as list_webhooks_service,
)


router = APIRouter()


@router.post("/", response_model=EvolutionAPIInstanceSchema)
async def create_instance(
    request: CreateEvolutionAPIInstanceSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_instance_service(request, company_id, db)


@router.get("/{evolutionapi_client_id}")
async def fetch_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await fetch_instance_service(evolutionapi_client_id, company_id, db)


@router.get("/{evolutionapi_client_id}/connect")
async def connect_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await connect_instance_service(evolutionapi_client_id, company_id, db)


# TODO: apparently this endpoint doesn't work anymore
@router.put("/{evolutionapi_client_id}/restart")
async def restart_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await restart_instance_service(evolutionapi_client_id, company_id, db)


@router.delete("/{evolutionapi_client_id}/logout")
async def shut_down_instance(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await shut_down_instance_service(evolutionapi_client_id, company_id, db)


@router.get("/{evolutionapi_client_id}/check-instance-connection")
async def check_instance_connection_state(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await check_instance_connection_state_service(
        evolutionapi_client_id, company_id, db
    )


@router.post("/{evolutionapi_client_id}/webhook")
async def add_webhook(
    evolutionapi_client_id: int,
    request: CreateEvolutionAPIWebhookSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await add_webhook_service(evolutionapi_client_id, request, company_id, db)


@router.get("/{evolutionapi_client_id}/webhook")
async def list_webhooks(
    evolutionapi_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await list_webhooks_service(evolutionapi_client_id, company_id, db)
