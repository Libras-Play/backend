"""add_img_url_and_learning_language

Revision ID: fc5e0716f0cc
Revises: 62404d05e743
Create Date: 2025-11-17 00:11:14.114633

Agrega:
1. Columna img_url (nullable) a la tabla topics
2. Columna learning_language (NOT NULL con FK) a la tabla exercises
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc5e0716f0cc'
down_revision = '62404d05e743'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Crear tabla sign_languages si no existe
    # Verificamos primero si existe para evitar errores
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'sign_languages' not in existing_tables:
        op.create_table(
            'sign_languages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=10), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('country', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('flag_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_sign_languages_id', 'sign_languages', ['id'])
        op.create_index('ix_sign_languages_code', 'sign_languages', ['code'], unique=True)
        
        # Poblar con datos iniciales
        op.execute("""
            INSERT INTO sign_languages (code, name, country, description) VALUES
            ('LSB', 'Língua Brasileira de Sinais (Libras)', 'Brasil', 'Lenguaje de señas oficial de Brasil'),
            ('ASL', 'American Sign Language', 'Estados Unidos', 'Lenguaje de señas americano'),
            ('LSM', 'Lengua de Señas Mexicana', 'México', 'Lenguaje de señas oficial de México'),
            ('AUSLAN', 'Australian Sign Language', 'Australia', 'Lenguaje de señas australiano')
        """)
    
    # 2. Agregar img_url a topics (nullable)
    op.add_column('topics', sa.Column('img_url', sa.String(length=500), nullable=True))
    
    # 3. Agregar learning_language a exercises
    # Primero agregar columna como nullable con valor default temporal
    op.add_column('exercises', sa.Column('learning_language', sa.String(length=10), nullable=True))
    
    # 4. Actualizar ejercicios existentes con un valor por defecto (LSB - Libras Brasileño)
    # Esto es seguro porque asumimos que los ejercicios existentes son de LSB
    op.execute("UPDATE exercises SET learning_language = 'LSB' WHERE learning_language IS NULL")
    
    # 5. Ahora hacer la columna NOT NULL
    op.alter_column('exercises', 'learning_language', nullable=False)
    
    # 6. Crear índice para learning_language
    op.create_index('ix_exercises_learning_language', 'exercises', ['learning_language'])
    
    # 7. Agregar Foreign Key constraint a sign_languages.code
    op.create_foreign_key(
        'fk_exercises_learning_language',
        'exercises', 
        'sign_languages',
        ['learning_language'], 
        ['code'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    # Eliminar FK constraint
    op.drop_constraint('fk_exercises_learning_language', 'exercises', type_='foreignkey')
    
    # Eliminar índice
    op.drop_index('ix_exercises_learning_language', 'exercises')
    
    # Eliminar columnas
    op.drop_column('exercises', 'learning_language')
    op.drop_column('topics', 'img_url')
    
    # Nota: NO eliminamos la tabla sign_languages en downgrade
    # porque podría estar siendo usada por otras tablas en el futuro

