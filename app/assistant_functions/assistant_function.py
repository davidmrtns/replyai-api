from openai.types.responses import FunctionToolParam
from typing import List
from app.utils.logger import logger


FUNCTION_REGISTRY = {}


def register_function(documentation):
    def decorator(func):
        FUNCTION_REGISTRY[documentation.get("name")] = {
            "function": func,
            "documentation": documentation,
        }
        logger.debug(f"Function registered: {documentation.get('name')}")
        return func

    return decorator


def get_function_documentations() -> List[FunctionToolParam]:
    return [entry["documentation"] for entry in FUNCTION_REGISTRY.values()]
