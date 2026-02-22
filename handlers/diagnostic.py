from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import logging
logger = logging.getLogger(__name__)

from services.llm_client import llm_client
from services.redis_storage import storage
from services.logger import log_verdict

router = Router()

class DiagnosticStates(StatesGroup):
    s1 = State()
    s2 = State()
    s3 = State()
    decision_point = State()
    s4 = State()
    s5 = State()
    s6 = State()

ERROR_MESSAGES = {
    "ru": "Произошла ошибка. Попробуйте /start",
    "en": "An error occurred. Try /start",
    "es": "Ocurrió un error. Intente /start",
    "fr": "Une erreur s'est produite. Essayez /start",
    "de": "Ein Fehler ist aufgetreten. Versuchen Sie /start"
}

SESSION_ENDED_MESSAGES = {
    "ru": "Сессия завершена. Используйте /start для новой консультации.",
    "en": "Session ended. Use /start for a new consultation.",
    "es": "Sesión finalizada. Use /start para una nueva consulta.",
    "fr": "Session terminée. Utilisez /start pour une nouvelle consultation.",
    "de": "Sitzung beendet. Verwenden Sie /start für eine neue Beratung."
}

def format_question_with_options(question: str, options: list, question_num: int, total: int = 3, language: str = "ru") -> str:
    prompts = {
        "ru": f"💬 Напишите номер (1-{len(options)}) и/или свой ответ:",
        "en": f"💬 Write number (1-{len(options)}) and/or your answer:",
        "es": f"💬 Escriba el número (1-{len(options)}) y/o su respuesta:",
        "fr": f"💬 Écrivez le numéro (1-{len(options)}) et/ou votre réponse:",
        "de": f"💬 Schreiben Sie die Nummer (1-{len(options)}) und/oder Ihre Antwort:"
    }
    decision_prompts = {
        "ru": "💬 Напишите номер (1-2):",
        "en": "💬 Write number (1-2):",
        "es": "💬 Escriba el número (1-2):",
        "fr": "💬 Écrivez le numéro (1-2):",
        "de": "💬 Schreiben Sie die Nummer (1-2):"
    }
    question_labels = {
        "ru": f"Вопрос {question_num}/{total}:",
        "en": f"Question {question_num}/{total}:",
        "es": f"Pregunta {question_num}/{total}:",
        "fr": f"Question {question_num}/{total}:",
        "de": f"Frage {question_num}/{total}:"
    }
    formatted_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    if question_num == 0:
        prompt = decision_prompts.get(language, decision_prompts["en"])
        return f"{question}\n\n{formatted_options}\n\n{prompt}"
    prompt = prompts.get(language, prompts["en"])
    label = question_labels.get(language, question_labels["en"])
    return f"{label}\n{question}\n\n{formatted_options}\n\n{prompt}"

def map_input_to_option(user_input: str, options: list) -> str:
    user_input = user_input.strip()
    if user_input and user_input[0].isdigit():
        idx = int(user_input[0]) - 1
        if 0 <= idx < len(options):
            if len(user_input) == 1:
                return options[idx]
            elif len(user_input) > 1 and user_input[1] == ' ':
                additional_text = user_input[2:].strip()
                return f"{options[idx]}. {additional_text}"
    return user_input

async def start_diagnostic(message: Message, state: FSMContext, s0_text: str):
    user_id = message.from_user.id
    try:
        session = await storage.get_session(user_id)
        if not session:
            await message.answer("Сессия истекла. Используйте /start")
            return
        lang = session.get("language", "en")
        await storage.add_to_history(user_id, {"role": "user", "content": s0_text})
        llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id)
            await state.clear()
            return
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response)
            return
        if "options" not in llm_response:
            logger.error(f"RC-1 missing options: {llm_response}")
            await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
            return
        await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
        await storage.update_session(user_id, {"last_response": llm_response})
        question_text = format_question_with_options(
            llm_response["question"], llm_response["options"], question_num=1, language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s1)
        logger.info(f"User {user_id} started diagnostic with S1")
    except Exception as e:
        logger.error(f"Error in start_diagnostic: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

@router.message(DiagnosticStates.s1)
async def handle_s1(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        session = await storage.get_session(user_id)
        if not session:
            await message.answer("Сессия истекла. Используйте /start")
            return
        lang = session.get("language", "en")
        options = session.get("last_response", {}).get("options", [])
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id); await state.clear(); return
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response); return
        if "options" not in llm_response:
            logger.error(f"RC-1 missing options: {llm_response}")
            await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
            return
        await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
        await storage.update_session(user_id, {"last_response": llm_response})
        question_text = format_question_with_options(
            llm_response["question"], llm_response["options"], question_num=2, language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s2)
    except Exception as e:
        logger.error(f"Error in handle_s1: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

@router.message(DiagnosticStates.s2)
async def handle_s2(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        options = session.get("last_response", {}).get("options", [])
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id); await state.clear(); return
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response); return
        if "options" not in llm_response:
            logger.error(f"RC-1 missing options: {llm_response}")
            await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
            return
        await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
        await storage.update_session(user_id, {"last_response": llm_response})
        question_text = format_question_with_options(
            llm_response["question"], llm_response["options"], question_num=3, language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.s3)
    except Exception as e:
        logger.error(f"Error in handle_s2: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

@router.message(DiagnosticStates.s3)
async def handle_s3(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        options = session.get("last_response", {}).get("options", [])
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        decision_request = "Now provide ONLY the decision point with exactly 2 options: deep analysis or show result."
        await storage.add_to_history(user_id, {"role": "user", "content": decision_request})
        llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id); await state.clear(); return
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response); return
        if llm_response.get("type") not in ["RC-1", "decision_point"]:
            logger.warning(f"Unexpected type after S3: {llm_response.get('type')}")
            llm_response["type"] = "RC-1"
        if "question" not in llm_response or len(llm_response.get("options", [])) != 2:
            logger.warning(f"LLM skipped decision point, forcing manually")
            decision_options_map = {
                "ru": ["Глубокий анализ (3 дополнительных вопроса)", "Показать результат сейчас"],
                "en": ["Deep analysis (3 additional questions)", "Show result now"],
                "es": ["Análisis profundo (3 preguntas adicionales)", "Mostrar resultado ahora"],
                "fr": ["Analyse approfondie (3 questions supplémentaires)", "Afficher le résultat maintenant"],
                "de": ["Tiefenanalyse (3 zusätzliche Fragen)", "Ergebnis jetzt anzeigen"]
            }
            decision_question_map = {
                "ru": "Анализ завершен.",
                "en": "Analysis complete.",
                "es": "Análisis completo.",
                "fr": "Analyse terminée.",
                "de": "Analyse abgeschlossen."
            }
            llm_response = {
                "type": "RC-1",
                "question": decision_question_map.get(lang, decision_question_map["en"]),
                "options": decision_options_map.get(lang, decision_options_map["en"])
            }
        await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
        await storage.update_session(user_id, {"last_response": llm_response})
        question_text = format_question_with_options(
            llm_response["question"], llm_response["options"], question_num=0, language=lang
        )
        await message.answer(question_text)
        await state.set_state(DiagnosticStates.decision_point)
    except Exception as e:
        logger.error(f"Error in handle_s3: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

@router.message(DiagnosticStates.decision_point)
async def handle_decision(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text.strip() not in ["1", "2"]:
        return
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        options = session.get("last_response", {}).get("options", [])
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        if "1" in message.text:
            llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
            if llm_response.get("type") == "RATE_LIMIT_ERROR":
                await message.answer(llm_response["message"])
                await storage.clear_session(user_id); await state.clear(); return
            if llm_response.get("type") == "RC-3":
                from handlers.emergency import handle_emergency
                await handle_emergency(message, state, llm_response); return
            if "options" not in llm_response:
                logger.error(f"RC-1 missing options: {llm_response}")
                await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
                return
            await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
            await storage.update_session(user_id, {"last_response": llm_response})
            question_text = format_question_with_options(
                llm_response["question"], llm_response["options"], question_num=4, total=6, language=lang
            )
            await message.answer(question_text)
            await state.set_state(DiagnosticStates.s4)
        else:
            llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
            if llm_response.get("type") == "RATE_LIMIT_ERROR":
                await message.answer(llm_response["message"])
                await storage.clear_session(user_id); await state.clear(); return
            if llm_response.get("type") == "RC-3":
                from handlers.emergency import handle_emergency
                await handle_emergency(message, state, llm_response); return
            if llm_response.get("type") == "RC-2":
                await send_verdict(message, state, llm_response, user_id, lang)
    except Exception as e:
        logger.error(f"Error in handle_decision: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

@router.message(DiagnosticStates.s4)
@router.message(DiagnosticStates.s5)
@router.message(DiagnosticStates.s6)
async def handle_deep_analysis(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    state_map = {
        "DiagnosticStates:s4": (4, DiagnosticStates.s5),
        "DiagnosticStates:s5": (5, DiagnosticStates.s6),
        "DiagnosticStates:s6": (6, None)
    }
    question_num, next_state = state_map.get(current_state, (4, None))
    try:
        session = await storage.get_session(user_id)
        lang = session.get("language", "en")
        options = session.get("last_response", {}).get("options", [])
        user_answer = map_input_to_option(message.text, options)
        await storage.add_to_history(user_id, {"role": "user", "content": user_answer})
        llm_response = await llm_client.get_response(await storage.get_history(user_id), lang)
        if llm_response.get("type") == "RATE_LIMIT_ERROR":
            await message.answer(llm_response["message"])
            await storage.clear_session(user_id); await state.clear(); return
        if llm_response.get("type") == "RC-3":
            from handlers.emergency import handle_emergency
            await handle_emergency(message, state, llm_response); return
        
        # Проверить тип ответа
        if llm_response.get("type") == "RC-2":
            # Это финальный вердикт
            if "content" not in llm_response:
                logger.error(f"RC-2 missing content: {llm_response}")
                await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
                return
            await send_verdict(message, state, llm_response, user_id, lang)
        elif llm_response.get("type") == "RC-1":
            # Это следующий вопрос
            if "question" not in llm_response or "options" not in llm_response:
                logger.error(f"RC-1 missing fields: {llm_response}")
                await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
                return
            
            # Если это был последний вопрос (S6) - должен быть RC-2
            if next_state is None:
                logger.warning(f"Got RC-1 after S6, requesting final verdict")
                await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
                await storage.add_to_history(user_id, {"role": "user", "content": map_input_to_option("1", llm_response["options"])})
                # Запросить RC-2
                final_response = await llm_client.get_response(await storage.get_history(user_id), lang)
                if final_response.get("type") == "RC-2" and "content" in final_response:
                    await send_verdict(message, state, final_response, user_id, lang)
                else:
                    await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
                return
            
            # Иначе продолжаем опрос
            await storage.add_to_history(user_id, {"role": "assistant", "content": llm_response["question"]})
            await storage.update_session(user_id, {"last_response": llm_response})
            question_text = format_question_with_options(
                llm_response["question"], llm_response["options"],
                question_num=question_num + 1, total=6, language=lang
            )
            await message.answer(question_text)
            await state.set_state(next_state)
        else:
            logger.error(f"Unexpected response in deep analysis: {llm_response.get('type')}")
            await message.answer(ERROR_MESSAGES.get(lang, ERROR_MESSAGES["en"]))
    except Exception as e:
        logger.error(f"Error in handle_deep_analysis: {e}")
        session = await storage.get_session(user_id) or {}
        await message.answer(ERROR_MESSAGES.get(session.get("language", "en"), ERROR_MESSAGES["en"]))

async def send_verdict(message: Message, state: FSMContext, verdict: dict, user_id: int, language: str):
    log_verdict(user_id, verdict.get("pattern_label", "Unknown"), language)
    
    text = verdict.get("content", "Анализ недоступен")
    
    MAX_LENGTH = 4000
    
    if len(text) <= MAX_LENGTH:
        await message.answer(text, parse_mode="Markdown")
    else:
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > MAX_LENGTH:
                if current_part:
                    parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        for i, part in enumerate(parts):
            if i == 0:
                await message.answer(part, parse_mode="Markdown")
            else:
                await message.answer(f"_(продолжение {i+1})_\n\n{part}", parse_mode="Markdown")
    
    await storage.clear_session(user_id)
    await state.clear()
    end_msg = SESSION_ENDED_MESSAGES.get(language, SESSION_ENDED_MESSAGES["en"])
    await message.answer(end_msg)
