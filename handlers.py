import logging
from aiogram import Dispatcher, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import WebAppInfo
from aiogram.enums import ParseMode

from database import Database
from dailymotion_api import DailymotionClient

logger = logging.getLogger(__name__)

# ─── PREMIUM UI CONSTANTS ─────────────────────────────────
# These are "Premium" style multicolored Unicode emojis
PREMIUM_ICONS = {
    "number_1": "1️⃣",
    "number_2": "2️⃣",
    "number_3": "3️⃣",
    "warning": "❗",
    "check": "✅",
    "x_mark": "❌",
    "heart": "🫗", # Using a colorful icon, or 💖
    "money": "💰",
    "cart": "🛒",
    "list": "📑",
    "clock": "⏱️",
    "movie": "🎬",
    "rocket": "🚀",
    "star": "⭐",
    "fire": "🔥",
    "robot": "🤖",
    "shield": "🛡️",
    "target": "🎯",
    "sparkles": "✨",
}

# ─── PREMIUM CARD BUILDER ─────────────────────────────────
def _build_premium_card(results: list, query: str, dubbed: bool = False):
    """
    Generates the "Rexovaan" style card layout.
    Returns: (HTML_Text, Keyboard)
    """
    tag = "🗣️ ENGLISH-DUBBED" if dubbed else "🔎 SEARCH"

    # 1. The Header (Bold and Icon)
    header = (
        f"<b>{PREMIUM_ICONS['movie']} MOVIE TRACKER PRO {PREMIUM_ICONS['movie']}</b>\n"
        f"<i>Your personal Dailymotion scout</i>\n\n"
        f"<b>{tag}</b>\n<b>🔍 {query[:40]}</b>\n"
    )

    # 2. The List (Using 1️⃣, 2️⃣, 3️⃣)
    items_html = []
    buttons = InlineKeyboardBuilder()

    for i, r in enumerate(results):
        # Select the icon based on index (1, 2, 3...)
        num_icon = PREMIUM_ICONS.get(f"number_{i+1}", "🎬")

        title_clean = r['title'][:35]

        # Create the HTML line
        items_html.append(f"{num_icon} <b>{title_clean}</b>")

        # Add the "Watch" button (Inline)
        buttons.button(
            text=f"▶️ Watch: {title_clean}",
            url=r['url']
        )

    # 3. The Footer
    footer = (
        f"\n{PREMIUM_ICONS['fire']} <b>Found: {len(results)} result(s)</b>"
    )

    # Join everything
    final_text = header + "\n\n".join(items_html) + footer

    # Adjust buttons to look nice (2 columns)
    buttons.adjust(2)

    return final_text, buttons.as_markup()

# ─── HANDLERS ─────────────────────────────────────────────

def register_handlers(dp: Dispatcher, db: Database, bot: Bot):

    @dp.message(Command("start", "help"))
    async def cmd_start(message: types.Message):
        # Create the WebApp Menu
        menu_button = ReplyKeyboardBuilder().button(text="📑 Main Menu", web_app=WebAppInfo(url="https://your-website.com")) # You need a real URL here

        welcome_html = (
            f"{PREMIUM_ICONS['rocket']} <b>Welcome to Movie Tracker Pro</b>\n\n"
            f"{PREMIUM_ICONS['check']} <b>Features:</b>\n"
            f"{PREMIUM_ICONS['number_1']} <b>/search</b> — Quick search\n"
            f"{PREMIUM_ICONS['number_2']} <b>/dubbed</b> — English-dubbed only\n"
            f"{PREMIUM_ICONS['number_3']} <b>/request</b> — Track & notify\n\n"
            f"{PREMIUM_ICONS['robot']} <i>Powered by AI</i>"
        )

        # Send reply with menu button
        await message.answer(welcome_html, parse_mode=ParseMode.HTML, reply_markup=menu_button.as_markup(resize_keyboard=True))

    @dp.message(Command("search"))
    async def cmd_search(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{PREMIUM_ICONS['warning']} Usage: <code>/search [title]</code>", parse_mode=ParseMode.HTML)
            return

        query = parts[1].strip()
        await message.reply(f"{PREMIUM_ICONS['number_1']} Searching: <code>{query[:30]}</code>")
        results = await DailymotionClient.search(query, limit=10)

        if not results:
            empty_msg = (
                f"{PREMIUM_ICONS['x_mark']} <b>No Results Found</b>\n"
                f"{PREMIUM_ICONS['fire']} Try a different title."
            )
            await message.reply(empty_msg, parse_mode=ParseMode.HTML)
            return

        card_text, markup = _build_premium_card(results, query, dubbed=False)
        await message.reply(card_text, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)

    @dp.message(Command("dubbed"))
    async def cmd_dubbed(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{PREMIUM_ICONS['warning']} Usage: <code>/dubbed [title]</code>", parse_mode=ParseMode.HTML)
            return

        query = parts[1].strip()
        await message.reply(f"{PREMIUM_ICONS['number_2']} Hunting English-dubbed... <code>{query[:30]}</code> {PREMIUM_ICONS['shield']}")
        results = await DailymotionClient.dubbed_search(query, limit=10)

        if not results:
            empty_msg = (
                f"{PREMIUM_ICONS['x_mark']} <b>No English-Dubbed Results</b>\n"
                f"{PREMIUM_ICONS['fire']} Try a general search."
            )
            await message.reply(empty_msg, parse_mode=ParseMode.HTML)
            return

        card_text, markup = _build_premium_card(results, query, dubbed=True)
        await message.reply(card_text, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)

    @dp.message(Command("list"))
    async def cmd_list(message: types.Message):
        requests = await db.list_requests(message.from_user.id)

        if not requests:
            empty_msg = (
                f"{PREMIUM_ICONS['x_mark']} <b>No Active Requests</b>\n"
                f"{PREMIUM_ICONS['fire']} Use /request to track a movie."
            )
            await message.reply(empty_msg, parse_mode=ParseMode.HTML)
            return

        items_html = []
        buttons = InlineKeyboardBuilder()

        for req in requests:
            req_id, movie_title, ts = req
            short_title = movie_title if len(movie_title) < 25 else movie_title[:22] + "..."

            items_html.append(f"📑 <b>{short_title} #{req_id}</b>")
            buttons.button(text=f"🗑️ Cancel #{req_id}", callback_data=f"cancel_{req_id}")

        builder = ReplyKeyboardBuilder()
        menu_btn = builder.button(text="📑 Menu", web_app=WebAppInfo(url="https://your-website.com"))

        html = (
            f"{PREMIUM_ICONS['list']} <b>Your Tracking List</b>\n"
            f"{PREMIUM_ICONS['robot']} Checked every hour.\n\n"
            f"\n".join(items_html)
        )

        await message.reply(html, parse_mode=ParseMode.HTML, reply_markup=buttons.as_markup())

    @dp.callback_query(lambda c: c.data and c.data.startswith("cancel_"))
    async def cancel_callback(callback: types.CallbackQuery):
        req_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id

        deleted = await db.delete_request(req_id, user_id=user_id)

        if deleted:
            await callback.answer(f"{PREMIUM_ICONS['check']} Request #{req_id} cancelled!", show_alert=False)
            await callback.message.edit_text(f"{PREMIUM_ICONS['check']} <b>Request Removed!</b>", parse_mode=ParseMode.HTML)
        else:
            await callback.answer(f"{PREMIUM_ICONS['x_mark']} Error or not yours!", show_alert=True)

    @dp.message(Command("request"))
    async def cmd_request(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{PREMIUM_ICONS['warning']} Usage: <code>/request [title]</code>", parse_mode=ParseMode.HTML)
            return

        title = parts[1].strip()
        req_id = await db.add_request(message.from_user.id, title)

        success_html = (
            f"{PREMIUM_ICONS['check']} <b>REQUEST ADDED</b>\n\n"
            f"{PREMIUM_ICONS['movie']} {title}\n"
            f"{PREMIUM_ICONS['target']} ID: <code>#{req_id}</code>\n"
            f"{PREMIUM_ICONS['clock']} Auto-check: Every 60 min\n\n"
            f"{PREMIUM_ICONS['robot']} I'll notify you when it's available!"
        )
        await message.reply(success_html, parse_mode=ParseMode.HTML)

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: types.Message):
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply(f"{PREMIUM_ICONS['warning']} Usage: <code>/cancel [id]</code>\n{PREMIUM_ICONS['list']} Find IDs with /list", parse_mode=ParseMode.HTML)
            return

        req_id = int(parts[1])
        deleted = await db.delete_request(req_id, user_id=message.from_user.id)

        if deleted:
            await message.reply(f"{PREMIUM_ICONS['check']} Request <code>#{req_id}</code> trashed! {PREMIUM_ICONS['x_mark']}", parse_mode=ParseMode.HTML)
        else:
            await message.reply(f"{PREMIUM_ICONS['x_mark']} Request <code>#{req_id}</code> not found.", parse_mode=ParseMode.HTML)
