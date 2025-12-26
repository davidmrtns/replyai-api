from fastapi import Form
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Literal


class InformacoesCriarEmpresa(BaseModel):
    nome: str
    slug: str
    fuso_horario: str
    openai_api_key: str
    elevenlabs_api_key: Optional[str] = None
    empresa_ativa: bool


class InformacoesBasicas(BaseModel):
    nome: str
    fuso_horario: str
    openai_api_key: str
    elevenlabs_api_key: Optional[str] = None
    empresa_ativa: bool


class InformacoesColaborador(BaseModel):
    id: Optional[int] = None
    nome: str
    apelido: Optional[str] = None
    departamento: Optional[str] = None

    @field_validator("apelido", "departamento", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor or None

    @field_validator("id", mode="before")
    @classmethod
    def int_vazio(cls, valor):
        if isinstance(valor, str) and valor.strip() == "":
            return None
        return valor


class InformacoesAgendaUnica(BaseModel):
    endereco: str
    atalho: str


class InformacoesMidia(BaseModel):
    atalho: str
    ordem: int


async def parse_form_data_midia(
    atalho: str = Form(...), ordem: int = Form(...)
) -> InformacoesMidia:
    return InformacoesMidia(atalho=atalho, ordem=ordem)


class InformacoesAssistentes(BaseModel):
    assistente_padrao: Optional[int] = None

    @field_validator("assistente_padrao", mode="before")
    @classmethod
    def int_vazio(cls, valor):
        if isinstance(valor, str) and valor.strip() == "":
            return None
        return valor


class InformacoesMensagens(BaseModel):
    tipo_cliente: Literal["digisac", "evolution"]
    tempo_recall_min: int
    tempo_recall_final_min: int
    quant_recalls: int
    ativar_recall: bool
    ativar_recall_confirmacao: bool
    mensagem_erro_ia: Optional[str] = None

    @field_validator("mensagem_erro_ia", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor or None


class InformacoesAgenda(BaseModel):
    tipo_cliente: Optional[Literal["outlook", "google_calendar"]]
    tipo_cancelamento_evento: str
    ativar_confirmacao: bool
    duracao_evento: int
    hora_inicio_agenda: str
    hora_final_agenda: str

    @field_validator("tipo_cliente", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor if valor.strip() else None


class TimezoneRequest(BaseModel):
    timezone: str


class InformacoesCRM(BaseModel):
    tipo_cliente: Optional[Literal["rdstation"]]

    @field_validator("tipo_cliente", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor if valor.strip() else None


class InformacoesRDStationCRMClient(BaseModel):
    token: str
    id_fonte_padrao: str


class InformacoesRDStationDealStage(BaseModel):
    id: Optional[int] = None
    atalho: str
    deal_stage_id: str
    user_id: Optional[str] = None
    estagio_inicial: bool

    @field_validator("user_id", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor if valor.strip() else None


class InformacoesFinanceiras(BaseModel):
    tipo_cliente: Optional[Literal["asaas"]]
    lembrar_vencimentos: bool
    enviar_boletos_vencimentos: bool
    cobrar_inadimplentes: bool

    @field_validator("tipo_cliente", mode="before")
    @classmethod
    def string_vazia(cls, valor):
        return valor if valor.strip() else None


class InformacoesAsaas(BaseModel):
    token: str
    rotulo: str
    numero_cliente: int


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


class InformacoesExemploPrompt(BaseModel):
    tipo_assistente: Optional[
        Literal["responder", "agendar", "retomar", "confirmar", "reescrever", "cobrar"]
    ] = None
    prompt: str
