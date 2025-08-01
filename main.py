import os
import logging
from telegram.ext import Application, MessageHandler, filters
from handlers import *
from stem.control import Controller
from stem import Signal

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def renew_tor_ip():
    try:
        with Controller.from_port(port=9051) as c:
            c.authenticate()
            c.signal(Signal.NEWNYM)
            logging.info("Tor IP renewed successfully")
    except Exception as e:
        logging.error(f"Tor IP renewal failed: {e}")

async def post_init(app):
    renew_tor_ip()

def main():
    app = Application.builder() \
        .token(os.getenv("TOKEN")) \
        .post_init(post_init) \
        .build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))
    
    # Health check endpoint
    @app.route('/health')
    async def health(request):
        return {"status": "OK"}

    app.run_polling()

if __name__ == "__main__":
    main()
