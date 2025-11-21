"""remove_language_id_from_topics

Revision ID: 62404d05e743
Revises: 0006_add_translations
Create Date: 2025-11-16 22:16:43.302590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62404d05e743'
down_revision = '0006_add_translations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Eliminar columna language_id de tabla topics.
    Topics ahora son multilenguaje y no están vinculados a un solo sign_language.
    """
    # Primero eliminar índice si existe
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_topics_sign_language_order') THEN
                DROP INDEX ix_topics_sign_language_order;
            END IF;
        END $$;
    """)
    
    # Eliminar foreign key constraint si existe
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE topics DROP CONSTRAINT IF EXISTS topics_sign_language_id_fkey;
        EXCEPTION
            WHEN undefined_object THEN NULL;
        END $$;
    """)
    
    # Eliminar columna language_id
    op.drop_column('topics', 'language_id')


def downgrade() -> None:
    """No downgrade - Topics multilenguaje es el diseño final"""
    pass
