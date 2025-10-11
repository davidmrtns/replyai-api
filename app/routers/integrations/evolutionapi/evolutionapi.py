import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Company
from .evolutionapi_helpers import add_evolutionapi_client_to_db, get_evolutionapi_client
from ...routers_helpers import check_company_access
from app.schemas.integrations_schemas import EvolutionInstanceSchema, EvolutionAPIWebhookSchema
from app.clients.evolutionapi_client import EvolutionAPIClient


router = APIRouter()


@router.post('/{company_slug}')
async def create_instance(
        request: EvolutionInstanceSchema,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    response = EvolutionAPIClient.create_instance(request.nome_instancia)

    if response.status_code == 201:
        db_register_response = await add_evolutionapi_client_to_db(response, company.id, db)
        return db_register_response
    return None


@router.get('/{company_slug}/{api_key}')
async def fetch_instance(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)

    response = evolutionapi_client.fetch_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.get('/{company_slug}/{api_key}/connect')
async def connect_instance(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)

    response = evolutionapi_client.connect_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.put('/{company_slug}/{api_key}/restart')
async def restart_instance(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)
    
    response = evolutionapi_client.restart_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.delete('/{company_slug}/{api_key}/logout')
async def desligar_instancia(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)
    
    response = evolutionapi_client.logout_instance()
    if response.status_code == 200:
        return response.json()
    return None


@router.get('/{company_slug}/{api_key}/check-instance-connection')
async def check_instance_connection_state(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)
    
    response = evolutionapi_client.check_instance_connection_state()
    if response.status_code == 200:
        return response.json()
    return None


@router.get('/check-evolutionapi-connection')
async def check_evolutionapi_connection():
    try:
        response = EvolutionAPIClient.check_evolutionapi_connection()
        return response.status_code == 200
    except Exception:
        # TODO: log the exception
        return False


@router.post('/{company_slug}/{api_key}/webhook')
async def add_webhook(
        company_slug: str,
        api_key: str,
        request: EvolutionAPIWebhookSchema,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)

    response = evolutionapi_client.add_webhook(request.webhook_url, request.is_enabled)
    if response.status_code == 201:
        return response.json()
    return None


@router.get('/{company_slug}/{api_key}/webhook')
async def list_webhooks(
        company_slug: str,
        api_key: str,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_client = await get_evolutionapi_client(company, api_key, db)
    
    response = evolutionapi_client.list_webhooks()
    if response.status_code == 200:
        return response.json()
    return None
