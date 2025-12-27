from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import obter_sessao
from app.db.models import AsaasClient, User
from app.exceptions.exceptions import ConflictingRequestException
from .asaas_helpers import get_asaas_client_from_db
from app.schemas.asaas_client_schema import (
    AsaasClientSchema,
    CreateAsaasClientSchema,
    UpdateAsaasClientSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.apply_model_update import apply_model_update
from ...routers_helpers import (
    get_logged_in_user,
    require_auth,
    validate_company_id,
    validate_company_id,
)


router = APIRouter(dependencies=[Depends(require_auth)])


# TODO: maybe add a GET endpoint to list asaas clients, or get one by ID


@router.post("/", response_model=AsaasClientSchema)
async def create_asaas_client(
    request: CreateAsaasClientSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    validate_company_id(logged_in_user, request)

    asaas_client = (
        db.query(AsaasClient)
        .filter_by(
            id_empresa=logged_in_user.company_id or request.company_id,
            client_number=request.client_number,
        )
        .first()
    )
    if asaas_client:
        raise ConflictingRequestException(
            detail="The company already has an Asaas client with this client number. Try again with a different client number.",
            user_friendly_detail="This company already has an Asaas client with this client number.",
            http_status_code=409,
        )

    asaas_client = AsaasClient(
        token=encrypt_api_key(request.token),
        label=request.label,
        client_number=request.client_number,
        company_id=logged_in_user.company_id or request.company_id,
    )

    db.add(asaas_client)
    db.commit()
    db.refresh(asaas_client)

    return asaas_client


@router.patch("/{asaas_client_id}", response_model=AsaasClientSchema)
async def update_asaas_client(
    asaas_client_id: int,
    request: UpdateAsaasClientSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    update_data = request.model_dump(exclude_unset=True)

    if "token" in update_data:
        update_data["token"] = encrypt_api_key(update_data["token"])

    asaas_client = await get_asaas_client_from_db(asaas_client_id, logged_in_user, db)

    apply_model_update(asaas_client, update_data)
    db.commit()
    return asaas_client


@router.delete("/{asaas_client_id}")
async def delete_asaas_client(
    asaas_client_id: int,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    asaas_client = await get_asaas_client_from_db(asaas_client_id, logged_in_user, db)

    if asaas_client:
        db.delete(asaas_client)
        db.commit()
        return True
    return False
