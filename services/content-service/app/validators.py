"""
Validadores dinámicos para schemas de Exercise.
Valida idiomas contra las tablas del sistema.
"""
from typing import Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models


# Cache de idiomas válidos (se actualiza al iniciar la app)
_valid_ui_languages: Set[str] = {"pt-BR", "es-ES", "en-US"}  # Default
_valid_sign_languages: Set[str] = {"LSB", "ASL", "LSM"}  # Default


async def load_valid_languages(db: AsyncSession) -> None:
    """
    Carga dinámicamente los idiomas válidos desde la base de datos.
    Debe llamarse al iniciar la aplicación.
    """
    global _valid_ui_languages, _valid_sign_languages
    
    # Cargar idiomas de UI desde tabla 'languages'
    ui_langs_result = await db.execute(select(models.Language.code))
    ui_langs = ui_langs_result.scalars().all()
    if ui_langs:
        _valid_ui_languages = set(ui_langs)
    
    # Cargar idiomas de señas desde tabla 'sign_languages'
    sign_langs_result = await db.execute(select(models.SignLanguage.code))
    sign_langs = sign_langs_result.scalars().all()
    if sign_langs:
        _valid_sign_languages = set(sign_langs)


def get_valid_ui_languages() -> Set[str]:
    """Retorna el set de idiomas de UI válidos"""
    return _valid_ui_languages


def get_valid_sign_languages() -> Set[str]:
    """Retorna el set de idiomas de señas válidos"""
    return _valid_sign_languages


async def validate_language_exists(db: AsyncSession, language_code: str) -> bool:
    """Valida que un idioma de UI exista en la base de datos"""
    result = await db.execute(
        select(models.Language).where(models.Language.code == language_code)
    )
    return result.scalar_one_or_none() is not None


async def validate_sign_language_exists(db: AsyncSession, sign_language_code: str) -> bool:
    """Valida que un idioma de señas exista en la base de datos"""
    result = await db.execute(
        select(models.SignLanguage).where(models.SignLanguage.code == sign_language_code)
    )
    return result.scalar_one_or_none() is not None
