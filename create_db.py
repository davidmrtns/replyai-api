from app.db.database import Base, engine
from app.db.models import *


Base.metadata.create_all(bind=engine)
