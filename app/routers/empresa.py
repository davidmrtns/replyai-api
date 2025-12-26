import secrets
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import (
    RDStationCRMClient,
    RDStationCRMDealStage,
    AsaasClient,
    User,
    Employee,
    Company,
    Assistant,
)
from .routers_helpers import get_logged_in_user
from app.schemas.atualizacao_empresa_schema import (
    InformacoesBasicas,
    InformacoesMensagens,
    InformacoesAgenda,
    InformacoesAssistentes,
    InformacoesCRM,
    InformacoesRDStationCRMClient,
    InformacoesRDStationDealStage,
    InformacoesFinanceiras,
    InformacoesAsaas,
    InformacoesCriarEmpresa,
    InformacoesColaborador,
)
from app.schemas.empresa_schema import (
    EmpresaSchema,
    RDStationCRMClientSchema,
    RDStationCRMDealStageSchema,
    AsaasClientSchema,
    EmpresaMinSchema,
    ColaboradorSchema,
)
from app.utils.api_key_encryption import encrypt_api_key


async def verificar_permissao_empresa(
    slug: str,
    db: Session = Depends(obter_sessao),
    usuario: User = Depends(get_logged_in_user),
):
    empresa = db.query(Company).filter_by(slug=slug).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    if usuario.id_empresa is not None and (
        usuario.id_empresa != empresa.id or not empresa.empresa_ativa
    ):
        raise HTTPException(
            status_code=403, detail="Você não tem permissão para acessar esta empresa"
        )

    return empresa


router = APIRouter(dependencies=[Depends(get_logged_in_user)])


@router.get("/", response_model=List[EmpresaMinSchema])
async def obter_todas_empresas(
    usuario: User = Depends(get_logged_in_user), db: Session = Depends(obter_sessao)
):
    if not usuario.id_empresa:
        empresas = db.query(Company).all()
    else:
        empresas = (
            db.query(Company).filter_by(id=usuario.id_empresa, empresa_ativa=True).all()
        )
    return empresas


@router.post("/")
async def criar_empresa(
    request: InformacoesCriarEmpresa,
    usuario: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    if not usuario.id_empresa:
        empresa = db.query(Company).filter_by(slug=request.slug).first()
        if not empresa:
            token = secrets.token_hex(32)
            empresa = Company(
                nome=request.nome,
                slug=request.slug,
                token=token,
                fuso_horario=request.fuso_horario,
                openai_api_key=encrypt_api_key(request.openai_api_key),
                elevenlabs_api_key=encrypt_api_key(request.elevenlabs_api_key),
                empresa_ativa=request.empresa_ativa,
            )
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            return empresa
    return None


@router.get("/{slug}", response_model=EmpresaSchema)
async def obter_empresa(
    slug: str,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    return empresa


@router.put("/{slug}/informacoes_basicas", response_model=EmpresaSchema)
async def alterar_informacoes_basicas(
    slug: str,
    request: InformacoesBasicas,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    empresa.nome = request.nome
    empresa.fuso_horario = request.fuso_horario
    empresa.empresa_ativa = request.empresa_ativa
    empresa.openai_api_key = encrypt_api_key(request.openai_api_key)
    empresa.elevenlabs_api_key = encrypt_api_key(request.elevenlabs_api_key)
    db.commit()
    return empresa


@router.post("/{slug}/informacoes_basicas/colaborador")
async def adicionar_colaborador(
    slug: str,
    request: InformacoesColaborador,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    colaborador = Employee(
        name=request.name,
        nickname=request.nickname,
        department_name=request.department,
        company_id=empresa.id,
    )

    db.add(colaborador)
    db.commit()
    db.refresh(colaborador)
    return colaborador


@router.put("/{slug}/informacoes_basicas/colaborador", response_model=ColaboradorSchema)
async def alterar_colaborador(
    slug: str,
    request: InformacoesColaborador,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    colaborador = (
        db.query(Employee).filter_by(id=request.id, company_id=empresa.id).first()
    )
    if not colaborador:
        raise HTTPException(
            status_code=404, detail="Colaborador não encontrado para essa empresa"
        )

    colaborador.name = request.name
    colaborador.nickname = request.nickname
    colaborador.department_name = request.department
    db.commit()
    return colaborador


@router.delete("/{slug}/informacoes_basicas/colaborador/{id}")
async def remover_colaborador(
    slug: str,
    id: int,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    colaborador = db.query(Employee).filter_by(id=id, company_id=empresa.id).first()
    if colaborador:
        db.delete(colaborador)
        db.commit()
        return True
    return False


@router.put("/{slug}/informacoes_assistentes", response_model=EmpresaSchema)
async def alterar_informacoes_assistentes(
    slug: str,
    request: InformacoesAssistentes,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    if request.assistente_padrao:
        assistente = (
            db.query(Assistant)
            .filter_by(
                id=request.assistente_padrao,
                id_empresa=empresa.id,
                proposito="responder",
            )
            .first()
        )
        if not assistente:
            raise HTTPException(
                status_code=404, detail="Assistente não encontrado para essa empresa"
            )

        empresa.assistentePadrao = request.assistente_padrao
        db.commit()
    return empresa


@router.put("/{slug}/informacoes_mensagens", response_model=EmpresaSchema)
async def alterar_informacoes_mensagens(
    slug: str,
    request: InformacoesMensagens,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    empresa.message_client_type = request.tipo_cliente
    empresa.recall_timeout_minutes = request.tempo_recall_min
    empresa.final_recall_timeout_minutes = request.tempo_recall_final_min
    empresa.recall_quant = request.quant_recalls
    empresa.recall_ativo = request.ativar_recall
    empresa.recall_confirmacao_ativo = request.ativar_recall_confirmacao
    empresa.mensagem_erro_ia = request.mensagem_erro_ia
    db.commit()
    return empresa


@router.put("/{slug}/informacoes_agenda", response_model=EmpresaSchema)
async def alterar_informacoes_agenda(
    slug: str,
    request: InformacoesAgenda,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    empresa.agenda_client_type = request.tipo_cliente
    empresa.tipo_cancelamento_evento = request.tipo_cancelamento_evento
    empresa.confirmar_agendamentos_ativo = request.ativar_confirmacao
    empresa.duracao_evento = request.duracao_evento
    empresa.hora_inicio_agenda = request.hora_inicio_agenda
    empresa.hora_final_agenda = request.hora_final_agenda
    db.commit()
    return empresa


@router.put("/{slug}/informacoes_crm", response_model=EmpresaSchema)
async def alterar_informacoes_crm(
    slug: str,
    request: InformacoesCRM,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    empresa.crm_client_type = request.tipo_cliente
    db.commit()
    return empresa


@router.post("/{slug}/informacoes_crm/rdstation")
async def adicionar_cliente_rdstation(
    slug: str,
    request: InformacoesRDStationCRMClient,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(id_empresa=empresa.id).first()
    )
    if rdstationcrm_client:
        raise HTTPException(
            status_code=404,
            detail="Essa empresa já possui um cliente do RD Station CRM",
        )

    rdstationcrm_client = RDStationCRMClient(
        token=encrypt_api_key(request.token),
        id_fonte_padrao=request.id_fonte_padrao,
        id_empresa=empresa.id,
    )

    db.add(rdstationcrm_client)
    db.commit()
    db.refresh(rdstationcrm_client)
    return rdstationcrm_client


@router.put(
    "/{slug}/informacoes_crm/rdstation", response_model=RDStationCRMClientSchema
)
async def alterar_informacoes_rdstation(
    slug: str,
    request: InformacoesRDStationCRMClient,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(id_empresa=empresa.id).first()
    )
    if not rdstationcrm_client:
        raise HTTPException(
            status_code=404,
            detail="Cliente do RD Station CRM não encontrado para essa empresa",
        )

    rdstationcrm_client.token = encrypt_api_key(request.token)
    rdstationcrm_client.id_fonte_padrao = request.id_fonte_padrao
    db.commit()
    return rdstationcrm_client


@router.post("/{slug}/informacoes_crm/rdstation/estagio")
async def adicionar_estagio(
    slug: str,
    request: InformacoesRDStationDealStage,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(id_empresa=empresa.id).first()
    )
    if not rdstationcrm_client:
        raise HTTPException(
            status_code=404,
            detail="Cliente do RD Station CRM não encontrado para essa empresa",
        )

    estagio = RDStationCRMDealStage(
        atalho=request.atalho,
        deal_stage_id=request.deal_stage_id,
        user_id=request.user_id,
        deal_stage_inicial=request.estagio_inicial,
        id_rdstationcrm_client=rdstationcrm_client.id,
    )

    db.add(estagio)
    db.commit()
    db.refresh(estagio)
    return estagio


@router.put(
    "/{slug}/informacoes_crm/rdstation/estagio",
    response_model=RDStationCRMDealStageSchema,
)
async def alterar_informacoes_estagio(
    slug: str,
    request: InformacoesRDStationDealStage,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(id_empresa=empresa.id).first()
    )
    if not rdstationcrm_client:
        raise HTTPException(
            status_code=404,
            detail="Cliente do RD Station CRM não encontrado para essa empresa",
        )

    estagio = (
        db.query(RDStationCRMDealStage)
        .filter_by(id=request.id, id_rdstationcrm_client=rdstationcrm_client.id)
        .first()
    )
    if not estagio:
        raise HTTPException(
            status_code=404,
            detail="Estágio não encontrado para esse cliente do RD Station CRM",
        )

    estagio.atalho = request.atalho
    estagio.deal_stage_id = request.deal_stage_id
    estagio.user_id = request.user_id
    estagio.deal_stage_inicial = request.estagio_inicial
    db.commit()
    return estagio


@router.delete("/{slug}/informacoes_crm/rdstation/estagio/{id}")
async def remover_estagio(
    slug: str,
    id: int,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(id_empresa=empresa.id).first()
    )
    if not rdstationcrm_client:
        raise HTTPException(
            status_code=404,
            detail="Cliente do RD Station CRM não encontrado para essa empresa",
        )

    estagio = (
        db.query(RDStationCRMDealStage)
        .filter_by(id=id, id_rdstationcrm_client=rdstationcrm_client.id)
        .first()
    )
    if estagio:
        db.delete(estagio)
        db.commit()
        return True
    return False


@router.put("/{slug}/informacoes_financeiras", response_model=EmpresaSchema)
async def alterar_informacoes_financeiras(
    slug: str,
    request: InformacoesFinanceiras,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    empresa.financial_client_type = request.tipo_cliente
    empresa.lembrar_vencimentos_ativo = request.lembrar_vencimentos
    empresa.enviar_boleto_lembrar_vencimento = request.enviar_boletos_vencimentos
    empresa.cobrar_inadimplentes_ativo = request.cobrar_inadimplentes
    db.commit()
    return empresa


@router.post("/{slug}/informacoes_financeiras/asaas")
async def adicionar_cliente_asaas(
    slug: str,
    request: InformacoesAsaas,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    asaas_client = (
        db.query(AsaasClient)
        .filter_by(id_empresa=empresa.id, client_number=request.numero_cliente)
        .first()
    )
    if asaas_client:
        raise HTTPException(
            status_code=409,
            detail="Essa empresa já possui um cliente do Asaas com esse número de cliente",
        )

    asaas_client = AsaasClient(
        token=encrypt_api_key(request.token),
        rotulo=request.rotulo,
        client_number=request.numero_cliente,
        id_empresa=empresa.id,
    )

    db.add(asaas_client)
    db.commit()
    db.refresh(asaas_client)
    return asaas_client


@router.put("/{slug}/informacoes_financeiras/asaas", response_model=AsaasClientSchema)
async def alterar_informacoes_cliente_asaas(
    slug: str,
    request: InformacoesAsaas,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    asaas_client = (
        db.query(AsaasClient)
        .filter_by(id_empresa=empresa.id, client_number=request.numero_cliente)
        .first()
    )
    if not asaas_client:
        raise HTTPException(
            status_code=404, detail="Cliente do Asaas não encontrado para essa empresa"
        )

    asaas_client.token = encrypt_api_key(request.token)
    asaas_client.rotulo = request.rotulo
    db.commit()
    return asaas_client


@router.delete("/{slug}/informacoes_financeiras/asaas/{id}")
async def remover_cliente_asaas(
    slug: str,
    id: int,
    empresa: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    asaas_client = db.query(AsaasClient).filter_by(id=id, id_empresa=empresa.id).first()
    if asaas_client:
        db.delete(asaas_client)
        db.commit()
        return True
    return False
