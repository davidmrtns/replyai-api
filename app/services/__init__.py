from app.clients.assistants_client import AssistantReply


# TODO: temporary additions, remove later
class RespostaConfirmacao:
    def __init__(
        self, cliente: str, telefone: str, resposta_confirmacao: AssistantReply
    ):
        self.cliente = cliente
        self.telefone = telefone
        self.resposta_confirmacao = resposta_confirmacao

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            cliente=data["cliente"],
            telefone=data["telefone"],
            resposta_confirmacao=AssistantReply.from_dict(data["resposta_confirmacao"]),
        )


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
