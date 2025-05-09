from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Подключение к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/vindb")

# SQLAlchemy engine и session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# Модель таблицы для логов VIN
class VINLog(Base):
    __tablename__ = "vin_logs"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(17), index=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    report = Column(Text)

# Новая модель для хранения кредитов пользователя
class VINCredits(Base):
    __tablename__ = "vin_credits"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(String(50), unique=True, index=True)
    credits = Column(Integer, default=0)

# Создание таблиц
def init_db():
    Base.metadata.create_all(bind=engine)

# Добавить кредиты пользователю

def add_vin_credits_to_user(telegram_user_id: str, quantity: int):
    with SessionLocal() as session:
        user_credits = session.query(VINCredits).filter_by(telegram_user_id=telegram_user_id).first()

        if user_credits:
            user_credits.credits += quantity
        else:
            user_credits = VINCredits(telegram_user_id=telegram_user_id, credits=quantity)
            session.add(user_credits)

        session.commit()

# Списание одного кредита с баланса пользователя

def use_vin_credit(telegram_user_id: str) -> bool:
    with SessionLocal() as session:
        user_credits = session.query(VINCredits).filter_by(telegram_user_id=telegram_user_id).first()

        if user_credits and user_credits.credits > 0:
            user_credits.credits -= 1
            session.commit()
            return True

        return False
