from typing import Any

from pydantic import ValidationError

from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest

Request = DigisacRequest | EvolutionAPIRequest


class InvalidInboundMessage(Exception):
    pass


def deserialize_messages(
    messages: list[dict[str, Any]],
) -> list[Request]:
    requests: list[Request] = []

    for message in messages:
        integration = message["integration"]
        payload = message["payload"]

        try:
            if integration == "digisac":
                request = DigisacRequest.model_validate(payload)
            elif integration == "evolution":
                request = EvolutionAPIRequest.model_validate(payload)
            else:
                raise InvalidInboundMessage(f"Unsupported integration: {integration}")
        except ValidationError as error:
            raise InvalidInboundMessage(
                f"Invalid payload for integration {integration}: {error}"
            ) from error

        requests.append(request)

    return requests
