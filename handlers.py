from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
import yt_dlp
import asyncio
import time
import os
import re
import logging
from config import *
from utils import *

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and hasattr(update, 'message'):
        await update.message.reply_text("⚠️ An error occurred. Please try again.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = escape_markdown(
        "🎬 *YouTube Video Downloader*\n\n"
        "Send me a YouTube link to download videos\n\n"
        "Features:\n"
        "• Highest quality downloads\n"
        "• Real-time progress\n"
        "• Copyable descriptions\n"
        "• Fast downloads"
    )
    await update.message.reply_text(welcome_msg, parse_mode="MarkdownV2")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = escape_markdown(
        "🛠️ *Bot Help*\n\n"
        "Just send a YouTube link to download\n\n"
        "Max duration: 20 minutes\n"
        "Max size: 50MB (larger videos will be compressed)"
    )
    await update.message.reply_text(help_msg, parse_mode="MarkdownV2")

class ProgressTracker:
    def __init__(self, update, msg):
        self.update = update
        self.msg = msg
        self.start_time = time.time()
        self.last_update = time.time()
        self.last_bytes = 0
        self.last_speed = 0
        self.stalled_count = 0
        
    async def callback(self, d):
        if d['status'] == 'downloading':
            now = time.time()
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0)
            speed = d.get('speed', 0)
            
            if speed == 0 or (downloaded - self.last_bytes) < 1024:
                self.stalled_count += 1
                if self.stalled_count % 5 == 0:
                    status = "⏳ Download is progressing slowly..."
                    if speed == 0:
                        status = "⌛ Download paused (waiting for connection)..."
                    await self.msg.edit_text(status)
                return
            
            percent = min(99.9, (downloaded / total) * 100) if total else 0
            elapsed = now - self.start_time
            eta = (total - downloaded) / speed if speed else 0
            
            should_update = (
                (now - self.last_update >= 5) or 
                (abs(percent - (self.last_bytes/total*100 if total else 0)) >= 5
            )
            
            if should_update:
                progress_text = (
                    f"⬇️ Downloading: {percent:.1f}%\n"
                    f"⚡ Speed: {speed/(1024*1024):.1f} MB/s\n"
                    f"🕒 Elapsed: {format_time(elapsed)}\n"
                    f"⏳ Remaining: {format_time(eta)}\n"
                    f"📦 Size: {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB\n\n"
                    "Please be patient, your download is in progress..."
                )
                
                try:
                    await self.msg.edit_text(progress_text)
                    self.last_update = now
                    self.last_bytes = downloaded
                    self.last_speed = speed
                except Exception as e:
                    logger.warning(f"Progress update failed: {e}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+', url):
        await update.message.reply_text("❌ Invalid YouTube URL")
        return

    msg = await update.message.reply_text("🔍 Analyzing video...")
    filename = None

    try:
        await msg.edit_text("🔄 Getting video information...")
        
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Video')[:60]
            duration = info.get('duration', 0)
            description = info.get('description', 'No description available')
            safe_description = f"```\n{description[:800]}\n```" if description else "`No description available`"

            if duration > MAX_DURATION:
                await msg.edit_text(
                    f"❌ Video too long (> {MAX_DURATION//60}m)\n"
                    f"📌 Max allowed: {MAX_DURATION//60} minutes"
                )
                return

        await msg.edit_text("⬇️ Starting download...")
        
        filename = f"downloads/{info['id']}.mp4"
        progress = ProgressTracker(update, msg)
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': filename,
            'progress_hooks': [progress.callback],
            'retries': 10,
            'socket_timeout': 30,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        filesize = os.path.getsize(filename)
        if filesize > MAX_SIZE:
            await msg.edit_text("🔄 Compressing video...")
            compressed = f"{filename}_compressed.mp4"
            compress_video(filename, compressed)
            os.remove(filename)
            filename = compressed

        await msg.edit_text("📤 Uploading to Telegram...")
        
        with open(filename, 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption=(
                    f"🎥 {escape_markdown(title)}\n"
                    f"⏱️ Duration: {duration//60}m{duration%60:02d}s\n\n"
                    f"📝 Description:\n{safe_description}\n\n"
                    "⬇️ Downloaded via @YouTubeDownloaderBot"
                ),
                parse_mode="MarkdownV2",
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300
            )
            
    except Exception as e:
        error_msg = f"❌ Error: {str(e)[:200]}"
        await msg.edit_text(escape_markdown(error_msg))
        logger.error(f"Download failed: {e}", exc_info=True)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)
        try:
            await msg.delete()
        except:
            pass
