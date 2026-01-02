from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import get_db_session
from app.schemas.asaas_client_schema import (
    AsaasClientSchema,
    CreateAsaasClientSchema,
    UpdateAsaasClientSchema,
)
from ...routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.services.asaas_service import (
    create_asaas_client as create_asaas_client_service,
    update_asaas_client as update_asaas_client_service,
    delete_asaas_client as delete_asaas_client_service,
)


router = APIRouter()


@router.post("/", response_model=AsaasClientSchema)
async def create_asaas_client(
    request: CreateAsaasClientSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_asaas_client_service(request, company_id, db)


@router.patch("/{asaas_client_id}", response_model=AsaasClientSchema)
async def update_asaas_client(
    asaas_client_id: int,
    request: UpdateAsaasClientSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_asaas_client_service(request, asaas_client_id, company_id, db)


@router.delete("/{asaas_client_id}")
async def delete_asaas_client(
    asaas_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_asaas_client_service(asaas_client_id, company_id, db)
