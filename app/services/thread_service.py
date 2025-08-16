import json

from sqlalchemy.orm import Session

from app.db.new_models import Contact, Thread
from app.utils.assistant import Assistant as AiAssistant, Resposta


async def execute_thread(
        message: str | None,
        image: str | None,
        contact: Contact,
        assistant: AiAssistant,
        db: Session
) -> Resposta:
    current_thread_id = contact.current_thread.thread_id if contact.current_thread else None

    if message:
        assistant.adicionar_mensagens([message], [], current_thread_id)

    '''if contact_data:
        assistente.adicionar_mensagens([contact_data.__str__()], [], contato.threadId or None)''' # TODO: check how to pass the contact data in a better way

    if image:
        image_id = assistant.subir_imagens([image])
        assistant.adicionar_imagens(image_id, current_thread_id)

    response, thread_id = assistant.criar_rodar_thread(thread_id=current_thread_id)

    if not contact.current_thread:
        thread = Thread(
            thread_id=thread_id,
            last_message_from="assistant",
            contact_id=contact.id
        )
        db.add(thread)
        contact.current_thread = thread
        db.commit()

    response = json.loads(response)
    response_obj = Resposta.from_dict(response)
    return response_obj


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
