import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
from handlers import pre_fsm, diagnostic, emergency
from services.logger import setup_logging

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Порядок важен: emergency → pre_fsm → diagnostic
    dp.include_router(emergency.router)
    dp.include_router(pre_fsm.router)
    dp.include_router(diagnostic.router)
    
    logger.info("Bot started")
    
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
