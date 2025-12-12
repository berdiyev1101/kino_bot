from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import json
import os

# ================== Sozlamalar ==================
ADMIN_IDS = [5795200638,7070532437]
CHANNEL_USERNAME = "muhridd1n_channel"
DATABASE = "movies.json"

# ================== JSON baza yuklash/saqlash ==================
def load_db():
    if not os.path.exists(DATABASE):
        with open(DATABASE, "w") as f:
            f.write("{}")
        return {}
    try:
        with open(DATABASE, "r") as f:
            data = f.read().strip()
            if data == "":
                return {}
            return json.loads(data)
    except:
        with open(DATABASE, "w") as f:
            f.write("{}")
        return {}

def save_db(data):
    with open(DATABASE, "w") as f:
        json.dump(data, f, indent=4)

# ================== Menyular ==================
def get_user_menu(is_member: bool):
    """User menyusi: a’zo bo‘lsa kino qidirish, bo‘lmasa azo va tekshirish"""
    if is_member:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Kino qidirish", callback_data="get_movie")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanalga a’zo bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✔️ A’zolikni tekshirish", callback_data="check_sub")]
        ])

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
        chat_member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        is_member = chat_member.status in ("member", "administrator", "creator")
        await update.message.reply_text(
            "Menyu:",
            reply_markup=get_user_menu(is_member)
        )

# ================== Kanal obuna tekshirish ==================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    chat_member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
    is_member = chat_member.status in ("member", "administrator", "creator")
    if is_member:
        await query.edit_message_text("🔑 Kino kodi yuboring:", reply_markup=None)
        context.user_data["awaiting_code"] = True
    else:
        await query.edit_message_text("❌ Siz hali kanalga a'zo emassiz!",
                                      reply_markup=get_user_menu(False))

# ================== Xabarlarni ishlash ==================
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    user_id = update.effective_user.id

    # -------- Foydalanuvchi kodi --------
    if context.user_data.get("awaiting_code"):
        code = update.message.text.strip()
        if code in db:
            await update.message.reply_video(db[code])
        else:
            await update.message.reply_text("❌ Kod topilmadi.")
        context.user_data["awaiting_code"] = False

        # Kanal a’zo bo‘lganini tekshirish va menyuni ko‘rsatish
        chat_member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        is_member = chat_member.status in ("member", "administrator", "creator")
        await update.message.reply_text("Menyu:", reply_markup=get_user_menu(is_member))
        return

    # -------- Admin video yuklamoqda --------
    if context.user_data.get("adding_movie"):
        if update.message.video:
            context.user_data["file_id"] = update.message.video.file_id
            context.user_data["adding_movie"] = False
            await update.message.reply_text("Kino uchun kod yuboring:")
            context.user_data["waiting_code"] = True
        else:
            await update.message.reply_text("❌ Iltimos, faqat video yuboring!")
        return

    # -------- Admin kodi yuboradi --------
    if context.user_data.get("waiting_code"):
        code = update.message.text.strip()
        file_id = context.user_data["file_id"]
        if code in db:
            await update.message.reply_text("❌ Bu kod allaqachon ishlatilgan! Boshqa kod kiriting.")
            return
        db[code] = file_id
        save_db(db)
        await update.message.reply_text(f"✔️ Kino qo‘shildi!\n🔑 Kod: {code}")
        context.user_data["waiting_code"] = False
        await update.message.reply_text("Admin panel:", reply_markup=get_admin_menu())
        return

    # -------- Admin o‘chirish kodi --------
    if context.user_data.get("deleting"):
        code = update.message.text.strip()
        if code in db:
            db.pop(code)
            save_db(db)
            await update.message.reply_text(f"🎬 Kino '{code}' o‘chirildi!")
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

    # -------- User kino oladi --------
    if query.data == "get_movie":
        await query.edit_message_text("🔑 Kino kodini yuboring:")
        context.user_data["awaiting_code"] = True
        return

    if query.data == "check_sub":
        await check_subscription(update, context)
        return

    # -------- Admin tugmalar --------
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Faqat adminlar uchun.")
        return

    if query.data == "add_movie":
        await query.edit_message_text("🎬 Kinoni video sifatida yuboring:")
        context.user_data["adding_movie"] = True
        return

    if query.data == "list_movies":
        db = load_db()
        if db:
            text = "🎬 Kino ro‘yxati:\n" + "\n".join(db.keys())
        else:
            text = "🎬 Hozircha kino yo‘q."
        await query.edit_message_text(text)
        await update.effective_message.reply_text("Admin panel:", reply_markup=get_admin_menu())
        return

    if query.data == "delete_movie":
        db = load_db()
        if not db:
            await query.edit_message_text("❌ Kino yo‘q.")
            await update.effective_message.reply_text("Admin panel:", reply_markup=get_admin_menu())
            return
        await query.edit_message_text("❌ O‘chirmoqchi bo‘lgan kino kodi yuboring:")
        context.user_data["deleting"] = True
        return

# ================== Asosiy ==================
def main():
    app = ApplicationBuilder().token("8592086953:AAFoqAyRDi6vY2NnZ6j2rw2G-D9hiVynu5A").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.VIDEO, user_message))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
