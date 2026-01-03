from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.services.reply_service import ReplyService


router = APIRouter()


@router.post("/{slug}/{token}")
async def reply(
    request: EvolutionAPIRequest,  # TODO: change to DigisacRequest | EvolutionAPIRequest
    slug: str,
    token: str,
    db: Session = Depends(get_db_session),
):
    reply_service = ReplyService(db, request)
    return await reply_service.generate_reply(slug, token)
