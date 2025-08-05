from contextlib import contextmanager

import psycopg2
import tempfile
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


# Configurações de certificado
CERTIFICADO_SSL = os.getenv("AZURE_POSTGRES_CERT")

if os.name == "nt":  # Se for Windows
    TEMP_CERT_PATH = os.path.join(tempfile.gettempdir(), "azure_postgres_cert.pem")
else:  # Se for Linux
    TEMP_CERT_PATH = "/tmp/azure_postgres_cert.pem"

if CERTIFICADO_SSL:
    try:
        if "-----BEGIN CERTIFICATE-----" in CERTIFICADO_SSL:
            CERTIFICADO_SSL = CERTIFICADO_SSL.replace("\\n", "\n")
        with open(TEMP_CERT_PATH, "w") as cert_file:
            cert_file.write(CERTIFICADO_SSL)
        os.environ["PGSSLROOTCERT"] = TEMP_CERT_PATH
    except Exception as e:
        print(f"Erro ao salvar o certificado: {e}")


DATABASE_URL = os.getenv('DATABASE_URL')
MAX_RETRIES = 3
RETRY_DELAY = 5

engine = create_engine(
    DATABASE_URL,
    #connect_args={"sslmode": "verify-full"},
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def obter_sessao():
    tentativas = 0
    while tentativas < MAX_RETRIES:
        db = SessionLocal()
        try:
            yield db
            return
        except (psycopg2.OperationalError, OperationalError) as e:
            db.rollback()
            print(f"Erro de conexão com o banco: {e}. Tentativa {tentativas + 1} de {MAX_RETRIES}")
            tentativas += 1
            time.sleep(RETRY_DELAY)
            engine.dispose()
        finally:
            db.close()
    raise Exception("Não foi possível estabelecer conexão com o banco após várias tentativas.")


@contextmanager
def retornar_sessao():
    tentativas = 0
    while tentativas < MAX_RETRIES:
        db = SessionLocal()
        try:
            yield db
            return
        except (psycopg2.OperationalError, OperationalError) as e:
            db.rollback()
            print(f"Erro de conexão com o banco: {e}. Tentativa {tentativas + 1} de {MAX_RETRIES}")
            tentativas += 1
            time.sleep(RETRY_DELAY)
            engine.dispose()
        finally:
            db.close()
    raise Exception("Não foi possível estabelecer conexão com o banco após várias tentativas.")
