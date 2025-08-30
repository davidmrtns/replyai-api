import json

from sqlalchemy.orm import Session

from app.db.new_models import Contact, Thread
from app.clients.assistants_client import AssistantsClient, AssistantReply


async def execute_thread(
        message: str | None,
        image: str | None,
        contact: Contact,
        assistant: AssistantsClient,
        db: Session
) -> AssistantReply:
    current_thread_id = contact.current_thread.thread_id if contact.current_thread else None

    if message:
        assistant.add_message(message=message, thread_id=current_thread_id)

    '''if contact_data:
        assistente.adicionar_mensagens([contact_data.__str__()], [], contato.threadId or None)''' # TODO: check how to pass the contact data in a better way

    if image:
        image_id = assistant.upload_image(image)
        assistant.add_message(is_image=True, image_id=image_id, thread_id=current_thread_id)

    result = assistant.create_or_run_thread(thread_id=current_thread_id)

    if not contact.current_thread:
        await assign_new_thread_to_contact(contact, result.thread_id, db)

    response = AssistantReply.from_run_result(result)
    return response


async def assign_new_thread_to_contact(
        contact: Contact,
        thread_id: str,
        db: Session
) -> None:
    thread = Thread(
        thread_id=thread_id,
        last_message_from="assistant",
        contact_id=contact.id
    )
    db.add(thread)
    contact.current_thread = thread
    db.commit()
