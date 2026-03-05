import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===============================
# ENV VARIABLES
# ===============================
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8271376829"))

if not TOKEN:
    print("TOKEN not found")
    sys.exit()

# ===============================
# FILE PATHS
# ===============================
QR_PATH = "/storage/emulated/0/Bot py/qr.jpg"
USER_PATH = "/storage/emulated/0/Bot py/users.json"
KEY_PATH = "/storage/emulated/0/Bot py/keys.json"

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
# SAFE JSON LOADER
# ===============================
def load_json(path, default):

    try:
        if os.path.exists(path):
            with open(path,"r") as f:
                return json.load(f)
    except:
        pass

    return default

# ===============================
# DATABASE LOAD
# ===============================
users = load_json(USER_PATH,{})
keys = load_json(KEY_PATH,{
    "1d":[],
    "3d":[],
    "7d":[]
})

# ===============================
# SAVE FUNCTIONS
# ===============================
def save_users():
    with open(USER_PATH,"w") as f:
        json.dump(users,f)

def save_keys():
    with open(KEY_PATH,"w") as f:
        json.dump(keys,f)

# ===============================
# MENUS
# ===============================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🛒 Buy Key", callback_data="buykey")],
        [InlineKeyboardButton("📦 My Keys", callback_data="mykeys")],
        [InlineKeyboardButton("➕ Add Funds", callback_data="addfunds")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("🔑 Add Key", callback_data="admin_addkey")],
        [InlineKeyboardButton("❌ Remove Key", callback_data="admin_remove_menu")],
        [InlineKeyboardButton("📦 Stock", callback_data="admin_stock_list")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="mainmenu")]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back", callback_data="mainmenu")]
    ])

# ===============================
# START
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)

    if user_id not in users:
        users[user_id] = {"balance":0,"keys":[]}
        save_users()

    await update.message.reply_text(
        "🔥 Welcome To Key Shop Bot",
        reply_markup=main_menu()
    )

# ===============================
# ADMIN PANEL
# ===============================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👑 Admin Panel",
        reply_markup=admin_menu()
    )

# ===============================
# BUTTON HANDLER
# ===============================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = query.data

    # -------- MAIN MENU --------
    if data == "mainmenu":
        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔥 Welcome To Key Shop Bot",
            reply_markup=main_menu()
        )

    # -------- BALANCE --------
    elif data == "balance":

        users.setdefault(user_id,{"balance":0,"keys":[]})

        await query.edit_message_text(
            f"💰 Balance ₹{users[user_id]['balance']}",
            reply_markup=main_menu()
        )

    # -------- BUY KEY --------
    elif data == "buykey":

        keyboard = [
            [InlineKeyboardButton("1 Day ₹50", callback_data="buy_1d")],
            [InlineKeyboardButton("3 Day ₹120", callback_data="buy_3d")],
            [InlineKeyboardButton("7 Day ₹200", callback_data="buy_7d")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="mainmenu")]
        ]

        await query.edit_message_text(
            "🛒 Select Key Type",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -------- PURCHASE KEY --------
    elif data.startswith("buy_"):

        plan = data.split("_")[1]

        price_map = {"1d":50,"3d":120,"7d":200}

        price = price_map.get(plan)
        if price is None:
            return

        users.setdefault(user_id,{"balance":0,"keys":[]})

        if users[user_id]["balance"] < price:
            await query.edit_message_text("❌ Not Enough Balance", reply_markup=main_menu())
            return

        if len(keys.get(plan,[])) == 0:
            await query.edit_message_text("❌ Stock Empty", reply_markup=main_menu())
            return

        users[user_id]["balance"] -= price
        key_value = keys[plan].pop(0)

        users[user_id]["keys"].append(key_value)

        save_users()
        save_keys()

        await query.edit_message_text(
            f"✅ Purchase Done\n\n🔑 Key:\n{key_value}",
            reply_markup=main_menu()
        )

    # -------- MY KEYS --------
    elif data == "mykeys":

        user_keys = users.get(user_id,{}).get("keys",[])

        text = "📦 Your Keys\n\n" + ("\n".join(user_keys) if user_keys else "No Keys")

        await query.edit_message_text(text, reply_markup=main_menu())

    # -------- ADD FUNDS --------
    elif data == "addfunds":

        addfund_state[user_id] = "amount"

        await query.edit_message_text(
            f"💸 Enter Amount\nMin ₹{MIN_PAY}\nMax ₹{MAX_PAY}",
            reply_markup=back_menu()
        )

    # -------- ADMIN STATS --------
    elif data == "admin_stats":

        await query.edit_message_text(
            f"📊 Stats\nUsers: {len(users)}",
            reply_markup=admin_menu()
        )

    # -------- ADMIN ADD KEY --------
    elif data == "admin_addkey":

        admin_key_state[user_id] = "addkey"

        await query.edit_message_text(
            "Send Key Format:\n1d KEY-XXX",
            reply_markup=back_menu()
        )

    # -------- REMOVE KEY --------
    elif data.startswith("removekey_"):

        parts = data.split("_")

        if len(parts) >= 3:
            plan = parts[1]
            key_value = parts[2]

            if key_value in keys.get(plan,[]):
                keys[plan].remove(key_value)
                save_keys()

        await query.edit_message_text("✅ Key Removed", reply_markup=admin_menu())

# ===============================
# MESSAGE HANDLER
# ===============================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = str(update.message.from_user.id)

    # -------- ADMIN ADD KEY --------
    if user_id in admin_key_state:

        try:
            plan, key_value = update.message.text.split()

            if plan not in keys:
                await update.message.reply_text("Invalid Plan")
                return

            keys[plan].append(key_value)
            save_keys()

            await update.message.reply_text("✅ Key Added")
            del admin_key_state[user_id]

        except:
            await update.message.reply_text("Format:\n1d KEY-XXX")

    # -------- ADD FUNDS --------
    if user_id in addfund_state:

        if addfund_state[user_id] == "amount":

            text = update.message.text

            if not text or not text.isdigit():
                return

            amount = int(text)

            if amount < MIN_PAY or amount > MAX_PAY:
                return

            if not os.path.exists(QR_PATH):
                await update.message.reply_text("QR File Missing")
                return

            pending_funds[user_id] = str(amount)
            addfund_state[user_id] = "qr"

            await update.message.reply_photo(
                photo=open(QR_PATH,"rb"),
                caption=f"💰 Pay ₹{amount}\nSend Screenshot After Payment",
                reply_markup=back_menu()
            )

    # -------- PAYMENT SCREENSHOT --------
    if user_id in pending_funds and update.message.photo:

        amount = pending_funds[user_id]

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        ]])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 Payment\nUser: {user_id}\nAmount: ₹{amount}",
            reply_markup=keyboard
        )

        await update.message.reply_text(
            "✅ Sent To Admin",
            reply_markup=main_menu()
        )

        del pending_funds[user_id]

# ===============================
# RUN BOT
# ===============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))

print("🚀 Bot Running Production Ready")

app.run_polling(drop_pending_updates=True)