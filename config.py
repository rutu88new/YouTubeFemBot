import os

# Get token from Render environment variables
TOKEN = os.environ.get('TOKEN')  # Set this in Render dashboard
MAX_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION = 1200  # 20 minutes

# Ensure downloads directory exists
os.makedirs('downloads', exist_ok=True)
