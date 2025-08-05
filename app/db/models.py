from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    ativo = Column(Boolean, default=True)
    admin = Column(Boolean, default=False)
    id_empresa = Column(Integer, ForeignKey("companies.id"))

    empresa = relationship("Company", backref="usuarios")


class Agenda(Base):
    __tablename__ = "agendas"

    id = Column(Integer, primary_key=True, index=True)
    endereco = Column(String)
    atalho = Column(String)
    id_empresa = Column(Integer, ForeignKey("companies.id"))

    empresa = relationship("Company", backref="agenda")


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


class Colaborador(Base):
    __tablename__ = "colaboradores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    apelido = Column(String)
    departamento = Column(String)
    id_empresa = Column(Integer, ForeignKey("companies.id"))

    empresa = relationship("Company", backref="colaboradores")


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


class AsaasClient(Base):
    __tablename__ = "asaas_clients"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String)
    rotulo = Column(String)
    client_number = Column(Integer)
    id_empresa = Column(Integer, ForeignKey("companies.id"))

    empresa = relationship("Company", backref="asaas_client")


class ExemploPrompt(Base):
    __tablename__ = "exemplos_prompt"

    id = Column(Integer, primary_key=True, index=True)
    tipo_assistente = Column(String)
    prompt = Column(String)
