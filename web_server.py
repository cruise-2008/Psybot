from aiohttp import web
import asyncio
import logging
from bot import main as bot_main

logger = logging.getLogger(__name__)

async def health(request):
    return web.Response(text="Bot is running")

async def start_bot(app):
    asyncio.create_task(bot_main())

app = web.Application()
app.router.add_get('/health', health)
app.on_startup.append(start_bot)

if __name__ == '__main__':
    web.run_app(app, port=10000)
