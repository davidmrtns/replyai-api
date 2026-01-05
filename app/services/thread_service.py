from sqlalchemy.orm import Session

from app.db.models import Contact, Thread
from app.utils.decorators import disabled_func


@disabled_func
async def assign_new_thread_to_contact(
    contact: Contact, thread_id: str, db: Session
) -> None:
    thread = Thread(
        thread_id=thread_id, last_message_from="assistant", contact_id=contact.id
    )
    db.add(thread)
    contact.current_thread = thread
    db.commit()
