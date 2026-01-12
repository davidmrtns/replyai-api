from sqlalchemy.orm import Session

from app.db.models import AsaasClient
from app.exceptions.exceptions import ConflictingRequestException
from app.schemas.asaas_client_schema import (
    CreateAsaasClientSchema,
    UpdateAsaasClientSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


def create_asaas_client(payload: CreateAsaasClientSchema, company_id: int, db: Session):
    asaas_client = (
        db.query(AsaasClient)
        .filter_by(
            id_empresa=company_id,
            client_number=payload.client_number,
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
        token=encrypt_api_key(payload.token),
        label=payload.label,
        client_number=payload.client_number,
        company_id=company_id,
    )

    db.add(asaas_client)
    db.commit()
    db.refresh(asaas_client)

    return asaas_client


def update_asaas_client(
    asaas_client_id: int,
    payload: UpdateAsaasClientSchema,
    company_id: int | None,
    db: Session,
):
    update_data = payload.model_dump(exclude_unset=True)

    if "token" in update_data:
        update_data["token"] = encrypt_api_key(update_data["token"])

    asaas_client = get_resource_from_db(AsaasClient, asaas_client_id, db, company_id)

    apply_model_update(asaas_client, update_data)
    db.commit()
    return asaas_client


def delete_asaas_client(asaas_client_id: int, company_id: int | None, db: Session):
    asaas_client = get_resource_from_db(AsaasClient, asaas_client_id, db, company_id)

    if asaas_client:
        db.delete(asaas_client)
        db.commit()
        return True
    return False
