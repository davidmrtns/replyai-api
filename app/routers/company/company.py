import secrets
from typing import List
from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import get_db_session
from app.db.models import Assistant, AssistantPurposeEnum, Company, User
from app.exceptions.exceptions import ResourceNotFoundException
from app.schemas.company_schema import (
    CompanyMinSchema,
    CompanySchema,
    CreateCompanySchema,
    UpdateCompanySchema,
)
from app.utils.model_utils import apply_model_update
from app.utils.api_key_encryption import encrypt_api_key

from ..routers_helpers import get_logged_in_user, check_company_access


router = APIRouter()


@router.get("/", response_model=List[CompanyMinSchema])
async def get_all_companies(
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(get_db_session),
):
    if not logged_in_user.company_id:
        companies = db.query(Company).all()
    else:
        companies = (
            db.query(Company)
            .filter_by(id=logged_in_user.company_id, is_active=True)
            .all()
        )
    return companies


@router.post("/", response_model=CompanySchema)
async def create_company(
    request: CreateCompanySchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(get_db_session),
):
    if not logged_in_user.company_id:
        company = db.query(Company).filter_by(slug=request.slug).first()
        if not company:
            token = secrets.token_hex(32)

            company = Company(
                company_name=request.company_name,
                slug=request.slug,
                token=token,
                timezone=request.timezone,
                openai_api_key=encrypt_api_key(request.openai_api_key),
                elevenlabs_api_key=encrypt_api_key(request.elevenlabs_api_key),
                is_active=request.is_active,
            )

            db.add(company)
            db.commit()
            db.refresh(company)

            return company
    return None


@router.get("/{company_slug}", response_model=CompanySchema)
async def get_company(
    company_slug: str,
    company: Company = Depends(check_company_access),
):
    return company


@router.patch("/{company_slug}", response_model=CompanySchema)
async def update_company(
    company_slug: str,
    request: UpdateCompanySchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(get_db_session),
):
    update_data = request.model_dump(exclude_unset=True)

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
                resource_id=request.default_assistant_id,
                detail="Assistant not found for the specified company and ID.",
                user_friendly_detail="Assistant not found.",
                http_status_code=404,
            )

    apply_model_update(company, update_data)
    db.commit()
    return company
