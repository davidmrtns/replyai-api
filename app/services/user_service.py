from sqlalchemy.orm import Session

from app.db.models import User
from app.exceptions.exceptions import MalformedRequestException
from app.schemas.user_schema import CreateUserSchema, UserListSchema
from app.utils.model_utils import apply_model_update, get_resource_from_db
from app.utils.password_utils import hash_password


def create_user(payload: CreateUserSchema, company_id: int, db: Session):
    hashed_password = hash_password(payload.password)

    new_user = User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
        is_active=payload.is_active,
        is_admin=payload.is_admin,
        company_id=company_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def update_user(
    logged_in_user: User, user_id: int, payload: CreateUserSchema, db: Session
):
    # If the logged-in user is an admin, they can edit any user
    if logged_in_user.is_admin:
        user_to_edit_id = user_id
    elif user_id == logged_in_user.id:
        user_to_edit_id = logged_in_user.id
    else:
        user_to_edit_id = None

    if user_to_edit_id:
        user = get_resource_from_db(User, user_id, db, logged_in_user.company_id)

        update_data = payload.model_dump(exclude_unset=True)

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


def delete_user(user_id: int, company_id: int | None, db: Session):
    user = get_resource_from_db(User, user_id, db, company_id)

    if user:
        db.delete(user)
        db.commit()
        return True
    return False


def get_all_users(logged_in_user: User, limit: int, cursor: int | None, db: Session):
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
