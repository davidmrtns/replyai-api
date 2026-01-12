from openai.types.responses import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MediaMessageData
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company, Media
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_message_client import create_message_client
from app.utils.download_file import download_file
from app.utils.model_utils import get_resource_from_db


# TODO: correctly implement function
def send_media_to_contact_doc():
    return FunctionToolParam(
        name="add_event_to_agenda",
        description="Adds an event to a given agenda on a given date",
        strict=False,
        parameters={
            "type": "object",
            "properties": {
                "agenda_code": {
                    "type": "string",
                    "description": "The agenda code, as chosen by the user",
                },
                "date": {
                    "type": "string",
                    "description": "The date chosen by the user, in the format DD-MM-YYYYTHH:MM:SS",
                },
                "title": {
                    "type": "string",
                    "description": "The title of the event",
                },
                "description": {
                    "type": "string",
                    "description": "The description of the event, if applicable",
                },
                "localization": {
                    "type": "string",
                    "description": "The localization of the event, if applicable",
                },
            },
            "additionalProperties": False,
            "required": [
                "agenda_code",
                "date",
                "title",
                "description",
                "localization",
            ],
        },
        type="function",
    )


@register_function(send_media_to_contact_doc())
async def send_media_to_contact(
    assistant_id: str,
    thread_id: str,
    agenda_code: str,
    date: str,
    title: str,
    description: str,
    localization: str,
) -> bool:
    status = False

    with get_db_session_with_context() as db:
        assistant = await get_resource_from_db(Assistant, assistant_id, db)
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=send_media_to_contact.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=send_media_to_contact.__name__,
            )

        medias = (
            db.query(Media)
            .filter_by(shortcut=agenda_code, company_id=company.id)
            .order_by(Media.order)
            .all()
        )
        if not medias or len(medias) == 0:
            raise FailedFunctionRunException(
                detail="Media(s) not found in the database",
                function_name=send_media_to_contact.__name__,
            )

        message_client = create_message_client(company, db)
        if not message_client or not isinstance(message_client, DigisacClient):
            raise FailedFunctionRunException(
                detail="Message client not found or not supported for transfer",
                function_name=send_media_to_contact.__name__,
            )

        for media in medias:
            content = download_file(media.url)
            if content:
                media_message_data = MediaMessageData(
                    mediatype=media.mediatype,
                    mimetype=media.mediatype,
                    caption=media.media_name,
                    media=content,
                    filename=media.media_name,
                )

                """await _handle_message_sending_through_client(
                    message_client,
                    None,
                    "media",
                    None,
                    media_message_data,
                    contact,
                    assistant,
                )"""

    return status
