from typing import Tuple

from app.db.new_models import Contact, Company
from app.utils.agenda_client import AgendaClient
from app.utils.assistants_client import AssistantsClient, RespostaFinanceiro
from app.utils.crm_client import CRMClient
from app.clients.message_client import MessageClient


AssistantData = Tuple[AssistantsClient | None, int | None]
BillingResponse = Tuple[RespostaFinanceiro | None, str | None]
CompanyData = Tuple[Company, MessageClient | None, AgendaClient | None, CRMClient | None]
ContactAndAssistant = Tuple[Contact, AssistantsClient]
MessageData = Tuple[str | None, bool, str | None]
