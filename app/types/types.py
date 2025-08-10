from typing import Tuple

from app.db.new_models import Contact, Company
from app.utils.agenda_client import AgendaClient
from app.utils.assistant import Assistant as AiAssistant
from app.utils.crm_client import CRMClient
from app.utils.message_client import MessageClient


AssistantData = Tuple[AiAssistant | None, int | None]
CompanyData = Tuple[Company, MessageClient | None, AgendaClient | None, CRMClient | None]
ContactAndAssistant = Tuple[Contact, AiAssistant]
MessageData = Tuple[str, bool, str | None]
