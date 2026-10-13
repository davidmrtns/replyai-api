from abc import ABC
from typing import Any, List
from typing_extensions import Literal
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
import os
from threading import Lock
from uuid import uuid4

from app.assistant_functions.assistant_function import get_tools
from app.assistant_functions.runtime_context import RuntimeContext
from app.exceptions.exceptions import AIResponseException

DATABASE_URL = os.getenv("DATABASE_URL")
CHECKPOINTER_POOL_MIN_SIZE = int(os.getenv("CHECKPOINTER_POOL_MIN_SIZE", "1"))
CHECKPOINTER_POOL_MAX_SIZE = int(os.getenv("CHECKPOINTER_POOL_MAX_SIZE", "5"))

_checkpointer_pool: ConnectionPool | None = None
_checkpointer: PostgresSaver | None = None
_checkpointer_lock = Lock()


def get_checkpointer() -> PostgresSaver:
    global _checkpointer_pool, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required for the Postgres checkpointer")

    with _checkpointer_lock:
        if _checkpointer is None:
            _checkpointer_pool = ConnectionPool(
                conninfo=DATABASE_URL,
                min_size=CHECKPOINTER_POOL_MIN_SIZE,
                max_size=CHECKPOINTER_POOL_MAX_SIZE,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            )
            _checkpointer_pool.wait()
            _checkpointer = PostgresSaver(_checkpointer_pool)
            _checkpointer.setup()

    return _checkpointer


def close_checkpointer_pool() -> None:
    global _checkpointer_pool, _checkpointer

    with _checkpointer_lock:
        if _checkpointer_pool is not None:
            _checkpointer_pool.close()
        _checkpointer_pool = None
        _checkpointer = None


class AssistantClient(ABC):
    def __init__(
        self,
        assistant_name: str,
        assistant_id: str,
        model: BaseChatModel,
        instructions: str,
    ):
        self.assistant_name = assistant_name
        self.assistant_id = assistant_id
        self.messages: List[HumanMessage] = []
        checkpointer = get_checkpointer()
        self.agent = create_agent(
            model=model,
            tools=get_tools(),
            system_prompt=instructions,
            context_schema=RuntimeContext,
            checkpointer=checkpointer,
        )

    def add_message(
        self, content: str, content_type: Literal["text", "image", "document"]
    ):
        if content_type == "text":
            message = HumanMessage(
                content_blocks=[{"type": content_type, "text": content}]
            )
        else:
            message = HumanMessage(
                content_blocks=[{"type": content_type, "url": content}]
            )
        self.messages.append(message)

    def process_conversation(self, thread_id: str | None = None):
        thread_id = thread_id or str(uuid4())
        thread_config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.agent.invoke(
                {"messages": self.messages},
                config=thread_config,
                context={
                    "assistant_id": self.assistant_id,
                    "thread_id": thread_id,
                },
            )
            return result["messages"][-1].content_blocks, thread_id
        except Exception as e:
            raise AIResponseException(
                conversation_id=thread_id,
                assistant_id=self.assistant_id,
                detail=f"Failed to generate a response after processing the message: {e}",
                user_friendly_detail=(
                    "The AI assistant was unable to generate a response at this time. "
                    "Please try again later or check the error logs for more details."
                ),
                http_status_code=500,
            ) from e

    def get_messages(self, thread_id: str) -> list[dict]:
        thread_config = {"configurable": {"thread_id": thread_id}}
        state = self.agent.get_state(thread_config)

        return [
            {"type": message.type, "content": message.content}
            for message in state.values.get("messages", [])
        ]

    def transcribe_audio(self, file: Any) -> str:
        raise NotImplementedError(
            "Audio transcription is not implemented in this client."
        )
