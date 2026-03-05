import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ---------- ENV VARIABLES ----------
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8271376829"))

if not TOKEN:
    raise Exception("TOKEN not found in environment variables")

# ---------- PATHS ----------
QR_PATH = "qr.jpg"
USER_PATH = "users.json"
KEY_PATH = "keys.json"

# ---------- SETTINGS ----------
MIN_PAY = 30
MAX_PAY = 700

# ---------- STATES ----------
pending_funds = {}
addfund_state = {}

# ---------- DATABASE LOAD ----------
if os.path.exists(USER_PATH):
    with open(USER_PATH,"r") as f:
        users = json.load(f)
else:
    users = {}

if os.path.exists(KEY_PATH):
    with open(KEY_PATH,"r") as f:
        keys = json.load(f)
else:
    keys = {
        "1d": [],
        "3d": [],
        "7d": []
    }

# ---------- SAVE ----------
def save_users():
    with open(USER_PATH,"w") as f:
        json.dump(users,f)

def save_keys():
    with open(KEY_PATH,"w") as f:
        json.dump(keys,f)

# ---------- MENUS ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🛒 Buy Key", callback_data="buykey")],
        [InlineKeyboardButton("➕ Add Funds", callback_data="addfunds")],
        [InlineKeyboardButton("📦 My Keys", callback_data="mykeys")]
    ])

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)

    if user_id not in users:
        users[user_id] = {"balance":0,"keys":[]}
        save_users()

    await update.message.reply_text(
        "🔥 Welcome To Key Shop Bot",
        reply_markup=main_menu()
    )

# ---------- BUTTON HANDLER ----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = query.data

    # -------- MAIN MENU --------
    if data == "mainmenu":
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔥 Welcome To Key Shop Bot",
            reply_markup=main_menu()
        )

    # -------- BALANCE --------
    elif data == "balance":
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

    elif data.startswith("buy_"):

        plan = data.split("_")[1]

        price_map = {"1d":50,"3d":120,"7d":200}

        price = price_map[plan]

        if users[user_id]["balance"] < price:
            await query.edit_message_text("❌ Not Enough Balance", reply_markup=main_menu())
            return

        if len(keys[plan]) == 0:
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

    # -------- ADD FUNDS --------
    elif data == "addfunds":

        addfund_state[user_id] = "amount"

        await query.edit_message_text(
            f"💸 Enter Amount\nMin ₹{MIN_PAY}\nMax ₹{MAX_PAY}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="mainmenu")]
            ])
        )

    # -------- APPROVE PAYMENT --------
    elif data.startswith("approve_"):

        parts = data.split("_")
        uid = parts[1]
        amount = int(parts[2])

        if uid not in users:
            users[uid] = {"balance":0,"keys":[]}

        users[uid]["balance"] += amount
        save_users()

        await context.bot.send_message(
            chat_id=uid,
            text=f"✅ ₹{amount} Added To Your Balance"
        )

        await query.edit_message_text("✅ Payment Approved")

    # -------- REJECT PAYMENT --------
    elif data.startswith("reject_"):

        uid = data.split("_")[1]

        await context.bot.send_message(
            chat_id=uid,
            text="❌ Payment Rejected"
        )

        await query.edit_message_text("❌ Payment Rejected")

# ---------- MESSAGE HANDLER ----------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)

    # Add Funds Amount
    if user_id in addfund_state:

        if addfund_state[user_id] == "amount":

            text = update.message.text

            if not text.isdigit():
                return

            amount = int(text)

            if amount < MIN_PAY or amount > MAX_PAY:
                return

            pending_funds[user_id] = str(amount)
            addfund_state[user_id] = "qr"

            await update.message.reply_photo(
                photo=open(QR_PATH,"rb"),
                caption=f"💰 Pay ₹{amount}\nSend Screenshot After Payment"
            )

    # Payment Screenshot
    elif user_id in pending_funds and update.message.photo:

        amount = pending_funds[user_id]

        keyboard = [[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        ]]

        try:
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except:
            pass

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 Payment Request\nUser: {user_id}\nAmount: ₹{amount}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text(
            "✅ Sent To Admin",
            reply_markup=main_menu()
        )

        del pending_funds[user_id]

# ---------- RUN ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))

print("🚀 Bot Running 24/7 Ready")
app.run_polling(timeout=60, drop_pending_updates=True)