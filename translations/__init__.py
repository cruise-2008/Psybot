from .en import EN_TEXTS
from .ru import RU_TEXTS
from .es import ES_TEXTS
from .fr import FR_TEXTS
from .de import DE_TEXTS

TRANSLATIONS = {
    "en": EN_TEXTS,
    "ru": RU_TEXTS,
    "es": ES_TEXTS,
    "fr": FR_TEXTS,
    "de": DE_TEXTS
}

def get_text(lang, key):
    """Get translated text"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, "")
