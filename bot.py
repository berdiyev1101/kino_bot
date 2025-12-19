from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import json
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ================== Sozlamalar ==================
ADMIN_IDS = [5795200638, 7070532437]

CHANNELS = [
    "asilmediauzb1",
    "xebcof_movies"
]

DATABASE = "movies.json"

# ================== JSON baza ==================
def load_db():
    if not os.path.exists(DATABASE):
        with open(DATABASE, "w") as f:
            f.write("{}")
        return {}
    try:
        with open(DATABASE, "r") as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        with open(DATABASE, "w") as f:
            f.write("{}")
        return {}

def save_db(data):
    with open(DATABASE, "w") as f:
        json.dump(data, f, indent=4)

# ================== BARCHA kanallarni tekshirish ==================
async def is_member_of_channels(bot, user_id):
    """
    Foydalanuvchi BARCHA kanallarga a'zo bo'lsa True qaytaradi
    """
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except:
            return False
    return True

# ================== Menyular ==================
def get_user_menu(is_member: bool):
    if is_member:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Kino qidirish", callback_data="get_movie")]
        ])
    else:
        buttons = []
        for ch in CHANNELS:
            buttons.append([
                InlineKeyboardButton(
                    f"📢 @{ch}", url=f"https://t.me/{ch}"
                )
            ])

        buttons.append([
            InlineKeyboardButton("✔️ A’zolikni tekshirish", callback_data="check_sub")
        ])

        return InlineKeyboardMarkup(buttons)

def get_admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("📋 Kino ro‘yxati", callback_data="list_movies")],
        [InlineKeyboardButton("❌ Kino o‘chirish", callback_data="delete_movie")]
    ])

# ================== /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            "Admin panel:",
            reply_markup=get_admin_menu()
        )
    else:
        is_member = await is_member_of_channels(context.bot, user_id)
        await update.message.reply_text(
            "Menyu:",
            reply_markup=get_user_menu(is_member)
        )

# ================== Obuna tekshirish ==================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_member = await is_member_of_channels(context.bot, user_id)

    if is_member:
        context.user_data["awaiting_code"] = True
        await query.edit_message_text("🔑 Kino kodi yuboring:")
    else:
        await query.edit_message_text(
            "❌ Avval BARCHA kanallarga a’zo bo‘ling!",
            reply_markup=get_user_menu(False)
        )

# ================== Xabarlar ==================
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    user_id = update.effective_user.id

    # -------- User kino kodi --------
    if context.user_data.get("awaiting_code"):
        code = update.message.text.strip()
        if code in db:
            await update.message.reply_video(db[code])
        else:
            await update.message.reply_text("❌ Kod topilmadi.")

        context.user_data["awaiting_code"] = False
        is_member = await is_member_of_channels(context.bot, user_id)
        await update.message.reply_text(
            "Menyu:",
            reply_markup=get_user_menu(is_member)
        )
        return

    # -------- Admin video --------
    if context.user_data.get("adding_movie"):
        if update.message.video:
            context.user_data["file_id"] = update.message.video.file_id
            context.user_data["adding_movie"] = False
            context.user_data["waiting_code"] = True
            await update.message.reply_text("Kino uchun kod yuboring:")
        else:
            await update.message.reply_text("❌ Faqat video yuboring!")
        return

    # -------- Admin kod --------
    if context.user_data.get("waiting_code"):
        code = update.message.text.strip()
        if code in db:
            await update.message.reply_text("❌ Bu kod mavjud!")
            return

        db[code] = context.user_data["file_id"]
        save_db(db)

        context.user_data["waiting_code"] = False
        await update.message.reply_text(f"✔️ Kino qo‘shildi!\n🔑 Kod: {code}")
        await update.message.reply_text("Admin panel:", reply_markup=get_admin_menu())
        return

    # -------- Admin o‘chirish --------
    if context.user_data.get("deleting"):
        code = update.message.text.strip()
        if code in db:
            db.pop(code)
            save_db(db)
            await update.message.reply_text("✔️ O‘chirildi!")
        else:
            await update.message.reply_text("❌ Kod topilmadi.")

        context.user_data["deleting"] = False
        await update.message.reply_text("Admin panel:", reply_markup=get_admin_menu())
        return

# ================== Tugmalar ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "get_movie":
        context.user_data["awaiting_code"] = True
        await query.edit_message_text("🔑 Kino kodini yuboring:")
        return

    if query.data == "check_sub":
        await check_subscription(update, context)
        return

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Faqat adminlar uchun.")
        return

    if query.data == "add_movie":
        context.user_data["adding_movie"] = True
        await query.edit_message_text("🎬 Videoni yuboring:")
        return

    if query.data == "list_movies":
        db = load_db()
        text = "🎬 Kino ro‘yxati:\n" + "\n".join(db.keys()) if db else "🎬 Kino yo‘q."
        await query.edit_message_text(text)
        await update.effective_message.reply_text(
            "Admin panel:",
            reply_markup=get_admin_menu()
        )
        return

    if query.data == "delete_movie":
        context.user_data["deleting"] = True
        await query.edit_message_text("❌ O‘chirish uchun kod yuboring:")
        return

# ================== Main ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.VIDEO, user_message))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
