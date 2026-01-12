import json
from pathlib import Path
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.exceptions.exception_handler import (
    exception_handler,
    generic_exception_handler,
)
from app.exceptions.exceptions import AppException
from app.routers import *


app = FastAPI(title="ReplyAI API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "The API is running"}


# Route to save incoming requests for debugging purposes
@app.post("/request")
def save_request_body(request: dict):
    folder_path = Path("saved_requests")
    folder_path.mkdir(parents=True, exist_ok=True)
    file_name = f"request_{uuid.uuid4().hex}.json"
    file_path = folder_path / file_name

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(request, f, ensure_ascii=False, indent=4)
    return {"message": "Request saved successfully"}


app.add_exception_handler(AppException, exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(company.router, prefix="/company", tags=["Companies"])
app.include_router(user.router, prefix="/user", tags=["Users"])
app.include_router(employee.router, prefix="/employee", tags=["Employees"])
app.include_router(reply.router, prefix="/reply", tags=["Replies"])
app.include_router(agenda.router, prefix="/agenda", tags=["Agendas"])
app.include_router(assistant.router, prefix="/assistant", tags=["Assistants"])
app.include_router(media.router, prefix="/media", tags=["Medias"])
app.include_router(voice.router, prefix="/voice", tags=["Voices"])
app.include_router(asaas.router, prefix="/asaas", tags=["Asaas"])
app.include_router(digisac.router, prefix="/digisac", tags=["Digisac"])
app.include_router(evolutionapi.router, prefix="/evolutionapi", tags=["EvolutionAPI"])
app.include_router(microsoft.router, prefix="/microsoft", tags=["Microsoft"])
app.include_router(google.router, prefix="/google", tags=["Google"])
app.include_router(rdstation.router, prefix="/rdstation", tags=["RDStation"])
app.include_router(job.router, prefix="/job", tags=["Jobs"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
