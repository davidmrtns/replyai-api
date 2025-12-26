from fastapi import Depends
from openai import OpenAI

from app.db.models import Company
from app.routers.routers_helpers import check_company_access
from app.clients.assistants_client import CustomHTTPClient


def get_openai_client(company: Company = Depends(check_company_access)) -> OpenAI:
    return OpenAI(http_client=CustomHTTPClient(), api_key=company.openai_api_key)
