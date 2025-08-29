import os
import sqlite3
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

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

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    game_url = "https://gameapp-aehzeq.manus.space"
    
    keyboard = [[InlineKeyboardButton("Open Game", web_app=WebAppInfo(url=game_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome! Click the button below to open the game!",
        reply_markup=reply_markup
    )

async def help_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """Available commands:
/balance <username> - Get player balance
/credit <player_id> <token> <amount> - Credit player (admin only)
/debit <player_id> <token> <amount> - Debit player (admin only)"""
    
    await update.message.reply_text(help_text)

async def balance_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
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
        await update.message.reply_text(f"Error: {str(e)}")

async def credit_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /credit command (admin only)"""
    # Check if user is admin
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
        
        # Check if player exists
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        if not player:
            await update.message.reply_text("Player not found.")
            conn.close()
            return
        
        # Update balance
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
        await update.message.reply_text(f"Error: {str(e)}")

async def debit_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /debit command (admin only)"""
    # Check if user is admin
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
        amount = int(float(context.args[2]) * (10 ** 18))  # Convert to wei
        
        if token not in ['OXY', 'KO']:
            await update.message.reply_text("Token must be OXY or KO")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if player exists
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        if not player:
            await update.message.reply_text("Player not found.")
            conn.close()
            return
        
        # Check balance
        balance_field = 'ko_balance' if token == 'KO' else 'oxy_balance'
        current_balance = player[balance_field]
        
        if current_balance < amount:
            await update.message.reply_text("Insufficient balance")
            conn.close()
            return
        
        # Update balance
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
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    """Main function to run the bot"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("Telegram bot token not set. Skipping Telegram bot initialization.")
        return
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("credit", credit_command))
    application.add_handler(CommandHandler("debit", debit_command))
    
    print("Telegram bot started.")
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()

