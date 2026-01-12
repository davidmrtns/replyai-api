import io
import base64
import json
import uuid
from typing import NamedTuple

from PIL import Image
from fastapi import UploadFile
import httpx
from openai import OpenAI
from openai.types.responses import Response, ResponseFunctionToolCall
import time

from app.assistant_functions.assistant_function import FUNCTION_REGISTRY
from app.clients.message_client import FileData
from app.exceptions.exceptions import (
    AIResponseException,
    FailedResponseException,
    PendingResponseException,
)
from app.utils.api_key_encryption import decrypt_api_key
from app.utils.logger import logger


PENDING_STATUSES = {"queued", "in_progress"}
ERROR_STATUSES = {"canceled", "failed", "expired"}
FINAL_STATUSES = {"completed", "canceled", "failed", "expired"}


class ResponseOutput(NamedTuple):
    text_response: str
    conversation_id: str


class AssistantsClient:
    def __init__(
        self,
        assistant_name: str,
        instructions: str,
        assistant_id: str,
        openai_api_key: str,
    ):
        decrypted_api_key = decrypt_api_key(openai_api_key)

        self.client = OpenAI(http_client=CustomHTTPClient(), api_key=decrypted_api_key)
        self.assistant_name = assistant_name
        self.instructions = instructions
        self.assistant_id = assistant_id
        self.messages = []
        self.files = []
        self.audio_extensions = {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/x-m4a": "m4a",
            "audio/m4a": "m4a",
            "audio/ogg": "oga",
            "audio/vorbis": "oga",
            "application/octet-stream": "oga",
        }

    def add_message(
        self,
        message: str | None,
        is_image: bool = False,
        image_id: str | None = None,
        attachments_ids: list | None = None,
    ) -> None:
        base_message = {"role": "user", "type": "message"}

        if not is_image:
            base_message["content"] = [{"type": "input_text", "text": message}]
        else:
            base_message["content"] = [
                {
                    "type": "input_image",
                    "detail": "high",
                    "file_id": image_id,
                }
            ]

        if attachments_ids and len(attachments_ids) > 0:
            base_message["content"] = [
                {
                    "type": "input_file",
                    "file_id": attachment_id,
                }
                for attachment_id in attachments_ids
            ]

        self.messages.append(base_message)

    def upload_image(self, image: str) -> str:
        img_data = base64.b64decode(image)
        image = Image.open(io.BytesIO(img_data))

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        img_bytes.name = f"image_{uuid.uuid4()}.png"

        response = self.client.files.create(file=img_bytes, purpose="vision")

        return response.id

    async def upload_pdf_file(self, file: UploadFile) -> str:
        content = await file.read()
        pdf_bytes = io.BytesIO(content)
        pdf_bytes.seek(0)
        pdf_bytes.name = f"file_{uuid.uuid4()}.pdf"

        response = self.client.files.create(file=pdf_bytes, purpose="user_data")

        return response.id

    def download_uploaded_file(self, file_id: str):
        try:
            content = self.client.files.content(file_id)
            return content
        except:
            raise ValueError("Couldn't download the file")  # TODO: raise custom error

    def delete_uploaded_file(self, file_id: str) -> None:
        self.client.files.delete(file_id)

    async def transcribe_audio(self, audio_file: FileData) -> str:
        filename, mimetype, file_stream = audio_file
        base_mimetype = mimetype.split(";")[0].strip()  # normalize mimetype

        if base_mimetype in self.audio_extensions:
            file_stream.seek(0)
            file_stream.name = filename

            try:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1", file=file_stream
                )
                return transcription.text
            except Exception as e:
                raise ValueError(
                    f"Error while transcribing: {e}"
                )  # TODO: raise custom error
        else:
            raise ValueError(
                "Audio file type not supported"
            )  # TODO: raise custom error

    def process_conversation(
        self, conversation_id: str | None = None
    ) -> ResponseOutput:
        MAX_ATTEMPTS = 1

        for attempt in range(1, MAX_ATTEMPTS + 1):
            error = None
            try:
                response = self._generate_response(conversation_id)
                return self._process_response_output(response)
            except FailedResponseException as e:
                break  # No point in retrying if the response has definitively failed
            except Exception as e:
                error = e
                time.sleep(15)
                continue
            finally:
                if error:
                    logger.exception(f"Attempt {attempt}: {error}")

        raise AIResponseException(
            conversation_id=conversation_id,
            assistant_id=self.assistant_id,
            detail=f"Failed to generate a response after {MAX_ATTEMPTS} attempts.",
            user_friendly_detail=f"The AI assistant was unable to generate a response at this time. Please try again later or check the error logs for more details.",
            http_status_code=500,
        )

    def _generate_response(self, conversation_id: str | None) -> Response:
        if conversation_id:
            items = self.client.conversations.items.list(
                conversation_id=conversation_id, limit=1, order="desc"
            )
            last_item = items.data[0]

            if last_item.status in PENDING_STATUSES:
                raise PendingResponseException(
                    detail="A message is already in progress for this conversation. Trying again in a few seconds...",
                    response_id=last_item.id,
                    thread_id=conversation_id,
                )
        else:
            conversation = self.client.conversations.create()
            conversation_id = conversation.id

        return self.client.responses.create(
            model="gpt-4o",
            conversation=conversation_id,
            instructions=self.instructions,
            input=self.messages,
        )

    # TODO: test the function calls processing
    def _process_response_output(self, response: Response) -> ResponseOutput:
        input_list = []
        function_call_outputs = []

        input_list += response.output

        for item in response.output:
            if item.type != "function_call":
                continue

            result = self._process_tool_calls(item, response.conversation.id)
            function_call_outputs.append(result)

        if len(function_call_outputs) > 0:
            input_list += function_call_outputs
            response = self.client.responses.create(
                model="gpt-4o",
                instructions="Continue the previous response considering the function call outputs.",
                conversation=response.conversation.id,
                input=input_list,
            )

        if response.status in ERROR_STATUSES:
            raise FailedResponseException(
                detail="An error occured while processing the message. Trying again...",
                response_id=response.id,
                thread_id=response.conversation.id,
            )

        return ResponseOutput(
            text_response=response.output[0].content[0].text,
            conversation_id=response.conversation.id,
        )

    def _process_tool_calls(
        self, tool_call: ResponseFunctionToolCall, conversation_id: str
    ) -> dict:
        try:
            function_name = tool_call.name
            args = json.loads(tool_call.arguments)

            result = self._execute_function(function_name, conversation_id, args)
            return {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": str(result),
            }
        except Exception as e:
            raise PendingResponseException(
                detail="An error occured while processing tool calls for the response. Trying again...",
                response_id=tool_call.id,
                thread_id=conversation_id,
            ) from e

    def _execute_function(self, function_name: str, conversation_id: str, arguments):
        func = FUNCTION_REGISTRY.get(function_name)
        if not func:
            raise ValueError(f"Unknown function called: {function_name}")

        func = func.get("function")
        return func(self.assistant_id, conversation_id, **arguments)


class CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        super().__init__(*args, **kwargs)
