from pydantic import BaseModel
from typing import List, Optional, Literal


class AgendaSchema(BaseModel):
    id: int
    endereco: str
    atalho: str


class GoogleCalendarSchema(BaseModel):
    id: Optional[int] = None
    client_email: str
    timezone: str


class OutlookClientSchema(BaseModel):
    id: Optional[int] = None
    default_user: str
    timezone: str


class DepartamentoSchema(BaseModel):
    id: int
    atalho: str
    comentario: str
    departmentId: str
    userId: Optional[str]
    departamento_confirmacao: bool


class DigisacClientSchema(BaseModel):
    id: int
    digisacSlug: str
    digisacToken: str
    digisacDefaultUser: str
    service_id: str
    departamentos: Optional[List[DepartamentoSchema]]

    class Config:
        from_attributes = True


class VozSchema(BaseModel):
    id: int
    nome: str
    voiceId: str
    stability: float
    similarity_boost: float
    style: float

    class Config:
        from_attributes = True


class AssistenteSchema(BaseModel):
    id: int
    assistantId: str
    nome: str
    proposito: Literal[
        "responder", "agendar", "retomar", "confirmar", "reescrever", "cobrar"
    ]
    atalho: str
    voz: Optional[VozSchema]

    class Config:
        from_attributes = True


class MidiaSchema(BaseModel):
    id: int
    url: str
    mediatype: str
    nome: str
    atalho: str
    ordem: int

    class Config:
        from_attributes = True


class UsuarioSchema(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool
    admin: bool
    id_empresa: Optional[int] = None

    class Config:
        from_attributes = True


class ListaUsuariosSchema(BaseModel):
    has_more: bool
    next_cursor: Optional[int] = None
    limit: int
    data: List[UsuarioSchema]
