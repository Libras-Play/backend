"""
Configuración centralizada de idiomas soportados por la aplicación.

Este módulo define los idiomas de interfaz de usuario que la aplicación soporta.
Para agregar un nuevo idioma, simplemente añádelo a la lista SUPPORTED_LANGUAGES.
"""

from typing import List, Dict

# ============================================================================
# IDIOMAS SOPORTADOS (UI Languages)
# ============================================================================
# Para agregar un nuevo idioma (ej: francés), simplemente agrégalo aquí:
# SUPPORTED_LANGUAGES = ["es", "en", "pt", "fr"]
SUPPORTED_LANGUAGES: List[str] = ["es", "en", "pt"]

# Nombres completos de idiomas (para mensajes de error más descriptivos)
LANGUAGE_NAMES: Dict[str, str] = {
    "es": "Español",
    "en": "English",
    "pt": "Português",
}

# Códigos ISO completos (para referencia)
LANGUAGE_CODES: Dict[str, str] = {
    "es": "es-ES",
    "en": "en-US",
    "pt": "pt-BR",
}


def get_supported_languages() -> List[str]:
    """Retorna la lista de idiomas soportados."""
    return SUPPORTED_LANGUAGES.copy()


def is_valid_language(lang_code: str) -> bool:
    """Verifica si un código de idioma es válido."""
    return lang_code in SUPPORTED_LANGUAGES


def get_language_name(lang_code: str) -> str:
    """Obtiene el nombre completo de un idioma."""
    return LANGUAGE_NAMES.get(lang_code, lang_code)


def get_missing_languages(translations: Dict[str, str]) -> List[str]:
    """
    Retorna la lista de idiomas faltantes en un diccionario de traducciones.
    
    Args:
        translations: Diccionario con traducciones {idioma: texto}
        
    Returns:
        Lista de códigos de idioma faltantes
    """
    if translations is None:
        return SUPPORTED_LANGUAGES.copy()
    
    missing = []
    for lang in SUPPORTED_LANGUAGES:
        if lang not in translations or not translations[lang] or translations[lang].strip() == "":
            missing.append(lang)
    
    return missing


def validate_all_languages_present(translations: Dict[str, str], field_name: str = "field") -> None:
    """
    Valida que todas las traducciones requeridas estén presentes.
    
    Args:
        translations: Diccionario con traducciones {idioma: texto}
        field_name: Nombre del campo (para mensajes de error descriptivos)
        
    Raises:
        ValueError: Si falta algún idioma o alguna traducción está vacía
    """
    missing = get_missing_languages(translations)
    
    if missing:
        missing_names = [get_language_name(lang) for lang in missing]
        raise ValueError(
            f"Field '{field_name}' is missing translations for: {', '.join(missing_names)} ({', '.join(missing)}). "
            f"All supported languages must be provided: {', '.join(SUPPORTED_LANGUAGES)}"
        )
