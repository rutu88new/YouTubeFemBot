import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers import start_command, help_command, handle_video, error_handler
from config import TOKEN
from flask import Flask, request
import os

# Initialize Flask app
server = Flask(__name__)

@server.route('/')
def home():
    return "YouTube Fem Bot is running!", 200

@server.route('/health')
def health_check():
    return "OK", 200

# Webhook route for Zeabur
@server.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok', 200

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Create Telegram application
    app = Application.builder().token(TOKEN).build()

    # Register handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    # Determine run mode based on environment
    if os.environ.get('ZEABUR'):
        # Webhook mode for Zeabur
        PORT = int(os.environ.get('PORT', 3000))
        WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            drop_pending_updates=True
        )
    else:
        # Polling mode for local development
        logger.info("Starting bot in polling mode...")
        app.run_polling(
            poll_interval=3.0,
            timeout=30,
            drop_pending_updates=True
        )

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}", exc_info=True)
        raise
