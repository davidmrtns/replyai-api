class AIResponseException(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)

    def __str__(self):
        return f"AIResponseException: {self.detail}"
