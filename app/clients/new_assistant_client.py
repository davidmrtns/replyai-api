from abc import ABC
from typing import List
from typing_extensions import Literal
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
import os
from uuid import uuid4

from app.assistant_functions.get_current_datetime import get_current_datetime
from app.assistant_functions.runtime_context import RuntimeContext
from app.exceptions.exceptions import AIResponseException

DATABASE_URL = os.getenv("DATABASE_URL")


class NewAssistantClient(ABC):
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
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required for the Postgres checkpointer")

        self._pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=10,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        self._pool.wait()
        checkpointer = PostgresSaver(self._pool)
        checkpointer.setup()
        self.agent = create_agent(
            model=model,
            tools=[get_current_datetime],
            system_prompt=instructions,
            context_schema=RuntimeContext,
            checkpointer=checkpointer,
        )

    def close(self) -> None:
        self._pool.close()

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
