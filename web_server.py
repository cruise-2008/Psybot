from aiohttp import web
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def root(request):
    return web.Response(text="PsyCards Bot is active", status=200)

async def health(request):
    return web.Response(text="Bot is running", status=200)

async def init_app():
    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    
    # Запустить бота в фоне
    from bot import main as bot_main
    asyncio.create_task(bot_main())
    
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)
