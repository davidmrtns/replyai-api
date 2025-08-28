import io
import base64
import json
import uuid
from typing import NamedTuple

from PIL import Image
from fastapi import UploadFile
import httpx
from openai import OpenAI
from openai.types.beta import FunctionToolParam
from openai.types.beta.threads import Run
import time

from app.clients.message_client import FileData
from app.db.new_models import Assistant
from app.exceptions.exceptions import AIResponseException, FailedRunException, PendingRunException
from app.utils.function_utils import FUNCTION_REGISTRY
from app.utils.logger import logger


PENDING_STATUSES = {'queued', 'in_progress', 'cancelling'}
ERROR_STATUSES = {'canceled', 'failed', 'expired'}
FINAL_STATUSES = {'completed', 'canceled', 'failed', 'expired'}


class RunResult(NamedTuple):
    text_response: str
    thread_id: str


class AssistantsClient:
    def __init__(self, assistant_name: str, openai_assistant_id: str, openai_api_key: str):
        self.client = OpenAI(http_client=CustomHTTPClient(), api_key=openai_api_key)
        self.assistant_name = assistant_name
        self.openai_assistant_id = openai_assistant_id
        self.messages = []
        self.files = []
        self.audio_extensions = {
            'audio/mpeg': 'mp3',
            'audio/wav': 'wav',
            'audio/x-m4a': 'm4a',
            'audio/m4a': 'm4a',
            'audio/ogg': 'oga',
            'audio/vorbis': 'oga',
            'application/octet-stream': 'oga'
        }


    @classmethod
    def from_db(cls, assistant_db: Assistant):
        return cls(
            assistant_name=assistant_db.assistant_name,
            openai_assistant_id=assistant_db.openai_assistant_id,
            openai_api_key=assistant_db.company.openai_api_key
        )


    def add_message(
            self,
            message: str | None | None,
            is_image: bool = False,
            image_id: str | None = None,
            attachments_ids: list | None = None,
            thread_id: str | None = None
    ) -> None:
        base_message = {
            'role': 'user'
        }

        if not is_image:
            base_message['content'] = {
                [{ 'type': 'text', 'text': message }]
            }
        else:
            base_message['content'] = {
                [
                    {
                        "type": "image_file",
                        "image_file": { "file_id": image_id, "detail": "high" }
                    }
                ]
            }

        if attachments_ids and len(attachments_ids) > 0:
            base_message['attachments'] = [
                {
                    'file_id': attachment_id,
                    'tools': [
                        { 'type': 'file_search' }
                    ]
                } for attachment_id in attachments_ids
            ]

        if thread_id is None:
            self.messages.append(base_message)
        else:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                **base_message
            )


    def upload_image(self, image: str) -> str:
        img_data = base64.b64decode(image)
        image = Image.open(io.BytesIO(img_data))

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        img_bytes.name = f'image_{uuid.uuid4()}.png'

        response = self.client.files.create(
            file=img_bytes,
            purpose="vision"
        )

        return response.id


    async def upload_pdf_file(self, file: UploadFile) -> str:
        content = await file.read()
        pdf_bytes = io.BytesIO(content)
        pdf_bytes.seek(0)
        pdf_bytes.name = f'file_{uuid.uuid4()}.pdf'

        response = self.client.files.create(
            file=pdf_bytes,
            purpose="assistants"
        )

        return response.id


    def download_uploaded_file(self, file_id: str):
        try:
            content = self.client.files.content(file_id)
            return content
        except:
            raise ValueError("Couldn't download the file") # TODO: raise custom error


    def delete_uploaded_file(self, file_id: str) -> None:
        self.client.files.delete(file_id)


    async def transcribe_audio(self, audio_file: FileData) -> str:
        filename, mimetype, file_stream = audio_file
        
        if mimetype in self.audio_extensions:
            file_stream.seek(0)
            file_stream.name = filename

            try:
                transcription = self.client.audio.transcriptions.create(
                    model='whisper-1',
                    file=file_stream
                )
                return transcription.text
            except Exception as e:
                raise ValueError(f'Error while transcribing: {e}') # TODO: raise custom error
        else:
            raise ValueError('Audio file type not supported') # TODO: raise custom error


    def create_or_run_thread(self, thread_id: str | None = None) -> RunResult:
        MAX_ATTEMPTS = 5

        for attempt in range(1, MAX_ATTEMPTS + 1):
            error = None
            try:
                run = self._initiate_run(thread_id)
                response = self._process_run(run)
                return response
            except FailedRunException as e:
                break # No point in retrying if the run has definitively failed
            except Exception as e:
                error = e
                time.sleep(15)
                continue
            finally:
                if error:
                    logger.exception(f'Attempt {attempt}: {error}')
        
        raise AIResponseException(
            thread_id=thread_id,
            assistant_id=self.openai_assistant_id,
            detail=f'Failed to generate a response after {MAX_ATTEMPTS} attempts.',
            user_friendly_detail=f'The AI assistant was unable to generate a response at this time. Please try again later or check the error logs for more details.',
            http_status_code=500
        )


    def _initiate_run(self, thread_id: str | None) -> Run:
        if thread_id:
            runs = self.client.beta.threads.runs.list(
                thread_id=thread_id,
                limit=1,
                order='desc'
            )
            last_run = runs.data[0]

            if last_run.status not in PENDING_STATUSES:
                return self.client.beta.threads.runs.create(
                    assistant_id=self.openai_assistant_id,
                    thread_id=thread_id,
                    tool_choice='auto'
                )
            
            raise PendingRunException('A run is already in progress for this thread. Trying again in a few seconds...', last_run.id, thread_id)
        else:
            return self.client.beta.threads.create_and_run(
                assistant_id=self.openai_assistant_id,
                thread={ 'messages': self.messages },
                tool_choice='auto'
            )


    def _process_run(self, run: Run) -> RunResult:
        while run.status not in FINAL_STATUSES:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=run.thread_id,
                run_id=run.id
            )

            if run.required_action and run.required_action.type == 'submit_tool_outputs':
                if not self._process_tool_calls(run):
                    raise PendingRunException('An error occured while processing tool calls for the run. Trying again...', run.id, run.thread_id)
            
            time.sleep(2)
        
        if run.status in ERROR_STATUSES:
            raise PendingRunException('An error occured while processing the run. Trying again...', run.id, run.thread_id)

        run_result = self.client.beta.threads.messages.list(
            thread_id=run.thread_id,
            limit=1,
            order='desc'
        )

        last_message = run_result.data
        if not last_message or not last_message[0].content:
            raise FailedRunException('No response message found after run completion. Trying again...', run.id, run.thread_id)

        return RunResult(
            text_response=last_message[0].content[0].text.value,
            thread_id=run.thread_id
        )


    def _process_tool_calls(self, run: Run) -> bool:
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        function_outputs = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            try:
                result = self._execute_function(function_name, arguments)

                function_outputs.append({
                    'tool_call_id': tool_call.id,
                    'output': json.dumps(result)
                })
            except Exception as e:
                logger.exception(f'Error while executing {function_name}: {e}')

        if function_outputs:
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=run.thread_id,
                run_id=run.id,
                tool_outputs=function_outputs
            )

            return True
        return False


    def _execute_function(self, function_name, arguments):
        func = FUNCTION_REGISTRY.get(function_name)
        if not func:
            raise ValueError(f'Unknown function called: {function_name}')

        return func(self.openai_assistant_id, **arguments)


    def run_instruction(self, thread_id: str, instructions: str) -> str:
        run = self.client.beta.threads.runs.create(
            assistant_id=self.openai_assistant_id,
            thread_id=thread_id,
            instructions=instructions
        )

        while run.status != "completed":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=run.thread_id,
                run_id=run.id
            )
            time.sleep(2)

        resultado = self.client.beta.threads.messages.list(
            thread_id=run.thread_id
        )

        return resultado.data[0].content[0].text.value


    def list_thread_messages(self, thread_id: str, order: str, limit: int):
        messages = self.client.beta.threads.messages.list(thread_id, order=order, limit=limit)
        return messages


    def get_specific_message_from_thread(self, thread_id: str, index: int, order: str, limit: int): # TODO: check if there's another more efficient way of getting the message
        try:
            messages = self.list_thread_messages(thread_id, order, limit)
            if messages:
                return messages.data[index].content[0].text.value
        except Exception as e:
            print(f"An error occurred while trying to get message from thread: {e}") # TODO: raise custom error
        return None


class AssistantReply:
    def __init__(self, activity: str, department_code: str, message: str, media_code: str, assistant_code: str):
        self.activity = activity
        self.department_code = department_code
        self.message = message
        self.media_code = media_code
        self.assistant_code = assistant_code


    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            activity=data['atividade'],
            department_code=data['departamento'],
            message=data['mensagem'],
            media_code=data['midia'],
            assistant_code=data['assistente']
        )


    @classmethod
    def from_run_result(cls, run_result: RunResult):
        try:
            data = json.loads(run_result.text_response)
            return cls.from_dict(data)
        except Exception as e:
            raise ValueError(f'Error parsing AssistantReply from run result: {e}')


class RespostaConfirmacao:
    def __init__(self, cliente: str, telefone: str, resposta_confirmacao: AssistantReply):
        self.cliente = cliente
        self.telefone = telefone
        self.resposta_confirmacao = resposta_confirmacao

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            cliente=data["cliente"],
            telefone=data["telefone"],
            resposta_confirmacao=AssistantReply.from_dict(data["resposta_confirmacao"])
        )


class RespostaFinanceiro:
    def __init__(self, telefone: str, resposta: AssistantReply):
        self.telefone = telefone
        self.resposta = resposta

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            telefone=data["telefone"],
            resposta=AssistantReply.from_dict(data["resposta"])
        )


class Instrucao:
    def __init__(self, acao: str, dados: dict | None):
        self.acao = acao
        self.dados = dados

    def to_dict(self):
        obj = {"acao": self.acao}
        if self.dados is not None:
            obj["dados"] = self.dados

        return obj

    def __str__(self):
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        super().__init__(*args, **kwargs)


class Ferramentas:
    @staticmethod
    def get_current_datetime():
        return FunctionToolParam(
            function={
                "name": "get_current_datetime",
                "description": "A function to extract current date and time",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                    "required": []
                }
            },
            type="function"
        )

    @staticmethod
    def get_employees():
        return FunctionToolParam(
            function={
                "name": "get_employees",
                "description": "A function to return a list of employees",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                    "required": []
                }
            },
            type="function"
        )

    @staticmethod
    def get_all_tools():
        return [
            Ferramentas.get_employees(),
            Ferramentas.get_current_datetime()
        ]
