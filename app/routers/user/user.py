from fastapi import APIRouter, Response, Query
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import obter_sessao
from app.db.new_models import Company, User
from app.exceptions.exceptions import UserAccessException
from ..routers_helpers import get_logged_in_user
from app.schemas.atualizacao_empresa_schema import InformacoesUsuario
from app.schemas.empresa_schema import ListaUsuariosSchema, UsuarioSchema
from app.utils.password_utils import verify_password, create_access_token, hash_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/user/login')
router = APIRouter()


@router.get('/')
async def get_logged_in_user(logged_in_user: User = Depends(get_logged_in_user)):
    return logged_in_user


@router.post('/')
async def create_user(
        request: InformacoesUsuario,
        logged_in_user: User = Depends(get_logged_in_user),
        db: Session = Depends(obter_sessao)
):
    if logged_in_user.admin:
        if request.senha is not None and request.senha == request.confirmacao_senha:
            hashed_password = hash_password(request.senha)

            # If the logged-in user is an admin but not tied to a company, they can specify the company for the new user
            if not logged_in_user.id_empresa:
                id_empresa = request.id_empresa
            else:
                id_empresa = logged_in_user.id_empresa

            new_user = User(
                nome=request.nome,
                email=request.email,
                senha=hashed_password,
                ativo=request.usuario_ativo,
                admin=request.admin,
                id_empresa=id_empresa
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        raise UserAccessException(
            detail="Password does not exist or is different than confirmation.",
            user_friendly_detail="The inputted passwords do not match. Try again.",
            http_status_code=400
        )
    raise UserAccessException(
        detail="The logged in user is not an admin.",
        user_friendly_detail="You don't have permission to perform this action.",
        http_status_code=403
    )


@router.put('/', response_model=UsuarioSchema)
async def edit_user(
        request: InformacoesUsuario,
        logged_in_user: User = Depends(get_logged_in_user),
        db: Session = Depends(obter_sessao)
):
    # If the logged-in user is an admin, they can edit any user
    if logged_in_user.admin:
        user_to_edit_id = request.id
    elif request.id == logged_in_user.id:
        user_to_edit_id = logged_in_user.id
    else:
        user_to_edit_id = None

    if user_to_edit_id:
        query = db.query(User).filter_by(id=request.id)
        if logged_in_user.id_empresa:
            query = query.filter_by(id_empresa=logged_in_user.id_empresa)
        user = query.first()

        if not user:
            raise UserAccessException(
                detail="User to edit was not found in the database.",
                user_friendly_detail="The user was not found, or you don't have permission to edit it.",
                http_status_code=404
            )

        user.nome = request.nome
        user.email = request.email
        user.ativo = request.usuario_ativo
        user.admin = request.admin

        if request.senha is not None and request.senha == request.confirmacao_senha:
            hashed_password = hash_password(request.senha)
            user.senha = hashed_password
        else:
            raise UserAccessException(
                detail="Password does not exist or is different than confirmation.",
                user_friendly_detail="The inputted passwords do not match. Try again.",
                http_status_code=400
            )

        db.commit()
        return user
    raise UserAccessException(
        detail="The logged in user is not an admin, or is trying to edit another user.",
        user_friendly_detail="You don't have permission to edit this user.",
        http_status_code=403
    )


@router.delete('/{id}')
async def delete_user(
        id: int,
        logged_in_user: User = Depends(get_logged_in_user),
        db: Session = Depends(obter_sessao)
):
    # Only admins can delete users
    if logged_in_user.admin:
        query = db.query(User).filter_by(id=id)
        if logged_in_user.id_empresa:
            query = query.filter_by(id_empresa=logged_in_user.id_empresa)
        user = query.first()

        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    raise UserAccessException(
        detail="The logged in user is not an admin.",
        user_friendly_detail="You don't have permission to edit this user.",
        http_status_code=403
    )


@router.get('/all', response_model=ListaUsuariosSchema)
async def get_all_users(
        logged_in_user: User = Depends(get_logged_in_user),
        db: Session = Depends(obter_sessao),
        cursor: Optional[int] = Query(None, alias='cursor', description='ID do último item carregado'),
        limit: int = Query(10, alias='limit', ge=1, le=50, description='Número de registros por página')
):
    if not logged_in_user.admin:
        raise UserAccessException(
            detail="The logged in user is not an admin.",
            user_friendly_detail="You don't have permission to perform this action.",
            http_status_code=403
        )

    query = db.query(User).order_by(User.id.asc())
    if logged_in_user.id_empresa:
        query = query.filter(User.id_empresa == logged_in_user.id_empresa)
    if cursor:
        query = query.filter(User.id > cursor)

    users = query.limit(limit + 1).all()
    has_more = len(users) > limit

    if len(users) > limit:
        users.pop(-1)

    next_cursor = users[-1].id if has_more else None

    return ListaUsuariosSchema(
        has_more=has_more,
        next_cursor=next_cursor,
        limit=limit,
        data=users
    )


@router.post('/login')
async def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(obter_sessao)
):
    user = db.query(User).filter(User.email == form_data.username, User.ativo == True).first()

    if not user:
        raise UserAccessException(
            detail='User not found with this email.',
            user_friendly_detail='No user was found with this email.',
            http_status_code=404
        )

    if user.id_empresa:
        empresa = db.query(Company).filter_by(id=user.id_empresa).first()
        if not empresa.is_active:
            raise UserAccessException(
                detail='The user company is deactivated.',
                user_friendly_detail="You can't log in because the company associated with your account is deactivated. Contact the system admin.",
                http_status_code=401
            )

    if not verify_password(form_data.password, user.senha):
        raise UserAccessException(
            detail='The password is incorrect.',
            user_friendly_detail='Incorret credentials.',
            http_status_code=401
        )

    access_token = create_access_token(data={'sub': user.email})

    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=True,
        samesite='none'
    )
    return True


@router.post('/logout')
async def logout(response: Response):
    response.delete_cookie(key='access_token')
    return True
