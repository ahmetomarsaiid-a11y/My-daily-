import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from dailymotion_api import DailymotionClient

logger = logging.getLogger(__name__)

EMOJI = {
"success": "✅",
"rocket": "🚀",
"movie": "🎥",
"star": "⭐",
"fire": "🔥",
"link": "🔗",
"clock": "⏰",
"heart": "❤️",
"party": "🎉",
"sparkles": "✨",
"target": "🎯",
}

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━"

def setup_scheduler(bot: Bot, db: Database) -> AsyncIOScheduler:
scheduler = AsyncIOScheduler()

async def monitor_job():
logger.info(f"{EMOJI['clock']} Running scheduled monitor job")
requests = await db.get_all_requests()
if not requests:
logger.info("No pending requests")
return

for req in requests:
req_id = req["id"]
user_id = req["user_id"]
title = req["movie_title"]
try:
results = await DailymotionClient.dubbed_search(title, limit=1)
if results:
video = results[0]
notification = (
f"{DIVIDER}\n"
f"{EMOJI['party']} **MATCH FOUND!** {EMOJI['party']}\n"
f"{DIVIDER}\n\n"
f"{EMOJI['movie']} *{video['title']}*\n\n"
f"{EMOJI['link']} [Watch on Dailymotion]({video['url']})\n\n"
f"{DIVIDER}\n"
f"{EMOJI['target']} Matched: *{title}*\n"
f"{EMOJI['star']} Quality: English-Dubbed\n"
f"{EMOJI['heart']} Enjoy watching!"
)
await bot.send_message(
chat_id=user_id,
text=notification,
parse_mode="Markdown",
disable_web_page_preview=False,
)
await db.delete_request(req_id)
logger.info(f"{EMOJI['success']} Notified user {user_id}: '{title}', request #{req_id} deleted")
except Exception as e:
logger.error(f"Error processing request #{req_id}: {e}")

scheduler.add_job(monitor_job, "interval", minutes=60, id="hourly_monitor")
return scheduler
