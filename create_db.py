from app.db.database import Base, engine
from app.db.new_models import *


Base.metadata.create_all(bind=engine)
