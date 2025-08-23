import json
from pathlib import Path
import uuid
from fastapi import FastAPI

from app.exceptions.exception_handler import exception_handler
from app.exceptions.exceptions import AppException
from app.routers import trabalho, empresa, usuario, voz, evolutionapi, digisac, microsoft, google, exemplo
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers.reply import reply
from app.routers.agenda import agenda
from app.routers.assistant import assistant
from app.routers.media import media


app = FastAPI()

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():
    return {"message": "The API is running"}


# Route to save incoming requests for debugging purposes
@app.post("/request")
async def save_request_body(request: dict):
    folder_path = Path("saved_requests")
    folder_path.mkdir(parents=True, exist_ok=True)
    file_name = f"request_{uuid.uuid4().hex}.json"
    file_path = folder_path / file_name
    
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(request, f, ensure_ascii=False, indent=4)
    return {"message": "Request saved successfully"}


app.add_exception_handler(AppException, exception_handler)

app.include_router(reply.router, prefix="/reply", tags=["Replies"])
app.include_router(agenda.router, prefix="/agenda", tags=["Agendas"])
app.include_router(assistant.router, prefix="/assistant", tags=["Assistants"])
app.include_router(media.router, prefix="/media", tags=["Medias"])

app.include_router(trabalho.router, prefix="/trabalho",tags=["Trabalhos"])
app.include_router(empresa.router, prefix="/empresa", tags=["Empresas"])
app.include_router(usuario.router, prefix="/usuario", tags=["Usuarios"])
app.include_router(exemplo.router, prefix="/exemplo", tags=["Exemplos"])
app.include_router(voz.router, prefix="/voz", tags=["Vozes"])
app.include_router(evolutionapi.router, prefix="/evolutionapi", tags=["EvolutionAPI"])
app.include_router(digisac.router, prefix="/digisac", tags=["Digisac"])
app.include_router(microsoft.router, prefix="/microsoft", tags=["Microsoft"])
app.include_router(google.router, prefix="/google", tags=["Google"])
