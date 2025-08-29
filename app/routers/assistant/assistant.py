import openai
from fastapi import APIRouter
from fastapi.params import Depends
from openai import OpenAI
from openai.types import ResponseFormatJSONObject
from sqlalchemy.orm import Session
from typing import Annotated

from app.assistant_functions.assistant_function import get_function_documentations
from app.db.database import obter_sessao
from app.db.new_models import Assistant, Company
from app.exceptions.exceptions import AssistantEditingException
from app.routers.assistant.assistant_helpers import get_openai_client
from app.routers.routers_helpers import check_company_access
from app.schemas.integrations_schemas import AssistenteSchema
from app.schemas.empresa_schema import AssistenteSchema as AssistenteSchemaEmpresa


router = APIRouter()


@router.post("/{company_slug}")
async def create_assistant(
        company_slug: str,
        request: AssistenteSchema,
        company: Annotated[Company, Depends(check_company_access)],
        openai_client: Annotated[OpenAI, Depends(get_openai_client)],
        db: Session = Depends(obter_sessao)
):
    tools = get_function_documentations()

    assistant = openai_client.beta.assistants.create(
        model="gpt-4o",
        instructions=request.instrucoes,
        name=f"{request.nome} - {request.proposito}",
        response_format=ResponseFormatJSONObject(type="json_object"),
        temperature=1.0,
        tools=tools,
        top_p=1.0
    )

    if assistant:
        assistant_db = Assistant(
            openai_assistant_id=assistant.id,
            assistant_name=assistant.name,
            purpose=request.proposito,
            shortcut=request.atalho,
            voice_id=request.voz,
            company_id=company.id
        )

        db.add(assistant_db)
        db.commit()
        db.refresh(assistant_db)
        return assistant_db
    return None


@router.get("/{company_slug}/{assistant_id}")
async def get_instructions_from_assistant(
        company_slug: str,
        assistant_id: int,
        company: Annotated[Company, Depends(check_company_access)],
        openai_client: Annotated[OpenAI, Depends(get_openai_client)],
        db: Session = Depends(obter_sessao)
):
    assistant_db = db.query(Assistant).filter_by(openai_assistant_id=assistant_id, company_id=company.id).first()
    if assistant_db:
        assistant = openai_client.beta.assistants.retrieve(assistant_id=assistant_db.assistantId)
        if assistant:
            return assistant.instructions
    return None


@router.put("/{company_slug}/{assistant_id}", response_model=AssistenteSchemaEmpresa)
async def edit_assistant(
        company_slug: str,
        assistant_id: int,
        request: AssistenteSchema,
        company: Annotated[Company, Depends(check_company_access)],
        openai_client: Annotated[OpenAI, Depends(get_openai_client)],
        db: Session = Depends(obter_sessao)
):
    assistant_db = db.query(Assistant).filter_by(openai_assistant_id=assistant_id, company_id=company.id).first()
    if assistant_db:
        openai_client.beta.assistants.update(
            assistant_id=assistant_db.openai_assistant_id,
            name=f"{request.nome} - {request.proposito}",
            instructions=request.instrucoes
        )

        assistant_db.assistant_name = request.nome
        assistant_db.purpose = request.proposito
        assistant_db.shortcut = request.atalho
        assistant_db.voice_id = request.voz

        db.commit()
        return assistant_db
    return None


@router.delete("/{company_slug}/{assistant_id}")
async def delete_assistente(
        company_slug: str,
        assistant_id: int,
        company: Annotated[Company, Depends(check_company_access)],
        openai_client: Annotated[OpenAI, Depends(get_openai_client)],
        db: Session = Depends(obter_sessao)
):
    if company.default_assistant_id == assistant_id:
        raise AssistantEditingException(
            assistant_id=assistant_id,
            detail="User tried to delete the default assistant of the company.",
            user_friendly_detail="You cannot delete the default assistant of the company. Please change the default assistant and try again.",
            http_status_code=403
        )

    assistant_db = db.query(Assistant).filter_by(openai_assistant_id=assistant_id, company_id=company.id).first()
    if assistant_db:
        try:
            assistant = openai_client.beta.assistants.delete(
                assistant_id=assistant_db.assistantId
            )

            if assistant.id:
                db.delete(assistant_db)
                db.commit()
                return True
        except openai.NotFoundError as e:
            db.delete(assistant_db)
            db.commit()
            raise AssistantEditingException(
                assistant_id=assistant_id,
                detail="Assistant not found in OpenAI, but was removed from the database.",
                user_friendly_detail="The assistant was not found in OpenAI, but it has been removed from the database.",
                http_status_code=410
            )
    return False
