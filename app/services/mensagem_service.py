from sqlalchemy.orm import Session

from app.db.models import Midia
from app.db.new_models import Contact, Voice, Assistant, Company
from app.db.new_models import DigisacClient, EvolutionAPIClient
from app.utils.assistant import Assistant as AiAssistant
from app.utils.digisac import Digisac
from app.utils.eleven_labs import ElevenLabs
from app.utils.evolutionapi import EvolutionAPI
from app.utils.message_client import MessageClient


async def enviar_mensagem(mensagem: str, audio: bool, midia: str | None, contato: Contact, empresa: Company | None, message_client: MessageClient, assistente: Assistant, db: Session):
    msg_audio = None
    mediatype = ""

    if audio:
        if isinstance(message_client, Digisac):
            mediatype = "audio/mpeg"
        else:
            mediatype = "audio"
        assistente_db = db.query(Assistant).filter_by(assistantId=assistente.id).first()
        if assistente_db is not None:
            voz = db.query(Voice).filter_by(id=assistente_db.id_voz).first()
            if voz is not None:
                if empresa.elevenlabs_api_key:
                    elevenlabs_client = ElevenLabs(empresa.elevenlabs_api_key)
                    ass_reescrita_db = db.query(Assistant).filter_by(proposito="reescrever", id_empresa=empresa.id).first()
                    if ass_reescrita_db:
                        assistente_reescrita = AiAssistant(nome=ass_reescrita_db.nome, id=ass_reescrita_db.assistantId, api_key=empresa.openai_api_key)
                        assistente_reescrita.adicionar_mensagens([mensagem], [], None)
                        mensagem_reescrita, _ = assistente_reescrita.criar_rodar_thread(thread_id=None)
                        msg_audio = await elevenlabs_client.gerar_audio(mensagem=mensagem_reescrita, id_voz=voz.voiceId, stability=voz.stability, similarity_boost=voz.similarity_boost, style=voz.style)
    message_client.enviar_mensagem(mensagem=mensagem, base64=msg_audio, mediatype=mediatype, nome_arquivo=None, contact_id=contato.contactId, userId=None, origin="bot", nome_assistente=assistente.nome)

    if midia and empresa:
        midias_db = db.query(Midia).filter_by(atalho=midia, id_empresa=empresa.id).order_by(Midia.ordem).all()
        for midia_db in midias_db:
            conteudo = message_client.baixar_arquivo(midia_db.url)
            if conteudo:
                message_client.enviar_mensagem(mensagem="", base64=conteudo, mediatype=midia_db.mediatype, nome_arquivo=midia_db.nome, contact_id=contato.contactId, userId=None, origin="bot", nome_assistente=assistente.nome)


def criar_message_client(empresa: Company, db: Session):
    nome_assistente_padrao = db.query(Assistant).filter_by(id=empresa.assistentePadrao).with_entities(Assistant.nome).scalar()

    if empresa.message_client_type == "digisac":
        digisac_client_db = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
        if digisac_client_db:
            return Digisac(
                slug=digisac_client_db.digisacSlug,
                service_id=digisac_client_db.service_id,
                defaultUserId=digisac_client_db.digisacDefaultUser,
                defaultAssistantName=nome_assistente_padrao,
                token=digisac_client_db.digisacToken
            )
    elif empresa.message_client_type == "evolution":
        evolutionapi_client_db = db.query(EvolutionAPIClient).filter_by(id_empresa=empresa.id).first()
        if evolutionapi_client_db:
            return EvolutionAPI(
                api_key=evolutionapi_client_db.apiKey,
                defaultAssistantName=nome_assistente_padrao,
                instance=evolutionapi_client_db.instanceName
            )
    else:
        raise ValueError(f"Tipo de MessageClient desconhecido: {empresa.message_client_type}")
    return None
