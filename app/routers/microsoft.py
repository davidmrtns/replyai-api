import os
import urllib.parse
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Company
from app.db.new_models import OutlookClient
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.atualizacao_empresa_schema import InformacoesFusoHorario
from app.schemas.empresa_schema import OutlookClientSchema as OutlookClientSchemaEmpresa
from app.services.agendamento_service import criar_agenda_client
from app.utils.outlook import Outlook


router = APIRouter()

@router.get("/callback")
async def callback(
        request: Request,
        db: Session = Depends(obter_sessao)
):
    codigo = request.query_params.get("code")
    empresa = request.query_params.get("state")

    if not codigo:
        raise HTTPException(status_code=400, detail="Código não encontrado")

    empresa = db.query(Company).filter_by(slug=empresa).first()
    if empresa:
        payload = {
            "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
            "code": codigo,
            "grant_type": "authorization_code",
            "redirect_uri": os.getenv("MICROSOFT_REDIRECT_URI"),
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=payload, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in

        graph_headers = {"Authorization": f"Bearer {access_token}"}
        user_info_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=graph_headers)

        if user_info_response.status_code != 200:
            raise HTTPException(status_code=user_info_response.status_code, detail="Erro ao buscar informações do usuário.")

        user_data = user_info_response.json()
        user_email = user_data.get("mail") or user_data.get("userPrincipalName")

        if not user_email:
            raise HTTPException(status_code=400, detail="E-mail do usuário não encontrado.")

        outlook_client_db = db.query(OutlookClient).filter_by(id_empresa=empresa.id).first()
        if outlook_client_db:
            outlook_client_db.access_token = access_token
            outlook_client_db.refresh_token = refresh_token
            outlook_client_db.expires_at = expires_at
            outlook_client_db.usuarioPadrao = user_email
        else:
            outlook = OutlookClient(
                clientId="",
                tenantId="",
                clientSecret="",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                expires_at=expires_at,
                duracaoEvento=0,
                usuarioPadrao=user_email,
                horaInicioAgenda="",
                horaFinalAgenda="",
                timeZone="",
                id_empresa=empresa.id
            )
            db.add(outlook)
        db.commit()
        return RedirectResponse(url=os.getenv("SUCCESS_AUTH_URL"))
    return RedirectResponse(url=os.getenv("FAILED_AUTH_URL"))

@router.get("/{slug}/auth-link")
async def obter_link_autorizacao(
        slug: str,
        empresa: Company = Depends(verificar_permissao_empresa)
):
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI")
    scopes = ["User.Read", "Calendars.ReadWrite", "offline_access"]

    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(scopes),
        "state": empresa.slug,
        "prompt": "select_account"
    })

    return auth_url

@router.get("/{slug}/timezones")
async def obter_timezones(
        slug: str,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    outlook_client = criar_agenda_client(empresa, db)
    if outlook_client:
        timezones = await outlook_client.listar_timezones()
        return timezones
    return None

@router.put("/{slug}/timezone", response_model=OutlookClientSchemaEmpresa)
async def alterar_timezone(
        slug: str,
        request: InformacoesFusoHorario,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    outlook_client = db.query(OutlookClient).filter_by(id_empresa=empresa.id).first()
    if not outlook_client:
        raise HTTPException(status_code=404, detail="Cliente do Outlook não encontrado para essa empresa")

    outlook_client.timeZone = request.fuso_horario
    db.commit()
    return outlook_client
