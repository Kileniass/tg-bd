from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import User, Like, Match
from app.database import SQLALCHEMY_DATABASE_URL

# Инициализация базы данных
engine = create_engine(SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

def clear_database():
    """Очищает все таблицы в базе данных"""
    try:
        # Удаляем все записи из таблиц в правильном порядке (учитывая внешние ключи)
        db.query(Match).delete()
        db.query(Like).delete()
        db.query(User).delete()
        db.commit()
        print("\nБаза данных успешно очищена!")
    except Exception as e:
        db.rollback()
        print(f"\nОшибка при очистке базы данных: {e}")
        # Пробуем альтернативный способ очистки
        try:
            db.execute(text("DELETE FROM match"))
            db.execute(text("DELETE FROM likes"))
            db.execute(text("DELETE FROM users"))
            db.commit()
            print("\nБаза данных успешно очищена альтернативным способом!")
        except Exception as e2:
            db.rollback()
            print(f"\nОшибка при альтернативной очистке базы данных: {e2}")

# Очищаем базу данных
clear_database()

# Закрываем соединение с базой данных
db.close()