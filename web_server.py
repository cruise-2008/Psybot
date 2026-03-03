import asyncio
import os
from aiohttp import web
from bot import main as run_bot

async def handle(request):
    return web.Response(text="OK", status=200)

async def main():
    # Запуск порта для Render
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    
    # Твой основной бот
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())
