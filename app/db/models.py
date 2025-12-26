from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class Midia(Base):
    __tablename__ = "midias"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String)
    mediatype = Column(String)
    nome = Column(String)
    atalho = Column(String)
    ordem = Column(Integer)
    id_empresa = Column(Integer, ForeignKey("companies.id"))

    empresa = relationship("Company", backref="midias")


class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    atalho = Column(String)
    comentario = Column(String)
    departmentId = Column(String)
    userId = Column(String)
    departamento_confirmacao = Column(Boolean)
    id_digisac_client = Column(Integer, ForeignKey("digisac_clients.id"))

    digisac_client = relationship("DigisacClient", backref="departamentos")


class ExemploPrompt(Base):  # TODO: check if it's necessary
    __tablename__ = "exemplos_prompt"

    id = Column(Integer, primary_key=True, index=True)
    tipo_assistente = Column(String)
    prompt = Column(String)
