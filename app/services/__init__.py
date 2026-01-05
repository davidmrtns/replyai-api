from app.clients.assistants_client import AssistantReply


class RespostaFinanceiro:
    def __init__(self, telefone: str, resposta: AssistantReply):
        self.telefone = telefone
        self.resposta = resposta

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            telefone=data["telefone"],
            resposta=AssistantReply.from_dict(data["resposta"]),
        )
