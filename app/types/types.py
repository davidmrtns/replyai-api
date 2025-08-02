from typing import Tuple

from app.db.models import Empresa
from app.utils.agenda_client import AgendaClient
from app.utils.crm_client import CRMClient
from app.utils.message_client import MessageClient


CompanyData = Tuple[Empresa, MessageClient, AgendaClient, CRMClient]
