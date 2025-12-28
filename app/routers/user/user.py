from fastapi import APIRouter, Response, Query
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import obter_sessao
from app.db.models import Company, User
from app.exceptions.exceptions import UserAccessException
from app.schemas.user_schema import (
    CreateUserSchema,
    UpdateUserSchema,
    UserListSchema,
    UserSchema,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db
from ..routers_helpers import get_logged_in_user
from app.utils.password_utils import verify_password, create_access_token, hash_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")
router = APIRouter()


@router.post("/", response_model=UserSchema)
async def create_user(
    request: CreateUserSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    if logged_in_user.is_admin:
        hashed_password = hash_password(request.password)

        # If the logged-in user is an admin but not tied to a company, they can specify the company for the new user
        if not logged_in_user.company_id:
            company_id = request.company_id
        else:
            company_id = logged_in_user.company_id

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
    raise UserAccessException(
        detail="The logged-in user is not an admin.",
        user_friendly_detail="You don't have permission to perform this action.",
        http_status_code=403,
    )


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    request: UpdateUserSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    # If the logged-in user is an admin, they can edit any user
    if logged_in_user.is_admin:
        user_to_edit_id = user_id
    elif user_id == logged_in_user.id:
        user_to_edit_id = logged_in_user.id
    else:
        user_to_edit_id = None

    if user_to_edit_id:
        query = db.query(User).filter_by(id=user_to_edit_id)
        if logged_in_user.company_id:
            query = query.filter_by(company_id=logged_in_user.company_id)
        user = query.first()

        if not user:
            raise UserAccessException(
                detail="User to edit was not found in the database.",
                user_friendly_detail="The user was not found, or you don't have permission to edit it.",
                http_status_code=404,
            )

        update_data = request.model_dump(exclude_unset=True)

        if "new_password" in update_data:
            update_data.pop("new_password_confirmation")
            update_data["password"] = hash_password(update_data.pop("new_password"))

        apply_model_update(user, update_data)
        db.commit()
        return user
    raise UserAccessException(
        detail="The logged-in user is not an admin, or is trying to edit another user.",
        user_friendly_detail="You don't have permission to edit this user.",
        http_status_code=403,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    # Only admins can delete users
    if logged_in_user.is_admin:
        user = get_resource_from_db(User, user_id, db, logged_in_user.company_id)

        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    raise UserAccessException(
        detail="The logged-in user is not an admin.",
        user_friendly_detail="You don't have permission to edit this user.",
        http_status_code=403,
    )


@router.get("/all", response_model=UserListSchema)
async def get_all_users(
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
    cursor: Optional[int] = Query(
        None, alias="cursor", description="Last user ID from the previous page"
    ),
    limit: int = Query(
        10, alias="limit", ge=1, le=50, description="NNumber of records per page"
    ),
):
    if not logged_in_user.is_admin:
        raise UserAccessException(
            detail="The logged-in user is not an admin.",
            user_friendly_detail="You don't have permission to perform this action.",
            http_status_code=403,
        )

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


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(obter_sessao),
):
    user = (
        db.query(User)
        .filter(User.email == form_data.username, User.is_active == True)
        .first()
    )

    if not user:
        raise UserAccessException(
            detail="User not found with this email.",
            user_friendly_detail="No user was found with this email.",
            http_status_code=404,
        )

    if user.company_id:
        company = db.query(Company).filter_by(id=user.company_id).first()
        if not company.is_active:
            raise UserAccessException(
                detail="The user company is deactivated.",
                user_friendly_detail="You can't log in because the company associated with your account is deactivated. Contact the system admin.",
                http_status_code=401,
            )

    if not verify_password(form_data.password, user.password):
        raise UserAccessException(
            detail="The password is incorrect.",
            user_friendly_detail="Incorret credentials.",
            http_status_code=401,
        )

    access_token = create_access_token(data={"sub": user.email})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
    )
    return True


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return True
