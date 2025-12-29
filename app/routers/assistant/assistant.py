import openai
from fastapi import APIRouter
from fastapi.params import Depends
from openai.types import ResponseFormatJSONObject
from sqlalchemy.orm import Session

from app.assistant_functions.assistant_function import get_function_documentations
from app.db.database import get_db_session
from app.db.models import Assistant
from app.exceptions.exceptions import (
    AssistantEditingException,
    IntegrationAuthException,
)
from app.routers.assistant.assistant_helpers import get_openai_client
from app.routers.routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.assistant_schema import (
    AssistantSchema,
    CreateAssistantSchema,
    UpdateAssistantSchema,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db


router = APIRouter()


@router.post("/", response_model=AssistantSchema)
async def create_assistant(
    request: CreateAssistantSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    openai_client = get_openai_client(company_id, db)
    tools = get_function_documentations()

    openai_assistant = openai_client.beta.assistants.create(
        model="gpt-4o",
        instructions=request.instructions,
        name=f"{request.assistant_name}",
        response_format=ResponseFormatJSONObject(type="json_object"),
        temperature=1.0,
        tools=tools,
        top_p=1.0,
    )

    if openai_assistant:
        assistant = Assistant(
            openai_assistant_id=openai_assistant.id,
            assistant_name=openai_assistant.name,
            purpose=request.purpose,
            shortcut=request.shortcut,
            voice_id=request.voice_id,
            company_id=company_id,
        )

        db.add(assistant)
        db.commit()
        db.refresh(assistant)
        return assistant
    raise IntegrationAuthException(
        integration_name="OpenAI Assistant",
        company_slug="",
        detail="An error occurred while creating the assistant.",
        user_friendly_detail="An error occurred while creating the assistant. Try again later.",
        status_code=500,
    )


@router.get("/{assistant_id}")
async def get_instructions_from_assistant(
    assistant_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = get_openai_client(company_id or assistant.company_id, db)

    openai_assistant = openai_client.beta.assistants.retrieve(
        assistant_id=assistant.openai_assistant_id
    )
    if openai_assistant:
        return openai_assistant.instructions


@router.patch("/{assistant_id}", response_model=AssistantSchema)
async def update_assistant(
    assistant_id: int,
    request: UpdateAssistantSchema,
    company_id: int = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = get_openai_client(company_id or assistant.company_id, db)

    openai_update_data = {}
    if request.assistant_name is not None:
        openai_update_data["name"] = request.assistant_name
    if request.instructions is not None:
        openai_update_data["instructions"] = request.instructions

    openai_assistant = openai_client.beta.assistants.update(
        assistant_id=assistant.openai_assistant_id, **openai_update_data
    )

    if openai_assistant:
        apply_model_update(assistant, request)
        db.commit()
    return assistant


@router.delete("/{assistant_id}")
async def delete_assistente(
    assistant_id: int,
    company_id: int = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)
    openai_client = get_openai_client(company_id or assistant.company_id, db)

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
