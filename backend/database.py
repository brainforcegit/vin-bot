from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Մուտք դեպի բազա (.env-ից կամ ստանդարտ)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/vindb")

# SQLAlchemy engine ու session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# Մեր աղյուսակը
class VINLog(Base):
    __tablename__ = "vin_logs"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(17), index=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    report = Column(Text)

# Սկզբում կանչվում է՝ ստեղծելու աղյուսակը
def init_db():
    Base.metadata.create_all(bind=engine)
