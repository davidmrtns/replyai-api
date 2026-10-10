from abc import ABC
from typing_extensions import Literal
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from datetime import datetime

from app.exceptions.exceptions import AIResponseException


def get_current_date_time() -> str:
    """Returns the current date and time as a string in the format "YYYY-MM-DD HH:MM:SS"."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NewAssistantClient(ABC):
    def __init__(self, model: BaseChatModel, instructions: str):

        self.agent = create_agent(
            model=model,
            tools=[get_current_date_time],
            system_message=instructions,
            checkpointer=InMemorySaver(),
        )

    def add_message(
        self, content: str, content_type: Literal["text", "image", "document"]
    ) -> HumanMessage:
        if content_type == "text":
            return HumanMessage(
                content_blocks=[{"type": content_type, "text": content}]
            )
        return HumanMessage(content_blocks=[{"type": content_type, "url": content}])

    def process_conversation(self, message: HumanMessage, thread_id: str):
        thread_config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.agent.invoke({"messages": [message]}, config=thread_config)
            return result["messages"][-1].content_blocks, thread_id
        except Exception as e:
            raise AIResponseException(
                conversation_id="",
                assistant_id="",
                detail=f"Failed to generate a response after processing the message.",
                user_friendly_detail=f"The AI assistant was unable to generate a response at this time. Please try again later or check the error logs for more details.",
                http_status_code=500,
            ) from e
