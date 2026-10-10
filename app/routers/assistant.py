from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session
import os

from app.clients.new_assistant_client import NewAssistantClient
from app.clients.langchain_model_factory import build_chat_model
from app.db.database import get_db_session
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.assistant_schema import (
    AssistantSchema,
    CreateAssistantSchema,
    UpdateAssistantSchema,
)
from app.services.assistant_service import (
    create_assistant as create_assistant_service,
    get_assistant as get_assistant_service,
    update_assistant as update_assistant_service,
    delete_assistant as delete_assistant_service,
)

router = APIRouter()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model = build_chat_model(
    provider="google_genai",
    model_name="gemini-3.8-flash",
    api_key=GEMINI_API_KEY,
)
assistant: NewAssistantClient | None = None


def initialize_assistant() -> None:
    global assistant
    assistant = NewAssistantClient(
        assistant_id="1", model=model, instructions="You are a helpful assistant."
    )


def close_assistant() -> None:
    if assistant is not None:
        assistant.close()


@router.post("/", response_model=AssistantSchema)
def create_assistant(
    request: CreateAssistantSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return create_assistant_service(company_id, request, db)


@router.get("/{assistant_id}", response_model=AssistantSchema)
def get_assistant(
    assistant_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return get_assistant_service(assistant_id, company_id, db)


@router.patch("/{assistant_id}", response_model=AssistantSchema)
def update_assistant(
    assistant_id: int,
    request: UpdateAssistantSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return update_assistant_service(assistant_id, request, company_id, db)


@router.delete("/{assistant_id}")
def delete_assistant(
    assistant_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return delete_assistant_service(assistant_id, company_id, db)


@router.post("/v2/test")
def test_assistant(request: dict):
    current_assistant = _get_assistant()
    message = current_assistant.add_message(
        content=request["message"], content_type="text"
    )
    response, thread_id = current_assistant.process_conversation(
        message, request.get("thread_id")
    )
    return {"message": response, "thread_id": thread_id}


@router.get("/v2/thread/{thread_id}")
def get_thread_messages(thread_id: str):
    return {
        "thread_id": thread_id,
        "messages": _get_assistant().get_messages(thread_id),
    }


def _get_assistant() -> NewAssistantClient:
    if assistant is None:
        raise RuntimeError("The assistant has not been initialized")
    return assistant
