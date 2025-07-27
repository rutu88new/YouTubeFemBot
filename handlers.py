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
            
            time_condition = (now - self.last_update >= 5)
            progress_condition = (abs(percent - (self.last_bytes/total*100 if total else 0)) >= 5)
            should_update = time_condition or progress_condition
            
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
    msg = await update.message.reply_text("🔍 Analyzing video...")
    filename = None

    try:
        # First verify video availability
        await msg.edit_text("🔄 Verifying video access...")
        with yt_dlp.YoutubeDL({
            'quiet': True,
            'simulate': True,
            'geo_bypass': True,
            'extractor_args': {'youtube': {'skip': ['hls', 'dash']}}
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Could not extract video info")
            if info.get('availability') != 'public':
                raise Exception("Video is not publicly available")

        await msg.edit_text("⬇️ Starting download (may take a while)...")
        
        filename = f"downloads/{info['id']}.mp4"
        progress = ProgressTracker(update, msg)
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': filename,
            'progress_hooks': [progress.callback],
            'retries': 15,
            'fragment_retries': 15,
            'socket_timeout': 60,
            'noplaylist': True,
            'geo_bypass': True,
            'ignoreerrors': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        filesize = os.path.getsize(filename)
        if filesize > MAX_SIZE:
            await msg.edit_text("🔄 Compressing video (quality preserved)...")
            compressed = f"{filename}_compressed.mp4"
            compress_video(filename, compressed)
            os.remove(filename)
            filename = compressed

        await msg.edit_text("📤 Uploading to Telegram...")
        
        with open(filename, 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption=(
                    f"🎥 {escape_markdown(info['title'][:60])}\n"
                    f"⏱️ Duration: {info['duration']//60}m{info['duration']%60:02d}s\n\n"
                    f"📝 Description:\n```\n{info.get('description', 'No description')[:800]}\n```\n\n"
                    "⬇️ Downloaded via @YouTubeDownloaderBot"
                ),
                parse_mode="MarkdownV2",
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300
            )
            
    except Exception as e:
        error_msg = f"❌ Enhanced download failed: {str(e)[:200]}"
        await msg.edit_text(error_msg)
        logger.error(f"Download failed: {e}", exc_info=True)
        
        if "Video unavailable" in str(e) or "geo-restricted" in str(e).lower():
            await update.message.reply_text(
                "🌍 This video appears restricted on our servers.\n"
                "Possible solutions:\n"
                "1. Try a different video\n"
                "2. Contact admin to configure region bypass"
            )
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)
        try:
            await msg.delete()
        except:
            pass
