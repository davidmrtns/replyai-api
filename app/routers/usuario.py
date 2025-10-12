import jwt

from fastapi import APIRouter, Form, HTTPException, Response, Query
from fastapi.params import Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import obter_sessao
from app.db.models import Usuario
from app.db.new_models import Company
from app.schemas.atualizacao_empresa_schema import InformacoesUsuario
from app.schemas.empresa_schema import ListaUsuariosSchema, UsuarioSchema
from app.utils.password_utils import verify_password, create_access_token, hash_password
from app.utils.password_utils import SECRET_KEY, ALGORITHM


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usuario/login")

async def obter_usuario_logado(token: str = Cookie(None, alias="access_token"), db: Session = Depends(obter_sessao)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=401,
                detail="Não autenticado"
            )
    except:
        raise HTTPException(
            status_code=401,
            detail="Não autenticado"
        )

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado"
        )

    return user


router = APIRouter()

@router.get("/")
async def obter_usuario(usuario_logado: Usuario = Depends(obter_usuario_logado)):
    return usuario_logado

@router.post("/")
async def criar_usuario(
        request: InformacoesUsuario,
        usuario_logado: Usuario = Depends(obter_usuario_logado),
        db: Session = Depends(obter_sessao)
):
    if usuario_logado.admin:
        if request.senha == request.confirmacao_senha and request.senha is not None:
            senha_hash = hash_password(request.senha)

            if not usuario_logado.id_empresa:
                id_empresa = request.id_empresa
            else:
                id_empresa = usuario_logado.id_empresa

            novo_usuario = Usuario(
                nome=request.nome,
                email=request.email,
                senha=senha_hash,
                ativo=request.usuario_ativo,
                admin=request.admin,
                id_empresa=id_empresa
            )

            db.add(novo_usuario)
            db.commit()
            db.refresh(novo_usuario)
            return novo_usuario
        raise HTTPException(status_code=400, detail="As senhas inseridas não conferem")
    raise HTTPException(status_code=401, detail="Você não tem permissão para performar essa ação")

@router.put("/", response_model=UsuarioSchema)
async def alterar_usuario(
        request: InformacoesUsuario,
        usuario_logado: Usuario = Depends(obter_usuario_logado),
        db: Session = Depends(obter_sessao)
):
    if usuario_logado.admin:
        id_usuario = request.id
    elif request.id == usuario_logado.id:
        id_usuario = usuario_logado.id
    else:
        id_usuario = None

    if id_usuario:
        query = db.query(Usuario).filter_by(id=request.id)
        if usuario_logado.id_empresa:
            query = query.filter_by(id_empresa=usuario_logado.id_empresa)
        usuario_alterar = query.first()

        if not usuario_alterar:
            raise HTTPException(status_code=404, detail="O usuário não foi localizado ou você não tem permissão para editá-lo")

        usuario_alterar.nome = request.nome
        usuario_alterar.email = request.email
        usuario_alterar.ativo = request.usuario_ativo
        usuario_alterar.admin = request.admin

        if request.senha is not None:
            if request.senha == request.confirmacao_senha:
                senha_hash = hash_password(request.senha)
                usuario_alterar.senha = senha_hash
            else:
                raise HTTPException(status_code=400, detail="As senhas inseridas não conferem")
        db.commit()
        return usuario_alterar
    raise HTTPException(status_code=401, detail="Você não tem permissão para editar esse usuário")

@router.delete("/{id}")
async def remover_usuario(
        id: int,
        usuario_logado: Usuario = Depends(obter_usuario_logado),
        db: Session = Depends(obter_sessao)
):
    if usuario_logado.admin:
        query = db.query(Usuario).filter_by(id=id)
        if usuario_logado.id_empresa:
            query = query.filter_by(id_empresa=usuario_logado.id_empresa)

        usuario_remover = query.first()
        if usuario_remover:
            db.delete(usuario_remover)
            db.commit()
            return True
        return False
    raise HTTPException(status_code=401, detail="Você não tem permissão para excluir esse usuário")

@router.get("/todos", response_model=ListaUsuariosSchema)
async def obter_todos_usuario(
        usuario_logado: Usuario = Depends(obter_usuario_logado),
        db: Session = Depends(obter_sessao),
        cursor: Optional[int] = Query(None, alias="cursor", description="ID do último item carregado"),
        limit: int = Query(10, alias="limit", ge=1, le=50, description="Número de registros por página")
):
    if not usuario_logado.admin:
        raise HTTPException(status_code=401, detail="Você não tem permissão para performar essa ação")

    query = db.query(Usuario).order_by(Usuario.id.asc())

    if usuario_logado.id_empresa:
        query = query.filter(Usuario.id_empresa == usuario_logado.id_empresa)
    if cursor:
        query = query.filter(Usuario.id > cursor)

    usuarios = query.limit(limit + 1).all()
    has_more = len(usuarios) > limit

    if len(usuarios) > limit:
        usuarios.pop(-1)

    next_cursor = usuarios[-1].id if has_more else None

    return ListaUsuariosSchema(
        has_more=has_more,
        next_cursor=next_cursor,
        limit=limit,
        data=usuarios
    )

@router.post("/login")
async def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(obter_sessao)
):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username, Usuario.ativo == True).first()

    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if usuario.id_empresa:
        empresa = db.query(Company).filter_by(id=usuario.id_empresa).first()
        if not empresa.empresa_ativa:
            raise HTTPException(status_code=401, detail="Não foi possível fazer login pois a empresa à qual você faz parte está desativada. Entre em contato com um administrador do sistema")

    if not verify_password(form_data.password, usuario.senha):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = create_access_token(data={"sub": usuario.email})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none"
    )

    return {"status": True}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return True
