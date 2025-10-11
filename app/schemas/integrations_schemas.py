from typing import Optional, Literal

from fastapi import Form
from pydantic import BaseModel, field_validator


class AssistenteSchema(BaseModel):
    id: Optional[int] = None
    id_openai: Optional[str] = None
    nome: str
    instrucoes: str
    proposito: Literal["responder", "agendar", "retomar", "confirmar", "reescrever", "cobrar"]
    atalho: str
    voz: int


class VozSchema(BaseModel):
    nome: str
    descricao: Optional[str] = None
    stability: float
    similarity_boost: float
    style: float

async def parse_form_data_voz(
        nome: str = Form(...),
        descricao: Optional[str] = Form(None),
        stability: float = Form(...),
        similarity_boost: float = Form(...),
        style: float = Form(...)
) -> VozSchema:
    return VozSchema(
        nome=nome,
        descricao=descricao,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style
    )


class EvolutionInstanceSchema(BaseModel):
    nome_instancia: str

class EvolutionAPIWebhookSchema(BaseModel):
    webhook_url: str
    is_enabled: bool


class DigisacClientSchema(BaseModel):
    slug: str
    token: str
    user_id: Optional[str] = None
    service_id: Optional[str] = None

class DigisacDepartmentSchema(BaseModel):
    atalho: str
    comentario: str
    department_id: str
    user_id: Optional[str] = None
    departamento_confirmacao: bool

    @field_validator("user_id", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor or None
