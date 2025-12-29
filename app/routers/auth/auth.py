from fastapi import APIRouter, Response
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company, User
from app.exceptions.exceptions import UserAccessException
from app.utils.password_utils import create_access_token, verify_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")
router = APIRouter()


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
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
