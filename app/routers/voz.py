import os
import tempfile
from typing import List

from fastapi import APIRouter, UploadFile
from fastapi.params import Depends, File
from sqlalchemy.orm import Session
from typing import Annotated

from app.db.database import obter_sessao
from app.db.new_models import Company, Voice
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.integrations_schemas import VozSchema, parse_form_data_voz
from app.utils.eleven_labs import ElevenLabs


def obter_elevenlabs_client(empresa: Company = Depends(verificar_permissao_empresa)):
    return ElevenLabs(api_key=empresa.elevenlabs_api_key)


router = APIRouter()

@router.post("/{slug}")
async def criar_voz(
        slug: str,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[ElevenLabs, Depends(obter_elevenlabs_client)],
        request: VozSchema = Depends(parse_form_data_voz),
        arquivos: List[UploadFile] = File(...),
        db: Session = Depends(obter_sessao)
):
    temp_files = []

    try:
        for arquivo in arquivos:
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo.filename)[1])
            temp.write(await arquivo.read())
            temp.close()
            temp_files.append(temp.name)

        voz = cliente.criar_voz(nome=request.nome, descricao=request.descricao, arquivos=temp_files)
        if voz.voice_id:
            voz_db = Voice(
                nome=request.nome,
                voiceId=voz.voice_id,
                stability=request.stability,
                similarity_boost=request.similarity_boost,
                style=request.style,
                id_empresa=empresa.id
            )

            db.add(voz_db)
            db.commit()
            db.refresh(voz_db)
            return voz_db
    finally:
        for temp_file in temp_files:
            os.remove(temp_file)
    return {"erro": "Erro ao criar a voz"}

@router.get("/{slug}/{id}")
async def obter_voz(
        slug: str,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[ElevenLabs, Depends(obter_elevenlabs_client)],
        id: int,
        db: Session = Depends(obter_sessao)
):
    voz_db = db.query(Voice).filter_by(id=id, id_empresa=empresa.id).first()
    if voz_db:
        voz = cliente.obter_voz(voice_id=voz_db.voiceId)
        if voz:
            return {
                "preview_url": voz.preview_url,
                "descricao": voz.description
            }
    return None

@router.put("/{slug}/{id}")
async def editar_voz(
        slug: str,
        id: int,
        request: VozSchema,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[ElevenLabs, Depends(obter_elevenlabs_client)],
        db: Session = Depends(obter_sessao)
):
    voz_db = db.query(Voice).filter_by(id=id, id_empresa=empresa.id).first()
    if voz_db:
        resposta = cliente.editar_voz(voice_id=voz_db.voiceId, nome=request.nome, descricao=request.descricao)

        if resposta:
            voz_db.nome = request.nome
            voz_db.stability = request.stability
            voz_db.similarity_boost = request.similarity_boost
            voz_db.style = request.style

            db.commit()
            return voz_db
    return None

@router.delete("/{slug}/{id}")
async def excluir_voz(
        slug: str,
        id: int,
        empresa: Annotated[Company, Depends(verificar_permissao_empresa)],
        cliente: Annotated[ElevenLabs, Depends(obter_elevenlabs_client)],
        db: Session = Depends(obter_sessao)
):
    voz_db = db.query(Voice).filter_by(id=id, id_empresa=empresa.id).first()
    if voz_db:
        cliente.excluir_voz(voz_db.voiceId)
        db.delete(voz_db)
        db.commit()
        return True
    return False
