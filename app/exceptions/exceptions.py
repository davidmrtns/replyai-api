class AppException(Exception):
    def __init__(
        self, detail: str, user_friendly_detail: str = None, http_status_code: int = 500
    ):
        self.detail = detail
        self.user_friendly_detail = (
            user_friendly_detail or "An unexpected error occurred."
        )
        self.http_status_code = http_status_code
        super().__init__(self.detail)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.detail}"

    def detailed(self):
        data = vars(self).copy()
        return data


class AIResponseException(AppException):
    def __init__(self, thread_id: str, assistant_id: str, **kwargs):
        self.thread_id = thread_id or "Unknown thread"
        self.assistant_id = assistant_id or "Unknown assistant"
        super().__init__(**kwargs)


class NoAccessToCompanyException(AppException):
    def __init__(self, company_slug: str, **kwargs):
        self.company_slug = company_slug
        super().__init__(**kwargs)


class ConflictingRequestException(AppException):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MalformedRequestException(AppException):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ResourceNotFoundException(AppException):
    def __init__(self, resource_name: str, resource_id: str, **kwargs):
        self.resource_name = resource_name or "Unknown resource"
        self.resource_identifier = resource_id or "No ID provided"
        super().__init__(**kwargs)


class UserAccessException(AppException):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class AssistantEditingException(AppException):
    def __init__(self, assistant_id: str, **kwargs):
        self.assistant_id = assistant_id or "Unknown assistant"
        super().__init__(**kwargs)


class IntegrationAuthException(AppException):
    def __init__(self, integration_name: str, company_slug: str, **kwargs):
        self.integration_name = integration_name or "Unknown integration"
        self.company_slug = company_slug or "Unknown company slug"
        super().__init__(**kwargs)


class RunException(Exception):
    def __init__(self, detail: str, run_id: str, thread_id: str):
        self.detail = detail
        self.run_id = run_id or "Unknown run"
        self.thread_id = thread_id or "Unknown thread"
        super().__init__(self.detail)

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.detail} (Run ID: {self.run_id}, Thread ID: {self.thread_id})"


class PendingRunException(RunException):
    pass


class FailedRunException(RunException):
    pass


class FailedFunctionRunException(Exception):
    def __init__(self, detail: str, function_name: str):
        self.detail = detail
        self.function_name = function_name or "Unknown function"
        super().__init__(self.detail)

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.detail} (Function name: {self.function_name})"
