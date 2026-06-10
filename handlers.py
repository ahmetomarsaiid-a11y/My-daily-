import logging
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from database import Database
from dailymotion_api import DailymotionClient

logger = logging.getLogger(__name__)

# ──────── Cool UI Constants ─────────────────────────────────
EMOJI = {
    "logo": "🎬",
    "search": "🔍",
    "dubbed": "🗣️",
    "request": "📌",
    "list": "📋",
    "cancel": "❌",
    "trash": "🗑️",
    "success": "✅",
    "fail": "❌",
    "warning": "⚠️",
    "clock": "⏳",
    "movie": "🎥",
    "star": "⭐",
    "fire": "🔥",
    "robot": "🤖",
    "rocket": "🚀",
    "link": "🔗",
    "shield": "🛡️",
    "globe": "🌐",
    "target": "🎯",
    "heart": "❤️",
    "sparkles": "✨",
    "magnifier": "🔎",
    "notification": "🔔",
}

WELCOME_CARD = (
    f"{EMOJI['logo']} **MOVIE TRACKER PRO** {EMOJI['logo']}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"{EMOJI['rocket']} *Your personal Dailymotion scout*\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    f"{EMOJI['search']} **/search** `<title>` — Quick search\n"
    f"{EMOJI['dubbed']} **/dubbed** `<title>` — English-dubbed only\n"
    f"{EMOJI['request']} **/request** `<title>` — Track & notify\n"
    f"{EMOJI['list']} **/list** — Manage your requests\n"
    f"{EMOJI['trash']} **/cancel** `<id>` — Remove a request\n\n"
    f"{EMOJI['clock']} *Hourly auto-check is active*"
)

DIVIDER = "──────────────────────"
HEADER_BAR = "▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸"

def _build_result_card(results: list, query: str, dubbed: bool = False) -> str:
    tag = f"{EMOJI['dubbed']} ENGLISH-DUBBED" if dubbed else f"{EMOJI['search']} SEARCH"
    header = (
        f"{HEADER_BAR}\n"
        f" {tag}\n"
        f" {EMOJI['magnifier']} *{query[:40]}*\n"
        f"{HEADER_BAR}\n\n"
    )
    cards = []
    for i, r in enumerate(results):
        title_clean = r['title'][:55] + ("..." if len(r['title']) > 55 else "")
        card = (
            f"{EMOJI['star']} **#{i+1}** [{title_clean}]({r['url']})\n"
            f" {EMOJI['link']} `...{r['id'][-12:]}`"
        )
        cards.append(card)
    footer = f"\n{DIVIDER}\n{EMOJI['fire']} Found: **{len(results)}** result(s)"
    return header + "\n\n".join(cards) + footer

def _empty_state(emoji: str, message: str) -> str:
    return (
        f"{EMOJI['warning']} {emoji} {EMOJI['warning']}\n"
        f"{DIVIDER}\n"
        f"{message}"
    )

def register_handlers(dp: Dispatcher, db: Database):
    @dp.message(Command("start", "help"))
    async def cmd_start(message: types.Message):
        await message.answer(WELCOME_CARD, parse_mode=ParseMode.MARKDOWN)

    @dp.message(Command("search"))
    async def cmd_search(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{EMOJI['warning']} Usage: `/search <title>`", parse_mode=ParseMode.MARKDOWN)
            return
        query = parts[1].strip()
        await message.reply(f"{EMOJI['magnifier']} Searching... `{query[:30]}`")
        results = await DailymotionClient.search(query, limit=5)
        if not results:
            await message.reply(_empty_state(EMOJI['search'], f"No results for *{query}*"), parse_mode=ParseMode.MARKDOWN)
            return
        await message.reply(_build_result_card(results, query, dubbed=False), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    @dp.message(Command("dubbed"))
    async def cmd_dubbed(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{EMOJI['warning']} Usage: `/dubbed <title>`", parse_mode=ParseMode.MARKDOWN)
            return
        query = parts[1].strip()
        await message.reply(f"{EMOJI['magnifier']} Hunting English-dubbed... `{query[:30]}` {EMOJI['shield']}")
        results = await DailymotionClient.dubbed_search(query, limit=5)
        if not results:
            await message.reply(_empty_state(EMOJI['dubbed'], f"No English-dubbed results for *{query}*\nTry a broader search with /search"), parse_mode=ParseMode.MARKDOWN)
            return
        await message.reply(_build_result_card(results, query, dubbed=True), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    @dp.message(Command("request"))
    async def cmd_request(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(f"{EMOJI['warning']} Usage: `/request <title>`", parse_mode=ParseMode.MARKDOWN)
            return
        title = parts[1].strip()
        req_id = await db.add_request(message.from_user.id, title)
        success_card = (
            f"{DIVIDER}\n"
            f"{EMOJI['success']} **REQUEST ADDED** {EMOJI['success']}\n"
            f"{DIVIDER}\n\n"
            f"{EMOJI['movie']} *{title}*\n"
            f"{EMOJI['target']} ID: `#{req_id}`\n"
            f"{EMOJI['clock']} Checked every **60 minutes**\n"
            f"{EMOJI['notification']} You'll be notified instantly!\n\n"
            f"{DIVIDER}"
        )
        await message.reply(success_card, parse_mode=ParseMode.MARKDOWN)

    @dp.message(Command("list"))
    async def cmd_list(message: types.Message):
        requests = await db.list_requests(message.from_user.id)
        if not requests:
            empty_card = (
                f"{DIVIDER}\n"
                f"{EMOJI['warning']} {EMOJI['list']} NO ACTIVE REQUESTS {EMOJI['warning']}\n"
                f"{DIVIDER}\n\n"
                f"Use {EMOJI['request']} `/request <title>` to add one!\n"
                f"{EMOJI['robot']} I'll check every hour for you."
            )
            await message.reply(empty_card, parse_mode=ParseMode.MARKDOWN)
            return
        builder = InlineKeyboardBuilder()
        for req in requests:
            req_id, movie_title, ts = req
            short_title = movie_title if len(movie_title) < 28 else movie_title[:25] + "..."
            builder.button(text=f"{EMOJI['trash']} {short_title} #{req_id}", callback_data=f"cancel_{req_id}")
        builder.adjust(1)
        header = (
            f"{HEADER_BAR}\n"
            f" {EMOJI['list']} YOUR TRACKING LIST {EMOJI['list']}\n"
            f"{HEADER_BAR}\n\n"
            f"{EMOJI['sparkles']} **{len(requests)} active request(s)**\n"
            f"{EMOJI['clock']} Auto-check: every 60 min\n\n"
            f"{EMOJI['target']} Tap a button to cancel:"
        )
        await message.reply(header, parse_mode=ParseMode.MARKDOWN, reply_markup=builder.as_markup())

    @dp.callback_query(lambda c: c.data and c.data.startswith("cancel_"))
    async def cancel_callback(callback: types.CallbackQuery):
        req_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        deleted = await db.delete_request(req_id, user_id=user_id)
        if deleted:
            await callback.answer(f"{EMOJI['success']} Request #{req_id} cancelled!", show_alert=False)
            requests = await db.list_requests(user_id)
            if not requests:
                cleaned_card = (
                    f"{DIVIDER}\n"
                    f"{EMOJI['success']} ALL CLEAR! {EMOJI['success']}\n"
                    f"{DIVIDER}\n\n"
                    f"{EMOJI['sparkles']} No more pending requests.\n"
                    f"Use /request to add new ones!"
                )
                await callback.message.edit_text(cleaned_card, parse_mode=ParseMode.MARKDOWN)
                return
            builder = InlineKeyboardBuilder()
            for req in requests:
                rid, title, ts = req
                short_title = title if len(title) < 28 else title[:25] + "..."
                builder.button(text=f"{EMOJI['trash']} {short_title} #{rid}", callback_data=f"cancel_{rid}")
            builder.adjust(1)
            await callback.message.edit_text(
                f"{EMOJI['list']} **{len(requests)} request(s)** remaining:\n{EMOJI['target']} Tap to cancel:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=builder.as_markup(),
            )
        else:
            await callback.answer(f"{EMOJI['fail']} Already removed or not yours!", show_alert=True)

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: types.Message):
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply(f"{EMOJI['warning']} Usage: `/cancel <request_id>`\n{EMOJI['target']} Find IDs with /list", parse_mode=ParseMode.MARKDOWN)
            return
        req_id = int(parts[1])
        deleted = await db.delete_request(req_id, user_id=message.from_user.id)
        if deleted:
            await message.reply(f"{EMOJI['success']} Request `#{req_id}` trashed! {EMOJI['trash']}", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply(f"{EMOJI['fail']} Couldn't find request `#{req_id}`.\nUse /list to see your active requests.", parse_mode=ParseMode.MARKDOWN)
