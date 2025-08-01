import yt_dlp
import requests
import random
from config import *
from utils import *
from telegram import Update
from telegram.ext import ContextTypes

class Downloader:
    @staticmethod
    async def tor_download(url, msg):
        ydl_opts = {
            'format': 'bestvideo[height<=?2160]+bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'proxy': TOR_PROXY,
            'throttled_rate': '1.5M',
            'progress_hooks': [lambda d: self._progress_hook(d, msg)],
            'extractor_args': {'youtube': {'player_client': 'android'}},
            'retries': 10
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url)
                return ydl.prepare_filename(info)
        except Exception as e:
            raise Exception(f"Tor download failed: {str(e)[:200]}")

    @staticmethod
    async def invidious_download(url, msg):
        video_id = url.split("v=")[-1]
        instance = random.choice(INVIDIOUS_INSTANCES)
        api_url = f"{instance}/api/v1/videos/{video_id}"
        
        try:
            response = requests.get(api_url, timeout=10).json()
            best_stream = max(
                [s for s in response["formatStreams"] if s["type"].startswith("video/mp4")],
                key=lambda x: x["height"]
            )
            return await self._download_with_progress(best_stream["url"], msg)
        except Exception as e:
            raise Exception(f"Invidious failed: {str(e)[:200]}")

    async def _progress_hook(self, d, msg):
        if d['status'] == 'downloading':
            await progress_bar(
                current=d.get('downloaded_bytes', 0),
                total=d.get('total_bytes', 1),
                msg=msg
            )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔍 _Starting download..._", parse_mode="MarkdownV2")
    
    try:
        # Try Tor first
        file_path = await Downloader.tor_download(update.message.text, msg)
        
        # Fallback to Invidious
        if not file_path:
            file_path = await Downloader.invidious_download(update.message.text, msg)
        
        # Upload to Telegram
        await update.message.reply_video(
            video=open(file_path, 'rb'),
            caption="✅ Your video is ready!",
            supports_streaming=True
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Download failed:\n\n`{str(e)}`", parse_mode="MarkdownV2")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
