from openai.types.responses import FunctionToolParam
from typing import List
from langchain_core.tools import BaseTool

from app.utils.logger import logger

TOOL_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> BaseTool:
    TOOL_REGISTRY[tool.name] = tool
    logger.debug(f"Tool registered: {tool.name}")
    return tool


def get_tools() -> list[BaseTool]:
    return list(TOOL_REGISTRY.values())


# TODO: remove later
def get_function_documentations() -> List[FunctionToolParam]:
    return [entry["documentation"] for entry in {}.values()]
