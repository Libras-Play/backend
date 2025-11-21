"""
Validadores para campos de traducciones multilenguaje.

Este módulo proporciona validadores Pydantic para asegurar que todos los campos
traducibles tengan traducciones completas en todos los idiomas soportados.
"""

from typing import Dict, Any, Optional
from pydantic import field_validator, model_validator
from app.core.languages import (
    get_supported_languages,
    validate_all_languages_present,
    get_missing_languages,
    get_language_name
)


class TranslationValidatorMixin:
    """
    Mixin para agregar validación de traducciones a modelos Pydantic.
    
    Uso:
        class MyModel(TranslationValidatorMixin, BaseModel):
            title: Dict[str, str]
            description: Dict[str, str]
    """
    
    @staticmethod
    def validate_translation_field(value: Dict[str, str], field_name: str) -> Dict[str, str]:
        """
        Valida que un campo de traducción tenga todos los idiomas requeridos.
        
        Args:
            value: Diccionario de traducciones {idioma: texto}
            field_name: Nombre del campo para mensajes de error
            
        Returns:
            El mismo diccionario si es válido
            
        Raises:
            ValueError: Si falta algún idioma o alguna traducción está vacía
        """
        if value is None:
            raise ValueError(
                f"Field '{field_name}' cannot be null. "
                f"Translations required for: {', '.join(get_supported_languages())}"
            )
        
        if not isinstance(value, dict):
            raise ValueError(
                f"Field '{field_name}' must be a dictionary with language codes as keys"
            )
        
        # Validar que todos los idiomas estén presentes
        validate_all_languages_present(value, field_name)
        
        # Validar que no haya idiomas no soportados
        supported = get_supported_languages()
        extra_langs = set(value.keys()) - set(supported)
        if extra_langs:
            extra_names = [f"{lang} ({get_language_name(lang)})" for lang in extra_langs]
            raise ValueError(
                f"Field '{field_name}' contains unsupported languages: {', '.join(extra_names)}. "
                f"Supported languages are: {', '.join(supported)}"
            )
        
        return value
    
    @staticmethod
    def validate_optional_translation_field(
        value: Optional[Dict[str, str]], 
        field_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Valida un campo de traducción OPCIONAL.
        Si se proporciona, debe tener todos los idiomas.
        Si es null/None, es válido.
        
        Args:
            value: Diccionario de traducciones o None
            field_name: Nombre del campo para mensajes de error
            
        Returns:
            El mismo diccionario si es válido, o None
            
        Raises:
            ValueError: Si se proporciona pero le faltan idiomas
        """
        if value is None:
            return None
        
        # Si se proporciona, debe tener todos los idiomas
        return TranslationValidatorMixin.validate_translation_field(value, field_name)


def create_translation_dict(es: str = "", en: str = "", pt: str = "") -> Dict[str, str]:
    """
    Helper function para crear un diccionario de traducciones válido.
    
    Args:
        es: Texto en español
        en: Texto en inglés
        pt: Texto en portugués
        
    Returns:
        Diccionario con todas las traducciones
        
    Example:
        >>> translations = create_translation_dict(
        ...     es="Alfabeto",
        ...     en="Alphabet",
        ...     pt="Alfabeto"
        ... )
    """
    return {
        "es": es,
        "en": en,
        "pt": pt
    }


def merge_translations(
    existing: Optional[Dict[str, str]], 
    updates: Optional[Dict[str, str]]
) -> Optional[Dict[str, str]]:
    """
    Merge de traducciones existentes con actualizaciones parciales.
    
    Args:
        existing: Traducciones actuales
        updates: Traducciones a actualizar (puede ser parcial)
        
    Returns:
        Diccionario merged con todas las traducciones
        
    Example:
        >>> existing = {"es": "Hola", "en": "Hello", "pt": "Olá"}
        >>> updates = {"es": "Adiós"}
        >>> result = merge_translations(existing, updates)
        >>> result
        {"es": "Adiós", "en": "Hello", "pt": "Olá"}
    """
    if updates is None:
        return existing
    
    if existing is None:
        existing = {}
    
    merged = existing.copy()
    merged.update(updates)
    
    return merged


def expand_to_current_languages(
    obj: Optional[Dict[str, str]], 
    languages: Optional[list] = None
) -> Dict[str, str]:
    """
    Expande un diccionario de traducciones agregando idiomas faltantes con cadena vacía.
    Útil para crear drafts o preparar objetos para completar posteriormente.
    
    Args:
        obj: Diccionario de traducciones existente (puede ser None o parcial)
        languages: Lista de códigos de idioma a incluir (usa SUPPORTED_LANGUAGES si es None)
        
    Returns:
        Diccionario con todos los idiomas, faltantes rellenados con ""
        
    Example:
        >>> partial = {"es": "Hola"}
        >>> result = expand_to_current_languages(partial)
        >>> result
        {"es": "Hola", "en": "", "pt": ""}
    """
    from app.core.languages import get_supported_languages
    
    if languages is None:
        languages = get_supported_languages()
    
    expanded = obj.copy() if obj else {}
    
    for lang in languages:
        if lang not in expanded:
            expanded[lang] = ""
    
    return expanded


def validate_answers_multilanguage(
    answers: Any, 
    exercise_type: str, 
    languages: Optional[list] = None
) -> None:
    """
    Valida la estructura de answers según el tipo de ejercicio y que cada opción
    tenga traducciones completas en todos los idiomas.
    
    Args:
        answers: Objeto AnswersData (para test) o None (para camera)
        exercise_type: Tipo de ejercicio ('test' o 'camera')
        languages: Lista de idiomas requeridos (usa SUPPORTED_LANGUAGES si es None)
        
    Raises:
        ValueError: Si la estructura es inválida o faltan traducciones
        
    Example:
        >>> answers_data = AnswersData(options=[
        ...     AnswerOption(text={"es": "A", "en": "A", "pt": "A"}, correct=True),
        ...     AnswerOption(text={"es": "B", "en": "B", "pt": "B"}, correct=False)
        ... ])
        >>> validate_answers_multilanguage(answers_data, 'test')  # OK
    """
    from app.core.languages import get_supported_languages, validate_all_languages_present
    
    if languages is None:
        languages = get_supported_languages()
    
    if exercise_type == 'test':
        if not answers:
            raise ValueError(
                "Exercise type 'test' requires 'answers' field with structure: "
                "{options: [{text: {...}, correct: bool}]}"
            )
        
        if not hasattr(answers, 'options') or not answers.options:
            raise ValueError("Answers for 'test' exercises must contain 'options' array")
        
        if len(answers.options) < 2:
            raise ValueError("Test exercises require at least 2 answer options")
        
        # Validar que cada opción tenga traducciones completas
        for idx, option in enumerate(answers.options):
            if not hasattr(option, 'text') or not option.text:
                raise ValueError(f"Answer option {idx} is missing 'text' field")
            
            # Validar traducciones completas
            validate_all_languages_present(option.text, f'answers.options[{idx}].text')
        
        # Validar que exactamente una sea correcta
        correct_count = sum(1 for opt in answers.options if opt.correct)
        if correct_count != 1:
            raise ValueError(
                f"Exactly one answer must be marked as correct, found {correct_count}"
            )
    
    elif exercise_type == 'camera':
        # Para camera, answers puede ser None o puede tener una opción descriptiva
        if answers and hasattr(answers, 'options') and answers.options:
            # Si hay opciones, validar traducciones
            for idx, option in enumerate(answers.options):
                if hasattr(option, 'text') and option.text:
                    validate_all_languages_present(option.text, f'answers.options[{idx}].text')


def validate_learning_language(learning_language: str, valid_codes: Optional[list] = None) -> None:
    """
    Valida que un código de lenguaje de señas sea válido.
    
    Args:
        learning_language: Código del lenguaje de señas (ej: "LSB", "ASL", "LSM")
        valid_codes: Lista de códigos válidos (si None, no valida contra lista)
        
    Raises:
        ValueError: Si el código no es válido
        
    Example:
        >>> validate_learning_language("LSB", ["LSB", "ASL", "LSM"])  # OK
        >>> validate_learning_language("LSF", ["LSB", "ASL", "LSM"])  # ValueError
    """
    if not learning_language:
        raise ValueError("learning_language is required")
    
    if valid_codes is not None and learning_language not in valid_codes:
        raise ValueError(
            f"Invalid sign language code: '{learning_language}'. "
            f"Must be one of: {', '.join(valid_codes)}"
        )

