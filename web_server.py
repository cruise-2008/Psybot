import asyncio
import os
from aiohttp import web
from bot import main as run_bot

async def handle(request):
    return web.Response(text="OK", status=200)

async def main():
    app = web.Application()
    # GET автоматически обрабатывает HEAD в aiohttp
    app.router.add_get("/", handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    # Запуск бота
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
