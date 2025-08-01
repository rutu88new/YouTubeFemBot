import os

# Get token from environment variables (set in Zeabur dashboard)
TOKEN = os.environ.get('TOKEN')
MAX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION = 1200  # 20 minutes

# Ensure downloads directory exists
os.makedirs('downloads', exist_ok=True)
