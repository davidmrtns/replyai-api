from app.schemas.base import StrictBaseModel


class CreateUserSchema(StrictBaseModel):
    name: str
    email: str
    password: str
    password_confirmation: str
    is_active: bool
    is_admin: bool
    company_id: int
