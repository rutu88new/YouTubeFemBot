import re
import subprocess

def escape_markdown(text):
    """Escape all special MarkdownV2 characters"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!\\'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def format_time(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    return f"{seconds//3600}h {(seconds%3600)//60}m"

def compress_video(input_path, output_path):
    """Compress video with minimal quality loss"""
    subprocess.run([
        'ffmpeg', '-i', input_path,
        '-vcodec', 'libx264', '-crf', '18',
        '-preset', 'fast', '-acodec', 'copy',
        output_path
    ], check=True)
