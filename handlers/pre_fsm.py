from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.redis_storage import storage
import logging
logger = logging.getLogger(__name__)
from translations import get_text

router = Router()

# FSM States
class PreFSMStates(StatesGroup):
    language_select = State()
    consent = State()
    initial_problem = State()

# Language selection keyboard
def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es"),
        ],
        [
            InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
            InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"),
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])

# Consent keyboard
def get_consent_keyboard(lang: str):
    consent_text = {
        "en": "✅ I agree",
        "ru": "✅ Согласен",
        "es": "✅ Acepto",
        "fr": "✅ J'accepte",
        "de": "✅ Ich stimme zu"
    }
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=consent_text.get(lang, "✅ I agree"), callback_data="consent_yes")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Старт бота - выбор языка"""
    user_id = message.from_user.id
    
    # Очистка предыдущей сессии
    await storage.clear_session(user_id)
    await state.clear()
    
    logger.info(f"User {user_id} started new session")
    
    await message.answer(
        "Welcome! / Привет! / ¡Hola! / Bonjour! / Hallo!\n\n"
        "Please select your language:",
        reply_markup=get_language_keyboard()
    )
    await state.set_state(PreFSMStates.language_select)

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    user_id = callback.from_user.id
    lang = callback.data.split("_")[1]  # "lang_ru" -> "ru"
    
    # Сохранение языка в сессию
    await storage.create_session(user_id, {"language": lang})
    
    logger.info(f"User {user_id} selected language: {lang}")
    
    # Отправка дисклеймера
    disclaimer = get_text(lang, "disclaimer")
    await callback.message.edit_text(
        disclaimer,
        reply_markup=get_consent_keyboard(lang)
    )
    await state.set_state(PreFSMStates.consent)
    await callback.answer()

@router.callback_query(F.data == "consent_yes")
async def process_consent(callback: CallbackQuery, state: FSMContext):
    """Обработка согласия"""
    user_id = callback.from_user.id
    
    # Получение языка из сессии
    session = await storage.get_session(user_id)
    if not session:
        await callback.message.answer("Session expired. Please /start again")
        return
    
    lang = session.get("language", "en")
    
    logger.info(f"User {user_id} gave consent")
    
    # Отправка инструкции для S0
    instructions = get_text(lang, "instructions")
    await callback.message.edit_text(instructions)
    await state.set_state(PreFSMStates.initial_problem)
    await callback.answer()

@router.message(PreFSMStates.initial_problem)
async def process_initial_problem(message: Message, state: FSMContext):
    """Обработка S0 и запуск диагностики"""
    user_id = message.from_user.id
    s0_text = message.text
    
    logger.info(f"User {user_id} provided S0: {s0_text}")
    
    # Сохранение S0 в сессию
    await storage.update_session(user_id, {"s0": s0_text})
    
    # Запуск диагностики
    from handlers.diagnostic import start_diagnostic
    await start_diagnostic(message, state, s0_text)
