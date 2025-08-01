import os

# Core Settings
TOKEN = os.getenv("TOKEN")
MAX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION = 1200  # 20 minutes

# Anti-Ban Systems
TOR_PROXY = "socks5://127.0.0.1:9050"
INVIDIOUS_INSTANCES = [
    "https://vid.puffyan.us",
    "https://inv.riverside.rocks",
    "https://yt.artemislena.eu"
]  # Rotate if one fails

# Ensure directories exist
os.makedirs("downloads", exist_ok=True)
