from telegram.ext import Application, MessageHandler, filters
from handlers import *
import logging
from stem.control import Controller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def renew_tor_ip():
    with Controller.from_port(port=9051) as c:
        c.authenticate()
        c.signal(Signal.NEWNYM)

def main():
    app = Application.builder().token(os.getenv("TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    app.run_polling()

if __name__ == "__main__":
    main()
