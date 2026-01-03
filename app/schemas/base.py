from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
