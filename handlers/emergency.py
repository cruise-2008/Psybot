from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import logging
logger = logging.getLogger(__name__)

from services.redis_storage import storage
from services.logger import log_emergency

router = Router()

EMERGENCY_CONTACTS = """
🆘 ВАЖНО: Если вам нужна немедленная помощь

🌍 Международная поддержка:
- Befrienders Worldwide: befrienders.org

📞 Горячие линии:
🇺🇸 USA: 988
🇬🇧 UK: 116 123
🇪🇺 EU: 116 123
🇷🇺 Russia: 8-800-2000-122
🇪🇸 Spain: 024
🇺🇦 Ukraine: 7333
🇨🇦 Canada: 1-833-456-4566
🇦🇺 Australia: 13 11 14

Помощь доступна 24/7. Вы не одни.
"""

CONTINUE_MESSAGES = {
    "ru": "\n\nКогда будете готовы, можете продолжить. Отправьте ваш ответ на предыдущий вопрос.",
    "en": "\n\nWhen you're ready, you can continue. Send your answer to the previous question.",
    "es": "\n\nCuando esté listo, puede continuar. Envíe su respuesta a la pregunta anterior.",
    "fr": "\n\nQuand vous serez prêt, vous pouvez continuer. Envoyez votre réponse à la question précédente.",
    "de": "\n\nWenn Sie bereit sind, können Sie fortfahren. Senden Sie Ihre Antwort auf die vorherige Frage."
}

async def handle_emergency(message: Message, state: FSMContext, emergency_data: dict):
    user_id = message.from_user.id
    emergency_code = emergency_data.get("emergency_code", "UNKNOWN")
    trigger = emergency_data.get("detected_trigger", "")
    language = emergency_data.get("user_language", "en")
    
    log_emergency(user_id, emergency_code, trigger, language)
    
    logger.warning(f"EMERGENCY DETECTED - User {user_id} | Code: {emergency_code} | Trigger: {trigger[:50]}")
    
    # Показываем контакты
    continue_msg = CONTINUE_MESSAGES.get(language, CONTINUE_MESSAGES["en"])
    await message.answer(EMERGENCY_CONTACTS + continue_msg)
    
    # НЕ завершаем сессию - пользователь может продолжить
    # Сессия и state остаются активными
