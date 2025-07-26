import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers import start, help_cmd, handle_video, error_handler  # Changed from app.handlers
from config import TOKEN

# Health check server
from flask import Flask
server = Flask(__name__)

@server.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    server.run(host="0.0.0.0", port=8000)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Start Flask in background
    from threading import Thread
    Thread(target=run_flask, daemon=True).start()

    # Create bot application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))
    
    # Run bot
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
