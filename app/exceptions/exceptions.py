class AppException(Exception):
    def __init__(self, detail: str, user_friendly_detail: str = None, http_status_code: int = 500):
        self.detail = detail
        self.user_friendly_detail = user_friendly_detail or "An unexpected error occurred."
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
