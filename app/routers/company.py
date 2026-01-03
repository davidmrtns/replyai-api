from typing import List
from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import get_db_session
from app.db.models import Company
from app.schemas.company_schema import (
    CompanyMinSchema,
    CompanySchema,
    CreateCompanySchema,
    UpdateCompanySchema,
)
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    check_company_access,
)
from app.services.company_service import (
    get_all_companies as get_all_companies_service,
    create_company as create_company_service,
    update_company as update_company_service,
)


router = APIRouter()


@router.get("/", response_model=List[CompanyMinSchema])
async def get_all_companies(
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await get_all_companies_service(company_id, db)


@router.post("/", response_model=CompanySchema)
async def create_company(
    request: CreateCompanySchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await create_company_service(company_id, request, db)


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
    return await update_company_service(company, request, db)
