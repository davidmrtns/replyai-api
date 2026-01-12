from sqlalchemy.orm import Session

from app.clients.assistants_client import AssistantsClient
from app.db.models import Assistant, Company, Contact, Thread


class ThreadService:
    """Encapsulates thread and assistant related operations."""

    def __init__(self, contact: Contact, company: Company, db: Session):
        self.contact = contact
        self.company = company
        self.db = db

    def get_assistants_client(self) -> AssistantsClient:
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

        return AssistantsClient(
            assistant_name=assistant.assistant_name,
            instructions=assistant.instructions,
            assistant_id=assistant.id,
            openai_api_key=self.company.openai_api_key,
        )

    def execute_thread(self, message: str, image: str | None) -> str:
        """Runs or creates a thread for the assistant."""
        current_thread_id = (
            self.contact.current_thread.thread_id
            if self.contact.current_thread
            else None
        )

        assistant = self.get_assistants_client()
        if message:
            assistant.add_message(message=message)
        if image:
            image_id = assistant.upload_image(image)
            assistant.add_message(message=None, is_image=True, image_id=image_id)

        result = assistant.process_conversation(conversation_id=current_thread_id)

        if not self.contact.current_thread:
            self._assign_thread_to_contact(result.conversation_id)

        return result.text_response

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
