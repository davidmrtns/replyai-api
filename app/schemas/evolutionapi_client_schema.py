from app.schemas.base import StrictBaseModel, OrmBaseModel


class EvolutionAPIInstanceSchema(OrmBaseModel):
    instance_name: str
    api_key: str


class CreateEvolutionAPIInstanceSchema(StrictBaseModel):
    instance_name: str
    api_key: str


class CreateEvolutionAPIWebhookSchema(StrictBaseModel):
    webhook_url: str
    is_enabled: bool
