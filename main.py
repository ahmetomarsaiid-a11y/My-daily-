import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from database import Database
from handlers import register_handlers
from scheduler import setup_scheduler

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
assert TOKEN, "TELEGRAM_BOT_TOKEN not found in environment"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_PATH = os.getenv("DB_PATH", "/app/data/movies.db")
db = Database(DB_PATH)
await db.init_db()

register_handlers(dp, db)

scheduler = setup_scheduler(bot, db)
scheduler.start()

try:
logger.info("Bot started polling")
await dp.start_polling(bot)
finally:
scheduler.shutdown(wait=False)
await bot.session.close()

if __name__ == "__main__":
asyncio.run(main())
