from fastapi import APIRouter, Response
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.services.auth_service import login as login_service, logout as logout_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")
router = APIRouter()


@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
):
    return login_service(response, form_data, db)


@router.post("/logout")
def logout(response: Response):
    return logout_service(response)
