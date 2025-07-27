from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
import yt_dlp
import asyncio
import time
import os
import re
import logging
import random
from config import *
from utils import *
from pytube import YouTube

logger = logging.getLogger(__name__)

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        # Small delay to avoid rate limiting
        await asyncio.sleep(2)

        # ===== Primary Method: Optimized yt-dlp =====
        await msg.edit_text("🔄 Verifying video access...")
        
        ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'retries': 3,
    'fragment_retries': 3,
    'socket_timeout': 15,
    'noplaylist': True,
    'geo_bypass': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['hls', 'dash']
        }
    },
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'http_headers': {
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None
}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception as ydl_error:
            logger.warning(f"Primary method failed: {ydl_error}")
            await msg.edit_text("⚡ Trying alternative download method...")
            
            # ===== Fallback Method: pytube =====
            try:
                yt = YouTube(url)
                stream = yt.streams.get_highest_resolution()
                filename = f"downloads/{yt.video_id}.mp4"
                stream.download(output_path="downloads/", filename=filename)
                
                info = {
                    'title': yt.title,
                    'duration': yt.length,
                    'description': yt.description,
                    'id': yt.video_id
                }
            except Exception as pytube_error:
                logger.error(f"Fallback method failed: {pytube_error}")
                raise Exception(f"All download methods failed:\n1. yt-dlp: {str(ydl_error)[:200]}\n2. pytube: {str(pytube_error)[:200]}")

        # File processing
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
        error_msg = f"❌ Download failed: {str(e)[:200]}"
        await msg.edit_text(error_msg)
        logger.error(f"Download failed: {e}", exc_info=True)

        if "Video unavailable" in str(e) or "geo-restricted" in str(e).lower():
            await update.message.reply_text(
                "🌍 This video appears restricted on our servers.\n"
                "Possible solutions:\n"
                "1. Try a different video\n"
                "2. Try again later\n"
                "3. Contact support if issue persists"
            )
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)
        try:
            await msg.delete()
        except:
            pass

async def error_handler(update: object, context: CallbackContext):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and hasattr(update, 'message'):
        await update.message.reply_text("⚠️ An error occurred. Please try again.")
