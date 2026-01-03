from functools import wraps
from requests import Response

from app.exceptions.exceptions import AppException, IntegrationException


def ensure_success_status(integration_name: str, valid_statuses=(200, 201)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                response: Response = func(*args, **kwargs)

                if response.status_code not in valid_statuses:
                    raise IntegrationException(
                        integration_name=integration_name,
                        company_slug="",
                        detail=f"Unexpected status: {response.status_code}",
                        user_friendly_detail="An error occurred. Try again later.",
                        http_status_code=response.status_code,
                    )
                return response

            except AppException:
                raise
            except Exception as e:
                raise IntegrationException(
                    integration_name=integration_name,
                    company_slug="",
                    detail="Unexpected integration error",
                    user_friendly_detail="An error occurred. Try again later.",
                    http_status_code=500,
                ) from e

        return wrapper

    return decorator


def disabled_func(reason: str = "Function temporarily disabled"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raise NotImplementedError(reason)

        return wrapper

    return decorator
