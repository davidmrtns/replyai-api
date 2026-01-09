import base64
from io import BytesIO
import mimetypes
import os
import threading
from typing import Literal

import requests
from requests import Response

from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.utils.api_key_encryption import decrypt_api_key
from app.utils.decorators import ensure_success_status
from .message_client import (
    ContactData,
    FileData,
    MediaMessageData,
    MessageClient,
    MessageContent,
)


BASE_URL = os.getenv("EVOLUTIONAPI_SERVER_URL")
GLOBAL_API_KEY = os.getenv("EVOLUTIONAPI_GLOBAL_KEY")


class EvolutionAPIClient(MessageClient):
    def __init__(
        self,
        message_client_id: int,
        api_key: str,
        instance_name: str,
        delay_amount: int,
    ):
        super().__init__(message_client_id)

        decrypted_api_key = decrypt_api_key(api_key)

        self.headers = {"apikey": decrypted_api_key, "Content-Type": "application/json"}
        self.instance_name = instance_name
        self.delay_amount = delay_amount

    def send_message(
        self,
        phone_number: str,
        message_type: Literal["text", "audio", "media"],
        text_message: str | None,
        audio_message_base64: str | None,
        media_message: MediaMessageData | None,
        assistant_name: str,
    ) -> Response:
        endpoint = (
            f"{BASE_URL}/message/sendText/{self.instance_name}"
            if message_type == "text"
            else (
                f"{BASE_URL}/message/sendWhatsAppAudio/{self.instance_name}"
                if message_type == "audio"
                else (
                    f"{BASE_URL}/message/sendMedia/{self.instance_name}"
                    if message_type == "media"
                    else None
                )
            )
        )

        if endpoint is None:
            raise ValueError("Invalid message type")  # TODO: raise custom exception

        payload = {"number": phone_number}

        if message_type == "text":
            payload["text"] = f"*{assistant_name}:*\n{text_message}"
        elif message_type == "audio":
            payload["audio"] = audio_message_base64
        elif message_type == "media":
            if media_message is None:
                raise ValueError(
                    'media_message cannot be None when message_type is "media"'
                )  # TODO: raise custom exception

            payload["mediatype"] = media_message.mediatype
            payload["mimetype"] = media_message.mimetype
            payload["caption"] = media_message.caption
            payload["media"] = media_message.media
            payload["fileName"] = media_message.filename
        else:
            raise ValueError("Invalid message type")  # TODO: raise custom exception

        response = requests.post(endpoint, headers=self.headers, json=payload)
        return response

    def send_presence(
        self, phone_number: str, presence_type: Literal["composing", "recording"]
    ) -> None:
        endpoint = f"{BASE_URL}/chat/sendPresence/{self.instance_name}"
        payload = {
            "number": phone_number,
            "options": {
                "delay": self.delay_amount,
                "presence": presence_type,
                "number": phone_number,
            },
        }

        function = lambda url, json, headers: requests.post(
            url, json=json, headers=headers
        )
        threading.Thread(
            target=function, args=(endpoint, payload, self.headers), daemon=True
        ).start()

    def get_contact_data(self, request: EvolutionAPIRequest) -> ContactData:
        contact_name = request.data.pushName
        phone_number = request.data.key.remoteJid.split("@")[0]
        return ContactData(contact_name=contact_name, phone_number=phone_number)

    def get_contact_id(self, phone_number: str) -> str:
        return f"{phone_number}@s.whatsapp.net"

    def get_file_data(self, request: EvolutionAPIRequest) -> FileData | None:
        file_bytes = base64.b64decode(request.data.message.base64)
        file_stream = BytesIO(file_bytes)

        mimetype = (
            request.data.message.audioMessage.mimetype
            if request.data.messageType == "audioMessage"
            else (
                request.data.message.imageMessage.mimetype
                if request.data.messageType == "imageMessage"
                else (
                    request.data.message.documentMessage.mimetype
                    if request.data.messageType == "documentMessage"
                    else None
                )
            )
        )
        if mimetype is None:
            return None

        file_extension = mimetypes.guess_extension(mimetype.split(";")[0].strip())
        filename = f"downloaded_file{file_extension}"

        return filename, mimetype, file_stream

    def get_message_content(self, request: EvolutionAPIRequest) -> MessageContent:
        text_message, is_audio, image = None, False, None

        match request.data.messageType:
            case "conversation":
                text_message = request.data.message.conversation
            case "extendedTextMessage":
                text_message = request.data.message.extendedTextMessage.text
            case "imageMessage":
                text_message = request.data.message.imageMessage.caption or ""
                image = request.data.message.base64
            case "audioMessage":
                is_audio = True

        return MessageContent(text_message=text_message, is_audio=is_audio, image=image)

    @staticmethod
    @ensure_success_status("EvolutionAPI")
    def create_instance(instance_name: str) -> Response:
        endpoint = f"{BASE_URL}/instance/create"
        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "groupsIgnore": True,
        }

        custom_headers = {
            "apikey": GLOBAL_API_KEY,
            "Content-Type": "application/json",
        }

        response = requests.post(endpoint, headers=custom_headers, json=payload)
        return response

    @ensure_success_status("EvolutionAPI")
    def fetch_instance(self) -> Response:
        endpoint = f"{BASE_URL}/instance/fetchInstances"
        response = requests.get(
            endpoint, headers=self.headers, params={"instanceName": self.instance_name}
        )
        return response

    @ensure_success_status("EvolutionAPI")
    def connect_instance(self) -> Response:
        endpoint = f"{BASE_URL}/instance/connect/{self.instance_name}"
        response = requests.get(endpoint, headers=self.headers)
        return response

    @ensure_success_status("EvolutionAPI")
    def check_instance_connection_state(self) -> Response:
        endpoint = f"{BASE_URL}/instance/connectionState/{self.instance_name}"
        response = requests.get(endpoint, headers=self.headers)
        return response

    @ensure_success_status("EvolutionAPI")
    def restart_instance(self) -> Response:
        endpoint = f"{BASE_URL}/instance/restart/{self.instance_name}"
        response = requests.put(endpoint, headers=self.headers)
        return response

    @ensure_success_status("EvolutionAPI")
    def logout_instance(self) -> Response:
        endpoint = f"{BASE_URL}/instance/logout/{self.instance_name}"
        response = requests.delete(endpoint, headers=self.headers)
        return response

    @staticmethod
    @ensure_success_status("EvolutionAPI")
    def check_evolutionapi_connection() -> Response:
        endpoint = f"{BASE_URL}/"
        response = requests.get(endpoint)
        return response

    @ensure_success_status("EvolutionAPI")
    def add_webhook(self, webhook_url: str, is_enabled: bool) -> Response:
        endpoint = f"{BASE_URL}/webhook/set/{self.instance_name}"

        payload = {
            "webhook": {
                "enabled": is_enabled,
                "url": webhook_url,
                "byEvents": False,
                "base64": True,
                "events": ["MESSAGES_UPSERT"],
            }
        }

        response = requests.post(endpoint, headers=self.headers, json=payload)
        return response

    @ensure_success_status("EvolutionAPI")
    def list_webhooks(self) -> Response:
        endpoint = f"{BASE_URL}/webhook/find/{self.instance_name}"
        response = requests.get(endpoint, headers=self.headers)
        return response
