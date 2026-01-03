import secrets
from sqlalchemy.orm import Session

from app.db.models import (
    Assistant,
    AssistantPurposeEnum,
    Company,
    DigisacClient,
    Department,
)
from app.clients.assistants_client import AssistantsClient
from app.exceptions.exceptions import ResourceNotFoundException, UserAccessException
from app.schemas.company_schema import CreateCompanySchema, UpdateCompanySchema
from app.utils.create_message_client import create_message_client
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.decorators import disabled_func
from app.utils.model_utils import apply_model_update


@disabled_func
async def get_company_data(slug: str, token: str, db: Session):
    company = (
        db.query(Company).filter_by(slug=slug, token=token, is_active=True).first()
    )

    if company is not None:
        message_client = create_message_client(company, db)
        return company, message_client
    return None


@disabled_func
async def get_assistant_from_company(
    company: Company, purpose: str | None, shortcut: str | None, db: Session
):
    if company:
        if purpose:
            assistant_db = (
                db.query(Assistant)
                .filter_by(company_id=company.id, purpose=purpose)
                .first()
            )
        else:
            assistant_db = (
                db.query(Assistant)
                .filter_by(company_id=company.id, shortcut=shortcut)
                .first()
            )
        if assistant_db:
            assistant = AssistantsClient(
                assistant_name=assistant_db.assistant_name,
                openai_assistant_id=assistant_db.openai_assistant_id,
                openai_api_key=company.openai_api_key,
            )
            return assistant, assistant_db.id
    return None, None


@disabled_func
async def get_department(
    company: Company,
    shortcut: str | None,
    is_confirmation_department: bool,
    db: Session,
) -> Department | None:
    if company:
        digisac_client = (
            db.query(DigisacClient).filter_by(company_id=company.id).first()
        )

        if digisac_client:
            if is_confirmation_department:
                department = (
                    db.query(Department)
                    .filter_by(
                        departamento_confirmacao=True,
                        id_digisac_client=digisac_client.id,
                    )
                    .first()
                )
            else:
                department = (
                    db.query(Department)
                    .filter_by(shortcut=shortcut, digisac_client_id=digisac_client.id)
                    .first()
                )
            if department:
                return department
    return None


# Services for company management
async def get_all_companies(company_id: int | None, db: Session):
    if not company_id:
        companies = db.query(Company).all()
    else:
        companies = db.query(Company).filter_by(id=company_id, is_active=True).all()
    return companies


async def create_company(
    company_id: int | None, payload: CreateCompanySchema, db: Session
):
    if not company_id:
        company = db.query(Company).filter_by(slug=payload.slug).first()
        if not company:
            token = secrets.token_hex(32)

            company = Company(
                company_name=payload.company_name,
                slug=payload.slug,
                token=token,
                timezone=payload.timezone,
                openai_api_key=encrypt_api_key(payload.openai_api_key),
                elevenlabs_api_key=encrypt_api_key(payload.elevenlabs_api_key),
                is_active=payload.is_active,
            )

            db.add(company)
            db.commit()
            db.refresh(company)

            return company
    raise UserAccessException(
        detail="The logged-in user doesn't have a company ID.",
        user_friendly_detail="You don't have permission to create a company.",
        http_status_code=400,
    )


async def update_company(payload: UpdateCompanySchema, company: Company, db: Session):
    update_data = payload.model_dump(exclude_unset=True)

    if "openai_api_key" in update_data:
        update_data["openai_api_key"] = encrypt_api_key(update_data["openai_api_key"])

    if "elevenlabs_api_key" in update_data:
        update_data["elevenlabs_api_key"] = encrypt_api_key(
            update_data["elevenlabs_api_key"]
        )

    if "default_assistant_id" in update_data:
        # Checks if the assistant exists and belongs to the company
        assistant = (
            db.query(Assistant)
            .filter_by(
                id=update_data["default_assistant_id"],
                company_id=company.id,
                purpose=AssistantPurposeEnum.reply,
            )
            .first()
        )

        if not assistant:
            raise ResourceNotFoundException(
                resource_type="Assistant",
                resource_id=payload.default_assistant_id,
                detail="Assistant not found for the specified company and ID.",
                user_friendly_detail="Assistant not found.",
                http_status_code=404,
            )

    apply_model_update(company, update_data)
    db.commit()
    return company
