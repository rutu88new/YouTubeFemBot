import re
import subprocess
import asyncio
from math import ceil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!\\'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m {secs}s"
    return f"{mins}m {secs}s"

async def compress_video(input_path, output_path):
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vcodec', 'libx264', '-crf', '23',
        '-preset', 'fast', '-acodec', 'copy',
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()

async def progress_bar(current, total, msg):
    percent = current / total * 100
    bar = "⬢" * int(percent / 5) + "⬡" * (20 - int(percent / 5))
    text = (
        f"**Download Progress**\n"
        f"{bar}\n"
        f"📊 **{percent:.1f}%** "
        f"({current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB)\n"
        "_Patience is a virtue..._"
    )
    await msg.edit_text(text, parse_mode="MarkdownV2")
