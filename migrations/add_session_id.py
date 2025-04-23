from alembic import op
import sqlalchemy as sa
import random
import string

def upgrade():
    # Добавляем колонку session_id
    op.add_column('users', sa.Column('session_id', sa.String(), nullable=True))
    
    # Создаем индекс для session_id
    op.create_index('ix_users_session_id', 'users', ['session_id'], unique=True)
    
    # Генерируем случайные ID для существующих пользователей
    connection = op.get_bind()
    users = connection.execute("SELECT id FROM users").fetchall()
    
    for user in users:
        session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        connection.execute(
            "UPDATE users SET session_id = %s WHERE id = %s",
            (session_id, user[0])
        )
    
    # Делаем колонку обязательной после заполнения
    op.alter_column('users', 'session_id', nullable=False)

def downgrade():
    # Удаляем индекс
    op.drop_index('ix_users_session_id', table_name='users')
    
    # Удаляем колонку
    op.drop_column('users', 'session_id') 