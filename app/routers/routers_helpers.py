from fastapi.security import APIKeyHeader
import jwt
from fastapi import Depends, Request, Security
from fastapi.params import Depends, Cookie
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Company, User
from app.exceptions.exceptions import (
    MalformedRequestException,
    NoAccessToCompanyException,
    UserAccessException,
)
from app.utils.password_utils import SECRET_KEY, ALGORITHM


def get_logged_in_user(
    token: str = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db_session),
) -> User:
    """
    Retrieves the logged-in user based on the provided JWT token.
    """
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise UserAccessException(
                detail="No email provided.",
                user_friendly_detail="Your email is not present in the request. Try logging in again.",
                http_status_code=403,
            )
    except:
        raise UserAccessException(
            detail="Not authenticated.",
            user_friendly_detail="You are not logged in. Try again.",
            http_status_code=401,
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise UserAccessException(
            detail="User not found.",
            user_friendly_detail="No user found with this email.",
            http_status_code=404,
        )

    return user


def check_company_access(
    company_slug: str,
    db: Session = Depends(get_db_session),
    logged_in_user: User = Depends(get_logged_in_user),
) -> Company:
    """
    Checks if the logged-in user has access to the company with the given slug.

    Raises NoAccessToCompanyException if the company does not exist or the user does not have access.
    """

    company = db.query(Company).filter_by(slug=company_slug).first()
    if not company:
        raise NoAccessToCompanyException(
            company_slug=company_slug,
            detail="Company does not exist on database.",
            user_friendly_detail="Company not found.",
            http_status_code=404,
        )

    if logged_in_user.company_id is not None and (
        logged_in_user.company_id != company.id or not company.is_active
    ):
        raise NoAccessToCompanyException(
            company_slug=company_slug,
            detail="User does not have access to this company.",
            user_friendly_detail="You don't have permission to access this company.",
            http_status_code=403,
        )

    return company


async def get_company_id_from_user_or_request(
    request: Request,
    logged_in_user: User = Depends(get_logged_in_user),
) -> int:
    """
    Retrieves the company ID either from the logged-in user or from the request body.

    Raises MalformedRequestException if neither is provided.
    """
    body = await request.json()
    body_company_id = body.get("company_id")

    if logged_in_user.company_id:
        if body_company_id and body_company_id != logged_in_user.company_id:
            raise MalformedRequestException(
                detail="The logged-in is tied to a company, but a different company ID was provided in the request.",
                user_friendly_detail="You cannot specify a different company for this action.",
                http_status_code=400,
            )
        return logged_in_user.company_id
    elif body_company_id:
        return body_company_id
    else:
        raise MalformedRequestException(
            detail="The logged-in user doesn't have a company ID and it was not provided in the request body.",
            user_friendly_detail="You must specify a company for the employee if the logged-in user is not tied to a company.",
            http_status_code=400,
        )


def get_company_id_from_logged_in_user(
    logged_in_user: User = Depends(get_logged_in_user),
) -> int | None:
    """
    Retrieves the company ID from the logged-in user.

    Returns None if the user is not tied to any company.
    """
    return logged_in_user.company_id


def require_admin_user(
    logged_in_user: User = Depends(get_logged_in_user),
):
    """
    Ensures that the logged-in user is an admin.

    Raises UserAccessException if the user is not an admin.
    """
    if not logged_in_user.is_admin:
        raise UserAccessException(
            detail="The logged-in user is not an admin.",
            user_friendly_detail="You don't have permission to perform this action.",
            http_status_code=403,
        )


secret_key_header = APIKeyHeader(name="Secret-Key", auto_error=False)


def validate_secret_key(token: str = Security(secret_key_header)):
    """
    Validates if the request contains the correct secret key in its headers.

    Raises MalformedRequestException if the secret key is missing or invalid.
    """
    if not token or SECRET_KEY != token:
        raise MalformedRequestException(
            detail="Invalid or missing secret key in request headers.",
            user_friendly_detail="You are not authorized to perform this action.",
            http_status_code=403,
        )
