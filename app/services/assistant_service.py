from openai import OpenAI
import openai
from openai.types import ResponseFormatJSONObject
from sqlalchemy.orm import Session

from app.assistant_functions.assistant_function import get_function_documentations
from app.clients.assistants_client import CustomHTTPClient
from app.db.models import Assistant, Company
from app.exceptions.exceptions import (
    AssistantEditingException,
    IntegrationException,
)
from app.schemas.assistant_schema import CreateAssistantSchema, UpdateAssistantSchema
from app.utils.api_key_encryption import decrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


def _get_openai_client(company_id: int, db: Session):
    company = db.query(Company).filter_by(id=company_id).first()

    # TODO: [IMPORTANT] centralize with AssistantsClient
    return OpenAI(
        http_client=CustomHTTPClient(), api_key=decrypt_api_key(company.openai_api_key)
    )


async def create_assistant(
    company_id: int, payload: CreateAssistantSchema, db: Session
):
    openai_client = _get_openai_client(company_id, db)
    tools = get_function_documentations()

    openai_assistant = openai_client.beta.assistants.create(
        model="gpt-4o",
        instructions=payload.instructions,
        name=f"{payload.assistant_name}",
        response_format=ResponseFormatJSONObject(type="json_object"),
        temperature=1.0,
        tools=tools,
        top_p=1.0,
    )

    if openai_assistant:
        assistant = Assistant(
            openai_assistant_id=openai_assistant.id,
            assistant_name=openai_assistant.name,
            purpose=payload.purpose,
            shortcut=payload.shortcut,
            voice_id=payload.voice_id,
            company_id=company_id,
        )

        db.add(assistant)
        db.commit()
        db.refresh(assistant)
        return assistant
    raise IntegrationException(
        integration_name="OpenAI Assistant",
        company_slug="",
        detail="An error occurred while creating the assistant.",
        user_friendly_detail="An error occurred while creating the assistant. Try again later.",
        status_code=500,
    )


async def get_instructions_from_assistant(
    assistant_id: int, company_id: int | None, db: Session
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = _get_openai_client(company_id or assistant.company_id, db)

    openai_assistant = openai_client.beta.assistants.retrieve(
        assistant_id=assistant.openai_assistant_id
    )
    if openai_assistant:
        return openai_assistant.instructions


async def update_assistant(
    assistant_id: int, payload: UpdateAssistantSchema, company_id: int, db: Session
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = _get_openai_client(company_id or assistant.company_id, db)

    openai_update_data = {}
    if payload.assistant_name is not None:
        openai_update_data["name"] = payload.assistant_name
    if payload.instructions is not None:
        openai_update_data["instructions"] = payload.instructions

    openai_assistant = openai_client.beta.assistants.update(
        assistant_id=assistant.openai_assistant_id, **openai_update_data
    )

    if openai_assistant:
        apply_model_update(assistant, payload)
        db.commit()
    return assistant


async def delete_assistant(assistant_id: int, company_id: int | None, db: Session):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = _get_openai_client(company_id or assistant.company_id, db)

    if assistant.company.default_assistant_id == assistant_id:
        raise AssistantEditingException(
            assistant_id=assistant_id,
            detail="User tried to delete the default assistant of the company.",
            user_friendly_detail="You cannot delete the default assistant of the company. Please change the default assistant and try again.",
            http_status_code=403,
        )

    try:
        openai_assistant = openai_client.beta.assistants.delete(
            assistant_id=assistant.openai_assistant_id
        )

        if openai_assistant.id:
            db.delete(assistant)
            db.commit()
            return True
    except openai.NotFoundError as e:
        db.delete(assistant)
        db.commit()
        raise AssistantEditingException(
            assistant_id=assistant_id,
            detail="Assistant not found in OpenAI, but was removed from the database.",
            user_friendly_detail="The assistant was not found in OpenAI, but it has been removed from the your company.",
            http_status_code=410,
        )
    return False
