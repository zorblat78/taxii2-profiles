"""Validator package initialiser."""

__all__ = [
    'STIXTemplateValidator',
    'ProfileValidationError',
    'validate',
]

try:
    from .STIXTemplateValidator import STIXTemplateValidator
    from .ProfileValidationError import ProfileValidationError
except ImportError:
    from STIXTemplateValidator import STIXTemplateValidator
    from ProfileValidationError import ProfileValidationError
