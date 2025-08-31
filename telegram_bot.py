import os
import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'src', 'database', 'game.db')

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def format_balance(balance_wei, decimals=18):
    """Format balance from wei to readable format"""
    return str(int(balance_wei) / (10 ** decimals))

# ---------- Commands ----------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    logging.info(f"/start used by {update.effective_user.id} ({update.effective_user.username})")

    game_url = "https://clinquant-sopapillas-19b989.netlify.app/"
    keyboard = [[InlineKeyboardButton("Open Game", web_app=WebAppInfo(url=game_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "Welcome! Click the button below to open the game!"

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    logging.info(f"/help used by {update.effective_user.id} ({update.effective_user.username})")

    help_text = """Available commands:
/balance <username> - Get player balance
/credit <player_id> <token> <amount> - Credit player (admin only)
/debit <player_id> <token> <amount> - Debit player (admin only)"""

    if update.message:
        await update.message.reply_text(help_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(help_text)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    logging.info(f"/balance by {update.effective_user.id} args={context.args}")

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /balance <username>")
        return

    username = context.args[0]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE username = ?", (username,))
        player = cursor.fetchone()
        conn.close()

        if not player:
            await update.message.reply_text("Player not found.")
            return

        oxy_balance = format_balance(player['oxy_balance'])
        ko_balance = format_balance(player['ko_balance'])

        balance_text = f"Balance for {player['username']}:\nOXY: {oxy_balance}\nKO: {ko_balance}"
        await update.message.reply_text(balance_text)

    except Exception as e:
        logging.error(f"Error in /balance: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /credit command (admin only)"""
    logging.info(f"/credit by {update.effective_user.id} args={context.args}")

    allowed_admins = os.environ.get('TELEGRAM_ALLOWED_ADMINS', '').split(',')
    if str(update.effective_user.id) not in allowed_admins:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("Usage: /credit <player_id> <token> <amount>")
        return

    try:
        player_id = int(context.args[0])
        token = context.args[1].upper()
        amount = int(float(context.args[2]) * (10 ** 18))  # Convert to wei

        if token not in ['OXY', 'KO']:
            await update.message.reply_text("Token must be OXY or KO")
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        if not player:
            await update.message.reply_text("Player not found.")
            conn.close()
            return

        balance_field = 'ko_balance' if token == 'KO' else 'oxy_balance'
        cursor.execute(
            f"UPDATE players SET {balance_field} = {balance_field} + ? WHERE id = ?",
            (amount, player_id)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"Player {player_id} credited with {context.args[2]} {token}")

    except ValueError:
        await update.message.reply_text("Invalid player_id or amount")
    except Exception as e:
        logging.error(f"Error in /credit: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def debit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /debit command (admin only)"""
    logging.info(f"/debit by {update.effective_user.id} args={context.args}")

    allowed_admins = os.environ.get('TELEGRAM_ALLOWED_ADMINS', '').split(',')
    if str(update.effective_user.id) not in allowed_admins:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("Usage: /debit <player_id> <token> <amount>")
        return

    try:
        player_id = int(context.args[0])
        token = context.args[1].upper()
        amount = int(float(context.args[2]) * (10 ** 18))

        if token not in ['OXY', 'KO']:
            await update.message.reply_text("Token must be OXY or KO")
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        if not player:
            await update.message.reply_text("Player not found.")
            conn.close()
            return

        balance_field = 'ko_balance' if token == 'KO' else 'oxy_balance'
        current_balance = player[balance_field]

        if current_balance < amount:
            await update.message.reply_text("Insufficient balance")
            conn.close()
            return

        cursor.execute(
            f"UPDATE players SET {balance_field} = {balance_field} - ? WHERE id = ?",
            (amount, player_id)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"Player {player_id} debited with {context.args[2]} {token}")

    except ValueError:
        await update.message.reply_text("Invalid player_id or amount")
    except Exception as e:
        logging.error(f"Error in /debit: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

# ---------- Main ----------

def main():
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        logging.error("❌ Telegram bot token not set. Skipping Telegram bot initialization.")
        return

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("credit", credit_command))
    application.add_handler(CommandHandler("debit", debit_command))

    logging.info("🤖 Telegram bot started.")
    application.run_polling()

if __name__ == '__main__':
    main()
