from abc import ABC
from typing_extensions import Literal
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from datetime import datetime
import os
from uuid import uuid4

from app.exceptions.exceptions import AIResponseException

DATABASE_URL = os.getenv("DATABASE_URL")


def get_current_date_time() -> str:
    """Returns the current date and time as a string in the format "YYYY-MM-DD HH:MM:SS"."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NewAssistantClient(ABC):
    def __init__(self, assistant_id: str, model: BaseChatModel, instructions: str):
        self.assistant_id = assistant_id
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
            tools=[get_current_date_time],
            system_prompt=instructions,
            checkpointer=checkpointer,
        )

    def close(self) -> None:
        self._pool.close()

    def add_message(
        self, content: str, content_type: Literal["text", "image", "document"]
    ) -> HumanMessage:
        if content_type == "text":
            return HumanMessage(
                content_blocks=[{"type": content_type, "text": content}]
            )
        return HumanMessage(content_blocks=[{"type": content_type, "url": content}])

    def process_conversation(self, message: HumanMessage, thread_id: str | None = None):
        thread_id = thread_id or str(uuid4())
        thread_config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.agent.invoke({"messages": [message]}, config=thread_config)
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
