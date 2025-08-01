import re
import subprocess
from math import ceil
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!\\'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def compress_video(input_path, output_path):
    subprocess.run([
        'ffmpeg', '-i', input_path,
        '-vcodec', 'libx264', '-crf', '23',
        '-preset', 'fast', '-acodec', 'copy',
        output_path
    ], check=True)

async def send_progress(update, msg, percent, speed, eta):
    progress_bar = "⬢" * int(percent / 10) + "⬡" * (10 - int(percent / 10))
    text = (
        f"**Downloading...**\n"
        f"{progress_bar} {percent:.1f}%\n"
        f"⚡ **Speed:** {speed/1024/1024:.1f} MB/s\n"
        f"⏳ **ETA:** {format_time(eta)}\n\n"
        "_This may take a while for long videos..._"
    )
    await msg.edit_text(text, parse_mode="MarkdownV2")
