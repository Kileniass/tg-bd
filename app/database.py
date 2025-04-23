from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Создаем директорию для базы данных
DB_DIR = Path("data")
DB_DIR.mkdir(parents=True, exist_ok=True)

# Используем абсолютный путь для файла базы данных
DB_FILE = DB_DIR / "app.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

# Создаем engine с поддержкой foreign keys
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

