from alembic.config import Config
from alembic import command
import os

def apply_migration():
    # Получаем путь к директории с миграциями
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    
    # Создаем конфигурацию Alembic
    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', migrations_dir)
    alembic_cfg.set_main_option('sqlalchemy.url', 'sqlite:///./app.db')
    
    # Применяем миграцию
    command.upgrade(alembic_cfg, 'head')
    print("Миграция успешно применена")

if __name__ == '__main__':
    apply_migration() 