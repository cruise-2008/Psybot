from aiohttp import web
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def root(request):
    return web.Response(text="PsyCards Bot is active", status=200)

async def health(request):
    return web.Response(text="Bot is running", status=200)

async def start_background_tasks(app):
    """Запуск бота при старте aiohttp"""
    from bot import main as bot_main
    app['bot_task'] = asyncio.create_task(bot_main())
    logger.info("Bot task started")

async def cleanup_background_tasks(app):
    """Остановка бота при завершении"""
    app['bot_task'].cancel()
    await app['bot_task']

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    
    # Запуск и остановка бота вместе с aiohttp
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    web.run_app(app, host="0.0.0.0", port=10000)
