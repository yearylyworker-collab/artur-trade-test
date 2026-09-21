import asyncio
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SIGNAL_CHANNEL_ID = os.environ["SIGNAL_CHANNEL_ID"]
TIMEZONE = os.getenv("TIMEZONE", "Europe/Prague")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
ROOT = Path(__file__).resolve().parent

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

last_channel_message_id: int | None = None


def now_text() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M:%S")


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in ADMIN_IDS)


def panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Анализ", callback_data="demo:analysis")],
        [
            InlineKeyboardButton(text="🟢 BUY", callback_data="demo:buy"),
            InlineKeyboardButton(text="🔴 SELL", callback_data="demo:sell"),
        ],
        [
            InlineKeyboardButton(text="✅ WIN", callback_data="demo:win"),
            InlineKeyboardButton(text="❌ LOSS", callback_data="demo:loss"),
        ],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="demo:stats")],
    ])


async def send_photo(filename: str, caption: str):
    return await bot.send_photo(
        SIGNAL_CHANNEL_ID,
        FSInputFile(ROOT / filename),
        caption=caption,
        parse_mode="HTML",
    )


async def edit_photo(filename: str, caption: str):
    global last_channel_message_id
    if not last_channel_message_id:
        await publish_analysis()
        return
    await bot.edit_message_media(
        chat_id=SIGNAL_CHANNEL_ID,
        message_id=last_channel_message_id,
        media=InputMediaPhoto(
            media=FSInputFile(ROOT / filename),
            caption=caption,
            parse_mode="HTML",
        ),
    )


async def publish_analysis():
    global last_channel_message_id
    caption = (
        "🔎 <b>ARTUR TRADE | АНАЛИЗ РЫНКА</b>\n\n"
        "Система проверяет доступные пары, структуру M1 и направление движения.\n"
        "Слабые ситуации пропускаются — ждём подтверждение.\n\n"
        f"🕐 {now_text()}"
    )
    msg = await send_photo("analysis.jpg", caption)
    last_channel_message_id = msg.message_id


async def publish_signal(direction: str):
    direction = direction.upper()
    icon = "🟢" if direction == "BUY" else "🔴"
    filename = "buy.jpg" if direction == "BUY" else "sell.jpg"
    caption = (
        "📡 <b>ARTUR TRADE | СИГНАЛ ПОДТВЕРЖДЁН</b>\n\n"
        "<b>EUR/USD OTC</b>\n"
        f"{icon} Направление: <b>{direction}</b>\n"
        f"🕐 Вход: <b>{now_text()}</b>\n"
        "⏳ Длительность сделки: <b>5 сек</b>\n"
        "📊 Таймфрейм: <b>M1</b>\n\n"
        "🧪 DEMO — проверяем только внешний вид и механику публикации."
    )
    await edit_photo(filename, caption)


async def publish_result(status: str):
    result = "✅ <b>WIN</b>" if status.upper() == "WIN" else "❌ <b>LOSS</b>"
    caption = (
        "📊 <b>ARTUR TRADE | РЕЗУЛЬТАТ СИГНАЛА</b>\n\n"
        "<b>EUR/USD OTC</b>\n"
        f"Результат: {result}\n"
        f"🕐 Закрытие: <b>{now_text()}</b>\n"
        "🔁 Повторы: <b>0</b>\n\n"
        "🧪 DEMO — результат выбирается вручную."
    )
    await edit_photo("result.jpg", caption)


async def publish_stats():
    caption = (
        "📈 <b>ARTUR TRADE | СТАТИСТИКА</b>\n\n"
        "Сегодня: DEMO\n"
        "✅ WIN: <b>—</b>\n"
        "❌ LOSS: <b>—</b>\n"
        "🔁 Повторы: <b>—</b>\n\n"
        "На этом этапе проверяем только оформление."
    )
    await send_photo("stats.jpg", caption)


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 <b>ARTUR TRADE TEST</b>\n\n"
        "Это тестовый пульт будущего движка канала.\n"
        "Открой /panel и нажимай по порядку:\n\n"
        "🔎 Анализ → 🟢 BUY/🔴 SELL → ✅ WIN/❌ LOSS → 📊 Статистика",
        parse_mode="HTML",
    )


@router.message(Command("panel"))
async def show_panel(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer(
        "🧪 <b>ПУЛЬТ ARTUR TRADE</b>\n\n"
        "Нажимай кнопки и смотри, как пост меняется в тестовом канале.",
        reply_markup=panel(),
        parse_mode="HTML",
    )


@router.message(Command("status"))
async def status(message: Message):
    await message.answer(
        "🟢 Бот запущен\n"
        "Режим: DEMO\n"
        f"Канал: {SIGNAL_CHANNEL_ID}"
    )


@router.callback_query(F.data.startswith("demo:"))
async def demo(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    action = call.data.split(":", 1)[1]
    if action == "analysis":
        await publish_analysis(); text = "Анализ опубликован"
    elif action == "buy":
        await publish_signal("BUY"); text = "BUY опубликован"
    elif action == "sell":
        await publish_signal("SELL"); text = "SELL опубликован"
    elif action == "win":
        await publish_result("WIN"); text = "WIN опубликован"
    elif action == "loss":
        await publish_result("LOSS"); text = "LOSS опубликован"
    else:
        await publish_stats(); text = "Статистика опубликована"
    await call.answer(text)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
