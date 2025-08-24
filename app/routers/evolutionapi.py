import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Company
from app.db.new_models import EvolutionAPIClient as EvolutionAPIClientDB
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.integrations_schemas import EvolutionInstanceSchema, EvolutionWebhookSchema
from app.clients.evolutionapi_client import EvolutionAPIClient


router = APIRouter()

@router.post("/{slug}")
async def criar_instancia(
        request: EvolutionInstanceSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    global_api_key = os.getenv("EVOLUTIONAPI_GLOBAL_KEY", "")
    if global_api_key:
        cliente = EvolutionAPIClient(api_key=global_api_key, instance="", defaultAssistantName="")
        resposta = cliente.criar_instancia(global_api_key=global_api_key, nome_instancia=request.nome_instancia)

        if resposta.status_code == 201:
            resposta_json = resposta.json()

            evolutionapi_client = EvolutionAPIClientDB(
                apiKey=resposta_json.get("hash", {}).get("apikey"),
                instanceName=resposta_json.get("instance", {}).get("instanceName"),
                id_empresa=empresa.id
            )

            db.add(evolutionapi_client)
            db.commit()
            db.refresh(evolutionapi_client)
            return evolutionapi_client
    return None

@router.get("/{slug}/{api_key}")
async def obter_instancia(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.retornar_instancia()
        if resposta.status_code == 200:
            return resposta.json()
    return None

@router.get("/{slug}/{api_key}/conectar")
async def conectar_instancia(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.conectar_instancia()
        if resposta.status_code == 200:
            return resposta.json()
    return None

@router.put("/{slug}/{api_key}/reiniciar")
async def reiniciar_instancia(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.reiniciar_instancia()
        if resposta.status_code == 200:
            return resposta.json()
    return None

@router.delete("/{slug}/{api_key}/desligar")
async def desligar_instancia(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.desligar_instancia()
        if resposta.status_code == 200:
            return resposta.json()
    return None

@router.get("/{slug}/{api_key}/checar-conexao")
async def checar_conexao_instancia(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.checar_conexao()
        if resposta.status_code == 200:
            return resposta.json()
    return None

@router.get("/checar-conexao-evolutionapi")
async def checar_conexao_evolutionapi(
        db: Session = Depends(obter_sessao)
):
    cliente = EvolutionAPIClient(api_key='mude-me', instance='', defaultAssistantName="")
    resposta = cliente.checar_conexao_evolutionapi()
    if resposta.status_code == 200:
        return resposta.json()
    return None

@router.post("/{slug}/{api_key}/webhook")
async def adicionar_webhook(
        slug: str,
        api_key: str,
        request: EvolutionWebhookSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.adicionar_webhook(request.webhook_url, request.habilitado)
        if resposta.status_code == 201:
            return resposta.json()
    return None

@router.get("/{slug}/{api_key}/webhook")
async def listar_webhooks(
        slug: str,
        api_key: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    evolutionapi_db = db.query(EvolutionAPIClientDB).filter_by(apiKey=api_key, id_empresa=empresa.id).first()
    if evolutionapi_db:
        cliente = EvolutionAPIClient(api_key=evolutionapi_db.apiKey, instance=evolutionapi_db.instanceName, defaultAssistantName="")
        resposta = cliente.listar_webhooks()
        if resposta.status_code == 200:
            return resposta.json()
    return None
