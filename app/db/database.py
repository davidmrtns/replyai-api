from contextlib import contextmanager
import psycopg2
import tempfile
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.exceptions.exceptions import DatabaseConnectionException
from app.utils.logger import logger


# Certificate setup
SSL_CERTIFICATE = os.getenv("AZURE_POSTGRES_CERT")

if os.name == "nt":  # If Windows
    TEMP_CERT_PATH = os.path.join(tempfile.gettempdir(), "azure_postgres_cert.pem")
else:  # If Linux
    TEMP_CERT_PATH = "/tmp/azure_postgres_cert.pem"

if SSL_CERTIFICATE:
    try:
        if "-----BEGIN CERTIFICATE-----" in SSL_CERTIFICATE:
            SSL_CERTIFICATE = SSL_CERTIFICATE.replace("\\n", "\n")
        with open(TEMP_CERT_PATH, "w") as cert_file:
            cert_file.write(SSL_CERTIFICATE)
        os.environ["PGSSLROOTCERT"] = TEMP_CERT_PATH
    except Exception as e:
        print(f"Error saving certificate: {e}")


DATABASE_URL = os.getenv("DATABASE_URL")
MAX_RETRIES = 3
RETRY_DELAY = 5


engine = create_engine(
    DATABASE_URL,
    # connect_args={"sslmode": "verify-full"},
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _db_session_generator():
    attempts = 0
    while attempts < MAX_RETRIES:
        db = SessionLocal()
        try:
            yield db
            logger.info("Database connection established successfully.")
            return
        except (psycopg2.OperationalError, OperationalError) as e:
            db.rollback()
            logger.error(
                f"Error connecting to database: {e}. Attempt {attempts + 1} of {MAX_RETRIES}"
            )
            attempts += 1
            time.sleep(RETRY_DELAY)
            engine.dispose()
        finally:
            db.close()
    raise DatabaseConnectionException(
        detail="Unable to establish a connection to the database after several attempts. Check logs for more details.",
        user_friendly_detail="Database connection error. Please try again later.",
        http_status_code=500,
    )


def get_db_session():
    yield from _db_session_generator()


@contextmanager
def get_db_session_with_context():
    yield from _db_session_generator()
