from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import PromptExample, User
from .routers_helpers import get_logged_in_user
from app.schemas.atualizacao_empresa_schema import InformacoesExemploPrompt
from app.schemas.empresa_schema import ExemploPromptSchema


router = APIRouter()


@router.post("/")
async def criar_exemplo_prompt(
    request: InformacoesExemploPrompt,
    usuario_logado: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    if usuario_logado.admin and not usuario_logado.id_empresa:
        exemplo = (
            db.query(PromptExample)
            .filter_by(assistant_type=request.tipo_assistente)
            .first()
        )
        if exemplo:
            raise HTTPException(
                status_code=409,
                detail="Já existe um exemplo de prompt desse tipo de assistente",
            )
        else:
            exemplo = PromptExample(
                assistant_type=request.tipo_assistente, prompt=request.prompt
            )
            db.add(exemplo)
            db.commit()
            db.refresh(exemplo)
            return exemplo
    raise HTTPException(
        status_code=401, detail="Você não tem permissão para criar exemplos de prompt"
    )


@router.get("/{tipo_assistente}")
async def obter_exemplo_prompt(
    tipo_assistente: str,
    usuario_logado: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    exemplo = db.query(PromptExample).filter_by(assistant_type=tipo_assistente).first()
    if exemplo:
        return exemplo
    return None


@router.put("/{tipo_assistente}", response_model=ExemploPromptSchema)
async def editar_exemplo_prompt(
    tipo_assistente: str,
    request: InformacoesExemploPrompt,
    usuario_logado: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    if usuario_logado.admin and not usuario_logado.id_empresa:
        exemplo = (
            db.query(PromptExample).filter_by(assistant_type=tipo_assistente).first()
        )
        if exemplo:
            exemplo.prompt = request.prompt
            db.commit()
            return exemplo
        return None
    raise HTTPException(
        status_code=401, detail="Você não tem permissão para editar exemplos de prompt"
    )


@router.delete("/{tipo_assistente}")
async def excluir_exemplo_prompt(
    tipo_assistente: str,
    usuario_logado: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    if usuario_logado.admin and not usuario_logado.id_empresa:
        exemplo = (
            db.query(PromptExample).filter_by(assistant_type=tipo_assistente).first()
        )
        if exemplo:
            db.delete(exemplo)
            db.commit()
            return True
        return False
    raise HTTPException(
        status_code=401, detail="Você não tem permissão para excluir exemplos de prompt"
    )
