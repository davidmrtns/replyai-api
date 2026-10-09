from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

PROVIDER_API_KEY_ARGUMENTS = {
    "google_genai": "google_api_key",
    "openai": "api_key",
    "anthropic": "api_key",
}


def build_chat_model(
    provider: str,
    model_name: str,
    api_key: str,
    **model_options: Any,
) -> BaseChatModel:
    """Build a tenant-scoped model without changing process environment state."""
    normalized_provider = provider.strip().lower()
    api_key_argument = PROVIDER_API_KEY_ARGUMENTS.get(normalized_provider)

    if api_key_argument is None:
        raise ValueError(f"Unsupported LangChain provider: {provider}")

    return init_chat_model(
        model=model_name,
        model_provider=normalized_provider,
        **{api_key_argument: api_key},
        **model_options,
    )
