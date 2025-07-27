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
from pytube import YouTube

logger = logging.getLogger(__name__)

# Renamed from 'start' to 'start_command'
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

# Renamed from 'help_cmd' to 'help_command'
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = escape_markdown(
        "🛠️ *Bot Help*\n\n"
        "Just send a YouTube link to download\n\n"
        "Max duration: 20 minutes\n"
        "Max size: 50MB (larger videos will be compressed)"
    )
    await update.message.reply_text(help_msg, parse_mode="MarkdownV2")

# ... (keep all other functions EXACTLY as-is, including handle_video and error_handler)async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    msg = await update.message.reply_text("🔍 Analyzing video...")
    filename = None

    try:
        # First try with optimized yt-dlp (Approach 1)
        await msg.edit_text("🔄 Verifying video access...")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'progress_hooks': [ProgressTracker(update, msg).callback],
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'noplaylist': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'ignoreerrors': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36'
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception as ydl_error:
            logger.warning(f"yt-dlp failed, trying pytube fallback: {ydl_error}")
            await msg.edit_text("🔄 Trying alternative download method...")
            
            # Fallback to pytube (Approach 3)
            try:
                yt = YouTube(url)
                stream = yt.streams.get_highest_resolution()
                filename = f"downloads/{yt.video_id}.mp4"
                stream.download(output_path="downloads/", filename=filename)
                
                # Create info dict similar to yt-dlp's format
                info = {
                    'title': yt.title,
                    'duration': yt.length,
                    'description': yt.description,
                    'id': yt.video_id
                }
            except Exception as pytube_error:
                raise Exception(f"All download methods failed:\n1. yt-dlp: {str(ydl_error)}\n2. pytube: {str(pytube_error)}")

        # Rest of your existing processing logic
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
                "2. Contact admin to configure region bypass"
            )
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)
        try:
            await msg.delete()
        except:
            pass
