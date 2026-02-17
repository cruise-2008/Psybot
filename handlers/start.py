from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.redis_storage import storage
import handlers.diagnostic as diagnostic

router = Router()

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
    },
    "es": { "disclaimer": "⚠️ **Descargo de responsabilidad**", "agree": "Acepto", "s0_prompt": "Describa..." },
    "fr": { "disclaimer": "⚠️ **Avertissement**", "agree": "D'accord", "s0_prompt": "Décrivez..." },
    "de": { "disclaimer": "⚠️ **Haftungsausschluss**", "agree": "Einverstanden", "s0_prompt": "Beschreiben..." }
}

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"),
         InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en")],
        [InlineKeyboardButton(text="Español 🇪🇸", callback_data="lang_es"),
         InlineKeyboardButton(text="Français 🇫🇷", callback_data="lang_fr")],
        [InlineKeyboardButton(text="Deutsch 🇩🇪", callback_data="lang_de")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    storage.clear_session(message.from_user.id)
    await message.answer("Select language / Выберите язык:", reply_markup=get_lang_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    content = translations.get(lang, translations["en"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=content["agree"], callback_data="agree")]
    ])
    
    await callback.message.edit_text(content["disclaimer"], reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "agree")
async def process_agreement(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    content = translations.get(lang, translations["en"])
    await callback.message.edit_text(content["s0_prompt"])
    await state.set_state("S0")
    await callback.answer()

@router.message(F.text, lambda message: any(state == "S0" for state in ["S0"]))
async def handle_s0(message: Message, state: FSMContext):
    await state.update_data(s0=message.text)
    await diagnostic.start_diagnostic(message, state)
