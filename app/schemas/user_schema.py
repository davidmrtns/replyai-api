from typing import List, Optional

from pydantic import model_validator
from app.schemas.base import StrictBaseModel, OrmBaseModel


class UserSchema(OrmBaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    is_admin: bool
    company_id: Optional[int] = None


class UserListSchema(OrmBaseModel):
    has_more: bool
    next_cursor: Optional[int] = None
    limit: int
    data: List[UserSchema]


class CreateUserSchema(StrictBaseModel):
    name: str
    email: str
    password: str
    password_confirmation: str
    is_active: bool
    is_admin: bool
    company_id: Optional[int] = None

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("Password and password confirmation do not match.")
        return self


class UpdateUserSchema(StrictBaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    new_password: Optional[str] = None
    new_password_confirmation: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.new_password_confirmation:
            raise ValueError("Password and password confirmation do not match.")
        return self
