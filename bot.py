import json
import os
import sys
import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===============================
# ENV
# ===============================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8271376829"))

if not TOKEN:
    print("TOKEN NOT FOUND")
    sys.exit()

# ===============================
# PATHS (Render Safe)
# ===============================
BASE_DIR = os.getcwd()

QR_PATH = os.path.join(BASE_DIR, "qr.jpg")
USER_PATH = os.path.join(BASE_DIR, "users.json")
KEY_PATH = os.path.join(BASE_DIR, "keys.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

# ===============================
# SETTINGS
# ===============================
MIN_PAY = 30
MAX_PAY = 700

# ===============================
# STATES
# ===============================
pending_funds = {}
addfund_state = {}
admin_key_state = {}

# ===============================
# DATABASE LOAD SAFE
# ===============================
def load_json(path, default):
    try:
        if os.path.exists(path):
            return json.load(open(path, "r"))
    except:
        pass
    return default

users = load_json(USER_PATH, {})
keys = load_json(KEY_PATH, {
    "1d": [],
    "3d": [],
    "7d": []
})
history = load_json(HISTORY_PATH, {})

# ===============================
# SAVE FUNCTIONS
# ===============================
def save_users():
    json.dump(users, open(USER_PATH, "w"))

def save_keys():
    json.dump(keys, open(KEY_PATH, "w"))

def save_history():
    json.dump(history, open(HISTORY_PATH, "w"))

# ===============================
# MENUS
# ===============================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🛒 Buy Key", callback_data="buykey")],
        [InlineKeyboardButton("📦 My Keys", callback_data="mykeys")],
        [InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("➕ Add Funds", callback_data="addfunds")],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back To Menu", callback_data="mainmenu")]
    ])

# ===============================
# START
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)

    if user_id not in users:
        users[user_id] = {"balance": 0, "keys": []}
        save_users()

    await update.message.reply_text(
        """
🔥 Welcome To Premium Key Store

💎 Instant Delivery Shop
⚡ Secure Payments
📦 Purchase History Enabled
""",
        reply_markup=main_menu()
    )

# ===============================
# BUTTON HANDLER
# ===============================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = query.data

    # ---------- MAIN MENU ----------
    if data == "mainmenu":
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔥 Premium Key Store",
            reply_markup=main_menu()
        )

    # ---------- ADMIN PANEL ----------
    elif data == "admin_panel":

        if query.from_user.id != ADMIN_ID:
            await query.answer("Not Authorized ❌", show_alert=True)
            return

        await query.edit_message_text(
            "👑 Admin Control Panel",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("🔑 Add Key", callback_data="admin_addkey")],
                [InlineKeyboardButton("❌ Remove Key", callback_data="admin_remove_menu")],
                [InlineKeyboardButton("📦 Stock", callback_data="admin_stock_list")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="mainmenu")]
            ])
        )

    # ---------- BALANCE ----------
    elif data == "balance":

        users.setdefault(user_id, {"balance": 0, "keys": []})

        await query.edit_message_text(
            f"""
💰 Account Balance

👤 User ID: {user_id}
💵 Balance: ₹{users[user_id]['balance']}
""",
            reply_markup=main_menu()
        )

    # ---------- BUY MENU ----------
    elif data == "buykey":

        keyboard = [
            [InlineKeyboardButton("1 Day ₹50", callback_data="buy_1d")],
            [InlineKeyboardButton("3 Day ₹120", callback_data="buy_3d")],
            [InlineKeyboardButton("7 Day ₹200", callback_data="buy_7d")],
            [InlineKeyboardButton("⬅ Back", callback_data="mainmenu")]
        ]

        await query.edit_message_text(
            "🛒 Choose Premium Plan",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ---------- PURCHASE ----------
    elif data.startswith("buy_"):

        plan = data.split("_")[1]

        price_map = {"1d": 50, "3d": 120, "7d": 200}
        price = price_map.get(plan)

        if not price:
            return

        users.setdefault(user_id, {"balance": 0, "keys": []})

        if users[user_id]["balance"] < price:
            await query.edit_message_text("❌ Insufficient Balance", reply_markup=main_menu())
            return

        if len(keys.get(plan, [])) == 0:
            await query.edit_message_text("❌ Stock Empty", reply_markup=main_menu())
            return

        users[user_id]["balance"] -= price
        key_value = keys[plan].pop(0)

        users[user_id]["keys"].append(key_value)

        if user_id not in history:
            history[user_id] = []

        history[user_id].append({
            "key": key_value,
            "price": price,
            "time": str(datetime.datetime.now())
        })

        save_users()
        save_keys()
        save_history()

        await query.edit_message_text(
            f"""
✅ Purchase Successful

🔑 Your Key:
{key_value}

⚠ Keep This Key Safe
""",
            reply_markup=main_menu()
        )

    # ---------- MY KEYS ----------
    elif data == "mykeys":

        user_keys = users.get(user_id, {}).get("keys", [])

        text = "📦 My Keys\n\n"

        if not user_keys:
            text += "❌ No keys purchased yet"
        else:
            for i, k in enumerate(user_keys, 1):
                text += f"{i}. 🔑 {k}\n"

        await query.edit_message_text(text, reply_markup=main_menu())

    # ---------- HISTORY ----------
    elif data == "history":

        user_history = history.get(user_id, [])

        if not user_history:
            text = "📜 No Purchase History"
        else:
            text = "📜 Purchase History\n\n"
            for h in user_history:
                text += f"🔑 {h['key']}\n💰 ₹{h['price']}\n🕐 {h['time']}\n\n"

        await query.edit_message_text(text, reply_markup=main_menu())

    # ---------- ADD FUNDS ----------
    elif data == "addfunds":

        addfund_state[user_id] = "amount"

        await query.edit_message_text(
            f"""
💳 Add Balance

Min ₹{MIN_PAY}
Max ₹{MAX_PAY}

Send amount now
""",
            reply_markup=back_menu()
        )

# ===============================
# MESSAGE HANDLER
# ===============================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = str(update.message.from_user.id)

    # ADD FUNDS FLOW
    if user_id in addfund_state:

        if addfund_state[user_id] == "amount":

            text = update.message.text

            if not text or not text.isdigit():
                return

            amount = int(text)

            if amount < MIN_PAY or amount > MAX_PAY:
                return

            if not os.path.exists(QR_PATH):
                return

            pending_funds[user_id] = str(amount)
            addfund_state[user_id] = "qr"

            await update.message.reply_photo(
                photo=open(QR_PATH, "rb"),
                caption=f"""
💳 Payment Required

Amount: ₹{amount}

1️⃣ Pay via QR
2️⃣ Send Payment Screenshot
""",
                reply_markup=back_menu()
            )

    # PAYMENT SCREENSHOT → ADMIN
    if user_id in pending_funds and update.message.photo:

        amount = pending_funds[user_id]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"""
💰 Payment Request

User: {user_id}
Amount: ₹{amount}
""",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            ]])
        )

        await update.message.reply_text(
            "✅ Payment Sent For Verification",
            reply_markup=main_menu()
        )

        del pending_funds[user_id]

# ===============================
# RUN BOT
# ===============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))

print("🚀 Premium Shop Bot Running")
app.run_polling(drop_pending_updates=True)