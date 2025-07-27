import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
# Updated imports to match new function names:
from handlers import start_command, help_command, handle_video, error_handler
from config import TOKEN
from flask import Flask
from threading import Thread

server = Flask(__name__)

@server.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    server.run(host="0.0.0.0", port=8000)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(TOKEN).build()

    # Updated handler registrations:
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start_command))  # Matches new name
    app.add_handler(CommandHandler("help", help_command))   # Matches new name
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    logger.info("Starting bot...")
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
