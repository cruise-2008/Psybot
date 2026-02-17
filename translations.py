translations = {
    "ru": {
        "disclaimer": "⚠️ **Отказ от ответственности**\n\nЭтот бот не является медицинским инструментом. В экстренных ситуациях всегда обращайтесь к специалисту.",
        "agree": "Согласен",
        "s0_prompt": "Опишите вашу ситуацию максимально подробно:",
    },
    "en": {
        "disclaimer": "⚠️ **Disclaimer**\n\nThis bot is not a medical tool. In emergencies, always contact a professional.",
        "agree": "I agree",
        "s0_prompt": "Describe your situation in as much detail as possible:",
    }
}

def get_text(lang, key):
    return translations.get(lang, translations["en"]).get(key, f"Missing key: {key}")
