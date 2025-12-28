from pydantic import BaseModel, field_validator
from typing import Optional


class InformacoesUsuario(BaseModel):
    id: Optional[int] = None
    nome: str
    email: str
    senha: Optional[str] = None
    confirmacao_senha: Optional[str] = None
    usuario_ativo: bool
    admin: bool
    id_empresa: Optional[int] = None

    @field_validator("id", "id_empresa", mode="before")
    @classmethod
    def int_vazio(cls, valor):
        if isinstance(valor, str) and valor.strip() == "":
            return None
        return valor

    @field_validator("senha", "confirmacao_senha", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor if valor.strip() else None
