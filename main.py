import os
import shutil
import requests
import zipfile
import tempfile
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'
COOKIES_FILE = 'cookies.txt'  # مسیر فایل کوکی‌ها

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

def choose_resolution(resolution):
    resolutions = {
        "low": 360,
        "medium": 720,
        "high": 1080,
        "very high": 2160
    }
    return resolutions.get(resolution, 720)

def download_video(url, resolution):
    height = choose_resolution(resolution)
    ydl_opts = {
        'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
        'cookies': COOKIES_FILE,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info_dict)
    return file_path

def convert_to_mp3(filename):
    clip = VideoFileClip(filename)
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    resolution = "high"

    try:
        video_path = download_video(url, resolution)
        await update.message.reply_text("Video downloaded successfully!")
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # Get the file size in MB

        if file_size <= 50:  # Telegram can handle videos up to 50MB directly
            await update.message.reply_video(video=video_path)
        else:  # For larger files, send as document
            await update.message.reply_document(document=video_path)

        convert_to_mp3(video_path)
        await update.message.reply_text("Video converted to MP3 successfully!")

        os.remove(video_path)
    except Exception as e:
        await update.message.reply_text(f'Failed to process the link: {e}')

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(600).write_timeout(600).build()

    start_handler = CommandHandler('start', start)
    link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)

    application.add_handler(start_handler)
    application.add_handler(link_handler)

    print('Bot is running...')
    application.run_polling()
