import os

# YouTube settings
MAX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION = 1200  # 20 mins

# Tor proxy
TOR_PROXY = "socks5://127.0.0.1:9050"
INVIDIOUS_INSTANCE = "https://vid.puffyan.us"  # Fallback API

# Ensure downloads dir exists
os.makedirs("downloads", exist_ok=True)
