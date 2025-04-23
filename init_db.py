from app.database import engine, Base, DB_FILE
from app import models
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    # Проверяем, существует ли файл базы данных
    if not DB_FILE.exists():
        logger.info("Создание новой базы данных...")
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("База данных успешно создана!")
    else:
        logger.info("База данных уже существует, пропускаем инициализацию")

if __name__ == "__main__":
    init_db() 