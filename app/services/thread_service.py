from typing import List
from sqlalchemy.orm import Session

from app.clients.langchain_model_factory import build_chat_model
from app.clients.assistant_client import AssistantClient
from app.db.models import Assistant, Company, Contact, Thread
from app.services.message_handler_service import MessageToProcess
from app.utils.logger import logger


class ThreadService:
    """Encapsulates thread and assistant related operations."""

    def __init__(self, contact: Contact, company: Company, db: Session):
        self.contact = contact
        self.company = company
        self.db = db

    def get_assistants_client(self) -> AssistantClient:
        """Retrieve the assistant for the contact."""
        assistant = (
            self.db.query(Assistant)
            .filter_by(id=self.contact.current_assistant, company_id=self.company.id)
            .first()
            if self.contact.current_assistant
            else self.company.default_assistant
        )
        if not self.contact.current_assistant:
            self.contact.current_assistant = assistant.id
            self.db.commit()

        model = build_chat_model(
            provider=self.company.ai_provider.provider_name,
            model_name=assistant.model_name,
            api_key=self.company.ai_provider.api_key,
        )
        return AssistantClient(
            assistant_name=assistant.assistant_name,
            assistant_id=assistant.id,
            model=model,
            instructions=assistant.instructions,
        )

    async def execute_thread(self, messages: List[MessageToProcess] | str) -> str:
        """Runs or creates a thread for the assistant."""
        current_thread_id = (
            self.contact.current_thread.thread_id
            if self.contact.current_thread
            else None
        )

        assistant = self.get_assistants_client()

        if isinstance(messages, list):
            logger.info(f"Messages: {[message.content for message in messages]}")
        else:
            logger.info(f"Message: {messages}")

        if isinstance(messages, str):
            assistant.add_message(content=messages, content_type="text")
        else:
            for message in messages:
                if message.type == "text":
                    assistant.add_message(content=message.content, content_type="text")
                elif message.type == "image":
                    pass  # TODO: Implement image handling logic
                    # image_id = assistant.upload_image(message.content)
                    # assistant.add_message(image_id=image_id)

        response, thread_id = assistant.process_conversation(
            thread_id=current_thread_id
        )

        if not self.contact.current_thread:
            self._assign_thread_to_contact(thread_id)

        return response[0]["text"]

    def _assign_thread_to_contact(self, thread_id: str):
        """Assign a new thread to the contact."""
        thread = Thread(
            thread_id=thread_id,
            last_message_from="assistant",
            contact_id=self.contact.id,
        )
        self.db.add(thread)
        self.contact.current_thread = thread
        self.db.commit()
