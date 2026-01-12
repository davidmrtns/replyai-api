from fastapi import APIRouter, Query
from fastapi.params import Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db_session
from app.db.models import User
from app.schemas.user_schema import (
    CreateUserSchema,
    UpdateUserSchema,
    UserListSchema,
    UserSchema,
)
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
    get_logged_in_user,
    require_admin_user,
)
from app.services.user_service import (
    create_user as create_user_service,
    update_user as update_user_service,
    delete_user as delete_user_service,
    get_all_users as get_all_users_service,
)


router = APIRouter()


@router.post("/", response_model=UserSchema)
def create_user(
    request: CreateUserSchema,
    _=Depends(require_admin_user),
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return create_user_service(request, company_id, db)


@router.patch("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    request: UpdateUserSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return update_user_service(logged_in_user, user_id, request, db)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    _=Depends(require_admin_user),
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return delete_user_service(user_id, company_id, db)


@router.get("/all", response_model=UserListSchema)
def get_all_users(
    _=Depends(require_admin_user),
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(get_db_session),
    cursor: Optional[int] = Query(
        None, alias="cursor", description="Last user ID from the previous page"
    ),
    limit: int = Query(
        10, alias="limit", ge=1, le=50, description="Number of records per page"
    ),
):
    return get_all_users_service(logged_in_user, limit, cursor, db)
