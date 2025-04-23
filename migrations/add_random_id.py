from alembic import op
import sqlalchemy as sa
import random
import string

def upgrade():
    # Добавляем колонку random_id
    op.add_column('users', sa.Column('random_id', sa.String(), nullable=True))
    
    # Создаем индекс для random_id
    op.create_index('ix_users_random_id', 'users', ['random_id'], unique=True)
    
    # Генерируем случайные ID для существующих пользователей
    connection = op.get_bind()
    users = connection.execute("SELECT id FROM users").fetchall()
    
    for user in users:
        random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        connection.execute(
            "UPDATE users SET random_id = %s WHERE id = %s",
            (random_id, user[0])
        )
    
    # Делаем колонку обязательной после заполнения
    op.alter_column('users', 'random_id', nullable=False)

def downgrade():
    # Удаляем индекс
    op.drop_index('ix_users_random_id', table_name='users')
    
    # Удаляем колонку
    op.drop_column('users', 'random_id') 