import secrets
from sqlalchemy.orm import Session

from app.db.models import (
    Assistant,
    AssistantPurposeEnum,
    Company,
)
from app.exceptions.exceptions import ResourceNotFoundException, UserAccessException
from app.schemas.company_schema import CreateCompanySchema, UpdateCompanySchema
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update


def get_company_by_slug_and_token(
    company_slug: str, token: str, db: Session
) -> Company | None:
    company = db.query(Company).filter_by(slug=company_slug, token=token).first()
    return company


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
