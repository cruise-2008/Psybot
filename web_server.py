from aiohttp import web
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def root(request):
    return web.Response(text="PsyCards Bot is active", status=200)

async def health(request):
    return web.Response(text="Bot is running", status=200)

async def start_bot():
    from bot import main as bot_main
    await bot_main()

if __name__ == "__main__":
    app = web.Application()
    # aiohttp автоматически обрабатывает HEAD для GET endpoints
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.create_task(start_bot())
    
    web.run_app(app, host="0.0.0.0", port=10000)
