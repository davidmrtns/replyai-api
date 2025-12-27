from io import BytesIO
import json
import mimetypes
import os
from time import sleep
from typing import List, Tuple
import requests
from requests import Response
from app.clients.message_client import (
    ContactData,
    FileData,
    MediaMessageData,
    MessageClient,
)
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.utils.api_key_encryption import decrypt_api_key


class DigisacClient(MessageClient):
    def __init__(
        self,
        digisac_slug: str,
        service_id: str,
        default_user_id: str,
        digisac_token: str,
    ):
        decrypted_api_key = decrypt_api_key(digisac_token)

        self.headers = {
            "Authorization": f"Bearer {decrypted_api_key}",
            "Content-Type": "application/json",
        }
        self.digisac_slug = digisac_slug
        self.base_url = f"https://{digisac_slug}.digisac.me/api/v1"
        self.service_id = service_id
        self.default_user_id = default_user_id

    def send_message(
        self,
        contact_id: str,
        user_id: str | None,
        text_message: str | None,
        audio_message_base64: str | None,
        media_message: MediaMessageData | None,
        assistant_name: str,
    ):
        endpoint = f"{self.base_url}/messages"

        payload = {
            "text": f"*{assistant_name}:*\n{text_message}",
            "type": "chat",
            "contactId": contact_id,
            "userId": user_id or self.default_user_id,
            "origin": "bot",
        }

        if audio_message_base64 or media_message:
            file = {
                "base64": audio_message_base64 or media_message.media,
                "mimetype": (
                    "audio/mpeg" if audio_message_base64 else media_message.mimetype
                ),
                "name": (
                    "audio_response" if audio_message_base64 else media_message.filename
                ),
            }
            payload["file"] = file
            payload["text"] = ""

        response = requests.post(endpoint, headers=self.headers, json=payload)
        return response

    def get_contact_data(self, request: DigisacRequest) -> ContactData:
        contact_name = ""
        phone_number = ""

        endpoint = f"{self.base_url}/contacts/{request.data.contactId}"
        response = requests.get(endpoint, headers=self.headers)

        if response.status_code == 200:
            json_response = json.loads(response.content)
            contact_name = (
                json_response.get("name", ""),
            )  # TODO: maybe improve typing
            phone_number = json_response.get("data", {}).get("number", "")

        return ContactData(contact_name=contact_name, phone_number=phone_number)

    def get_contact_id(self, phone_number: str, contact_name: str) -> str:
        contact_id = None

        endpoint = f"{self.base_url}/contacts"
        response = requests.get(
            endpoint,
            headers=self.headers,
            params={
                "where[data.number]": phone_number,
                "where[serviceId]": self.service_id,
            },
        )

        if response.status_code == 200:
            response_json = json.loads(response.content)
            if response_json.get("total", 0) > 0:
                data = response_json.get("data")
                if len(data) > 0:
                    contact_id = data[0].get("id", None)

        if contact_id is None:
            payload = {
                "serviceId": self.service_id,
                "internalName": contact_name,
                "alternativeName": contact_name,
                "number": phone_number,
            }
            response_create_contact = requests.post(
                endpoint, headers=self.headers, json=payload
            )

            if response_create_contact.status_code == 200:
                response_create_contact_json = json.loads(
                    response_create_contact.content
                )
                contact_id = response_create_contact_json.get("id", None)

        return contact_id

    def get_file_url(self, message_id: str) -> str | None:
        MAX_ATTEMPTS = 5
        attempt = 0

        url = None
        endpoint = f"{self.base_url}/messages/{message_id}?include=file"

        while not url and attempt < MAX_ATTEMPTS:
            try:
                response = requests.get(endpoint, headers=self.headers)

                if response.status_code == 200:
                    if not response.json().get("file", {}).get("url", ""):
                        sleep(10)
                        attempt += 1
                    else:
                        url = response.json().get("file", {}).get("url", "")
                else:
                    attempt += 1
            except:
                sleep(10)
                attempt += 1

        return url

    def get_file_data(self, request: DigisacRequest) -> FileData | None:
        url = self.get_file_url(request.data.message.id)
        if url:
            file_response = requests.get(url)

            if file_response.status_code == 200:
                filename = (
                    file_response.headers.get("Content-Disposition", "")
                    .split("filename=")[-1]
                    .strip('"')
                )
                if filename:
                    extension = os.path.splitext(filename)[1]
                else:
                    mimetype = file_response.headers.get(
                        "Content-Type", "application/octet-stream"
                    )
                    extension = mimetypes.guess_extension(mimetype) or ""

                mimetype = mimetypes.types_map.get(
                    extension, "application/octet-stream"
                )

                file_stream = BytesIO(file_response.content)
                filename = f"downloaded_file{extension}"

                return filename, mimetype, file_stream

        return None

    def get_ticket_and_last_message_ids(
        self, contact_id: str
    ) -> Tuple[str | None, str | None]:
        current_ticket_id = None
        last_message_id = None

        endpoint = f"{self.base_url}/contacts/{contact_id}"
        response = requests.get(endpoint, headers=self.headers)

        if response.status_code == 200:
            response_json = json.loads(response.content)
            current_ticket_id: str | None = response_json.get("currentTicketId", None)
            last_message_id: str | None = response_json.get("lastMessageId", None)

        return current_ticket_id, last_message_id

    def get_message_origin(self, message_id: str) -> str | None:
        origin = None

        endpoint = f"{self.base_url}/messages/{message_id}"
        response = requests.get(endpoint, headers=self.headers)

        if response.status_code == 200:
            response_json = json.loads(response.content)
            origin: str | None = response_json.get("origin", None)

        return origin

    def transfer_contact(
        self,
        contact_id: str,
        department_id: str,
        user_id: str | None,
        by_user_id: str | None,
        comments: str | None,
    ) -> Response:
        endpoint = f"{self.base_url}/contacts/{contact_id}/ticket/transfer"

        payload = {
            "departmentId": department_id,
            "byUserId": by_user_id or self.default_user_id,
            "comments": comments or "",
        }

        if user_id is not None:
            payload["userId"] = user_id

        response = requests.post(endpoint, headers=self.headers, json=payload)
        return response

    def add_tag_to_contact(self, contact_id: str, tag_ids: List[str]) -> Response:
        endpoint = f"{self.base_url}/contacts/{contact_id}"

        request = {"tagIds": tag_ids}

        response = requests.put(endpoint, headers=self.headers, json=request)
        return response

    def close_contact_ticket(
        self,
        contact_id: str,
        ticket_topic_ids: List[str],
        comments: str | None,
        by_user_id: str | None,
    ) -> Response:
        endpoint = f"{self.base_url}/contacts/{contact_id}/ticket/close"

        request = {
            "ticketTopicIds": ticket_topic_ids,
            "comments": comments or "",
            "byUserId": by_user_id or self.default_user_id,
        }

        response = requests.post(endpoint, headers=self.headers, json=request)
        return response

    def list_users(
        self, page: int, user_name: str | None = None, user_id: str | None = None
    ) -> Response:
        endpoint = f"{self.base_url}/users"

        query_params = {
            "where": {"archivedAt": {"$eq": None}},
            "order": [["name", "asc"]],
        }

        if user_id:
            query_params["where"]["id"] = {"$eq": user_id}
        elif user_name:
            query_params["where"]["name"] = {"$iLike": f"%{user_name}%"}

        params = {"page": page, "query": json.dumps(query_params)}

        response = requests.get(endpoint, headers=self.headers, params=params)
        return response

    def list_departments(
        self,
        page: int,
        department_name: str | None = None,
        department_id: str | None = None,
    ) -> Response:
        endpoint = f"{self.base_url}/departments"

        query_params = {
            "where": {"archivedAt": {"$eq": None}},
            "order": [["name", "asc"]],
        }

        if department_id:
            query_params["where"]["id"] = {"$eq": department_id}
        elif department_name:
            query_params["where"]["name"] = {"$iLike": f"%{department_name}%"}

        params = {"page": page, "query": json.dumps(query_params)}

        response = requests.get(endpoint, headers=self.headers, params=params)
        return response

    def list_services(
        self, page: int, service_name: str | None = None, service_id: str | None = None
    ) -> Response:
        endpoint = f"{self.base_url}/services"

        query_params = {
            "where": {"archivedAt": {"$eq": None}, "type": {"$eq": "whatsapp"}},
            "order": [["name", "asc"]],
        }

        if service_id:
            query_params["where"]["id"] = {"$eq": service_id}
        elif service_name:
            query_params["where"]["name"] = {"$iLike": f"%{service_name}%"}

        params = {"page": page, "query": json.dumps(query_params)}

        response = requests.get(endpoint, headers=self.headers, params=params)
        return response
