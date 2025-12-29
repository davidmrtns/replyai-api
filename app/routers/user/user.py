from fastapi import APIRouter, Query
from fastapi.params import Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db_session
from app.db.models import User
from app.exceptions.exceptions import MalformedRequestException
from app.schemas.user_schema import (
    CreateUserSchema,
    UpdateUserSchema,
    UserListSchema,
    UserSchema,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db
from ..routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
    get_logged_in_user,
    require_admin_user,
)
from app.utils.password_utils import hash_password


router = APIRouter()


@router.post("/", response_model=UserSchema)
async def create_user(
    request: CreateUserSchema,
    _=Depends(require_admin_user),
    company_id: int | None = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    hashed_password = hash_password(request.password)

    new_user = User(
        name=request.name,
        email=request.email,
        password=hashed_password,
        is_active=request.is_active,
        is_admin=request.is_admin,
        company_id=company_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    request: UpdateUserSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(get_db_session),
):
    # If the logged-in user is an admin, they can edit any user
    if logged_in_user.is_admin:
        user_to_edit_id = user_id
    elif user_id == logged_in_user.id:
        user_to_edit_id = logged_in_user.id
    else:
        user_to_edit_id = None

    if user_to_edit_id:
        user = await get_resource_from_db(User, user_id, db, logged_in_user.company_id)

        update_data = request.model_dump(exclude_unset=True)

        if "new_password" in update_data:
            update_data.pop("new_password_confirmation")
            update_data["password"] = hash_password(update_data.pop("new_password"))

        apply_model_update(user, update_data)
        db.commit()
        return user
    raise MalformedRequestException(
        detail="The logged-in user is not an admin, or is trying to edit another user.",
        user_friendly_detail="You don't have permission to edit this user.",
        http_status_code=400,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    _=Depends(require_admin_user),
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    user = await get_resource_from_db(User, user_id, db, company_id)
    print(user.__dict__)

    if user:
        db.delete(user)
        db.commit()
        return True
    return False


@router.get("/all", response_model=UserListSchema)
async def get_all_users(
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
    query = db.query(User).order_by(User.id.asc())
    if logged_in_user.company_id:  # if user is tied to a company, filter by it
        query = query.filter(User.company_id == logged_in_user.company_id)
    if cursor:
        query = query.filter(User.id > cursor)

    users = query.limit(limit + 1).all()
    has_more = len(users) > limit

    if len(users) > limit:
        users.pop(-1)

    next_cursor = users[-1].id if has_more else None

    return UserListSchema(
        has_more=has_more, next_cursor=next_cursor, limit=limit, data=users
    )
