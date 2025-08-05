import openai
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from openai import OpenAI
from openai.types import ResponseFormatJSONObject, ResponseFormatText
from sqlalchemy.orm import Session
from typing import Annotated

from app.db.database import obter_sessao
from app.db.new_models import Assistant, Company
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.integrations_schemas import AssistenteSchema
from app.schemas.empresa_schema import AssistenteSchema as AssistenteSchemaEmpresa
from app.utils.assistant import CustomHTTPClient, Ferramentas


def obter_openai_client(empresa: Company = Depends(verificar_permissao_empresa)):
    return OpenAI(http_client=CustomHTTPClient(), api_key=empresa.openai_api_key)


router = APIRouter()

@router.post("/{slug}")
async def criar_assistente(
        slug: str,
        request: AssistenteSchema,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[OpenAI, Depends(obter_openai_client)],
        db: Session = Depends(obter_sessao)
):
    ferramentas = Ferramentas.get_all_tools()

    assistente = cliente.beta.assistants.create(
        model="gpt-4o",
        instructions=request.instrucoes,
        name=f"{request.nome} - {request.proposito}",
        response_format=ResponseFormatJSONObject(type="json_object") if request.proposito != "reescrever" else ResponseFormatText(type="text"),
        temperature=1.0,
        tools=ferramentas,
        top_p=1.0
    )

    if assistente:
        assistente_bd = Assistant(
            assistantId=assistente.id,
            nome=assistente.name,
            proposito=request.proposito,
            atalho=request.atalho,
            id_voz=request.voz,
            id_empresa=empresa.id
        )

        db.add(assistente_bd)
        db.commit()
        db.refresh(assistente_bd)
        return assistente_bd
    return None

@router.get("/{slug}/{id}")
async def obter_instrucoes_assistente(
        slug: str,
        id: int,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[OpenAI, Depends(obter_openai_client)],
        db: Session = Depends(obter_sessao)
):
    assistente_db = db.query(Assistant).filter_by(id=id, id_empresa=empresa.id).first()
    if assistente_db:
        assistente_openai = cliente.beta.assistants.retrieve(assistant_id=assistente_db.assistantId)
        if assistente_openai:
            return assistente_openai.instructions
    return None

@router.put("/{slug}/{id}", response_model=AssistenteSchemaEmpresa)
async def editar_assistente(
        slug: str,
        id: int,
        request: AssistenteSchema,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[OpenAI, Depends(obter_openai_client)],
        db: Session = Depends(obter_sessao)
):
    assistente_db = db.query(Assistant).filter_by(id=id, id_empresa=empresa.id).first()
    if assistente_db:
        cliente.beta.assistants.update(
            assistant_id=assistente_db.assistantId,
            name=f"{request.nome} - {request.proposito}",
            instructions=request.instrucoes
        )

        assistente_db.nome = request.nome
        assistente_db.proposito = request.proposito
        assistente_db.atalho = request.atalho
        assistente_db.id_voz = request.voz

        db.commit()
        return assistente_db
    return None

@router.delete("/{slug}/{id}")
async def excluir_assistente(
        slug: str,
        id: int,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[OpenAI, Depends(obter_openai_client)],
        db: Session = Depends(obter_sessao)
):
    if empresa.assistentePadrao == id:
        raise HTTPException(status_code=403, detail="Não é possível excluir o assistente padrão da empresa. Troque o assistente padrão e tente novamente")

    assistente_db = db.query(Assistant).filter_by(id=id, id_empresa=empresa.id).first()
    if assistente_db:
        try:
            assistente = cliente.beta.assistants.delete(
                assistant_id=assistente_db.assistantId
            )

            if assistente.id:
                db.delete(assistente_db)
                db.commit()
                return True
        except openai.NotFoundError as e:
            print(f"Erro ao excluir o assistente da OpenAI: {e}")
            db.delete(assistente_db)
            db.commit()
            return True
    return False
