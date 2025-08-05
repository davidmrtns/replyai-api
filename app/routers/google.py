import os
import urllib.parse
import requests

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Company
from app.db.new_models import GoogleCalendarClient
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.atualizacao_empresa_schema import InformacoesFusoHorario
from app.schemas.empresa_schema import GoogleCalendarClientSchema as GoogleCalendarClientSchemaEmpresa
from app.services.agendamento_service import criar_agenda_client

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
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "code": codigo,
            "grant_type": "authorization_code",
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI")
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post("https://oauth2.googleapis.com/token", data=payload, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_info_response.status_code != 200:
            raise HTTPException(status_code=user_info_response.status_code, detail="Erro ao buscar informações do usuário.")

        user_data = user_info_response.json()
        user_email = user_data.get("email")

        if not user_email:
            raise HTTPException(status_code=400, detail="E-mail do usuário não encontrado.")

        google_calendar_client_db = db.query(GoogleCalendarClient).filter_by(id_empresa=empresa.id).first()
        if google_calendar_client_db:
            google_calendar_client_db.api_key = access_token
            google_calendar_client_db.client_x509_cert_url = refresh_token
            google_calendar_client_db.client_id = str(expires_in)
            google_calendar_client_db.client_email = user_email
        else:
            google_calendar_client = GoogleCalendarClient(
                project_id="",
                private_key_id="",
                private_key="",
                client_email=user_email,
                client_id="",
                client_x509_cert_url="",
                api_key="",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                duracao_evento=0,
                hora_inicio_agenda="",
                hora_final_agenda="",
                timezone="",
                id_empresa=empresa.id
            )
            db.add(google_calendar_client)
        db.commit()
        return RedirectResponse(url=os.getenv("SUCCESS_AUTH_URL"))
    return RedirectResponse(url=os.getenv("FAILED_AUTH_URL"))

@router.get("/{slug}/auth-link")
async def obter_link_autorizacao(
        slug: str,
        empresa: Company = Depends(verificar_permissao_empresa)
):

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar"
    ]

    auth_url = f"https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "access_type": "offline",
        "state": empresa.slug,
        "prompt": "consent"
    })

    return auth_url

@router.put("/{slug}/timezone", response_model=GoogleCalendarClientSchemaEmpresa)
async def alterar_informacoes_googlecalendar(
        slug: str,
        request: InformacoesFusoHorario,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    googlecalendar_client = db.query(GoogleCalendarClient).filter_by(id_empresa=empresa.id).first()
    if not googlecalendar_client:
        raise HTTPException(status_code=404, detail="Cliente do Google Calendar não encontrado para essa empresa")

    googlecalendar_client.timezone = request.fuso_horario
    db.commit()
    return googlecalendar_client
